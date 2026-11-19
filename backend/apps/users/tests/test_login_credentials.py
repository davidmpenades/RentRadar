from contextlib import contextmanager
from unittest import mock

import pytest
from django.contrib.auth.hashers import (
    MD5PasswordHasher,
    PBKDF2PasswordHasher,
    identify_hasher,
    is_password_usable,
    make_password,
)
from django.contrib.auth.signals import user_login_failed
from django.db import connection
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from django.views.debug import ExceptionReporter

from apps.users import login
from apps.users.login import (
    check_credentials,
    is_checkable_password,
    is_queryable_email,
)
from apps.users.models import User, UserManager
from apps.users.throttling import login_pair_key

pytestmark = pytest.mark.django_db

EMAIL = "ana@correo.es"
PASSWORD = "vela roja en el puerto"
WRONG_PASSWORD = "vela azul en el puerto"
SURROGATE = chr(0xD800)
# Se construye con chr: un escape podría convertirse en el carácter al escribirlo
DIAERESIS = chr(0xA8)
HIDDEN = "********************"
# La marca no aparece en ningún identificador del código
MARK = "zq7x"


class FastPBKDF2PasswordHasher(PBKDF2PasswordHasher):
    iterations = 1000


FAST_PBKDF2 = f"{__name__}.FastPBKDF2PasswordHasher"
MD5 = "django.contrib.auth.hashers.MD5PasswordHasher"


def account(email=EMAIL, password=PASSWORD, **fields):
    return User.objects.create(email=email, password=make_password(password), **fields)


def check(email, password):
    return check_credentials(RequestFactory().post("/"), email=email, password=password)


@contextmanager
def counted_hashes():
    # El hasher de test es MD5: verify y make_password pasan por su encode
    with mock.patch.object(
        MD5PasswordHasher,
        "encode",
        autospec=True,
        side_effect=MD5PasswordHasher.encode,
    ) as encode:
        yield encode


@pytest.fixture
def failed_logins():
    received = []

    def receiver(sender, credentials, **kwargs):
        received.append(credentials)

    user_login_failed.connect(receiver, weak=False)
    yield received
    user_login_failed.disconnect(receiver)


# --- Prefiltro ----------------------------------------------------------------

UNQUERYABLE_EMAILS = {
    "none": None,
    "empty": "",
    "blank": "   ",
    "null-character": "ana\x00@correo.es",
    "lone-surrogate": f"ana{SURROGATE}@correo.es",
}


@pytest.mark.parametrize(
    "email", UNQUERYABLE_EMAILS.values(), ids=UNQUERYABLE_EMAILS.keys()
)
def test_unqueryable_emails_are_rejected_without_queries_hashes_or_signal(
    email, failed_logins
):
    account()

    with counted_hashes() as encode, CaptureQueriesContext(connection) as queries:
        user = check(email, PASSWORD)

    assert user is None
    assert len(queries) == 0
    assert encode.call_count == 0
    assert failed_logins == []


UNCHECKABLE_PASSWORDS = {
    "none": None,
    "empty": "",
    "129-code-points": "a" * 129,
    "lone-surrogate": f"vela{SURROGATE}",
}


@pytest.mark.parametrize(
    "password", UNCHECKABLE_PASSWORDS.values(), ids=UNCHECKABLE_PASSWORDS.keys()
)
def test_uncheckable_passwords_are_rejected_without_queries_hashes_or_signal(
    password, failed_logins
):
    account()

    with counted_hashes() as encode, CaptureQueriesContext(connection) as queries:
        user = check(EMAIL, password)

    assert user is None
    assert len(queries) == 0
    assert encode.call_count == 0
    assert failed_logins == []


@pytest.mark.parametrize(
    "email",
    ["ana", "  Ana@Correo.ES ", "a" * 4000, DIAERESIS + "ana@correo.es"],
    ids=["without-at-sign", "spaces-and-case", "4000-characters", "diaeresis"],
)
def test_any_other_email_is_queryable(email):
    assert is_queryable_email(email)


@pytest.mark.parametrize(
    "password",
    ["\x00", "vela\x00roja", "ñ" * 128],
    ids=["only-null", "null-inside", "128-code-points"],
)
def test_any_other_password_is_checkable(password):
    assert is_checkable_password(password)


# --- Recuento de hashes -------------------------------------------------------


def unknown_email():
    account()
    return "luis@correo.es", PASSWORD


def wrong_password():
    account()
    return EMAIL, WRONG_PASSWORD


def inactive_with_its_password():
    account(is_active=False)
    return EMAIL, PASSWORD


def inactive_with_a_wrong_password():
    account(is_active=False)
    return EMAIL, WRONG_PASSWORD


def unusable_password():
    account(password=None)
    return EMAIL, PASSWORD


@pytest.mark.parametrize(
    "prepare",
    [
        unknown_email,
        wrong_password,
        inactive_with_its_password,
        inactive_with_a_wrong_password,
        unusable_password,
    ],
)
def test_each_kind_of_wrong_credentials_computes_exactly_one_hash(prepare):
    email, password = prepare()
    stored = User.objects.get(email=EMAIL).password
    # Un hash de otro algoritmo daría un recuento falso
    assert not is_password_usable(stored) or identify_hasher(stored).algorithm == "md5"

    with counted_hashes() as encode:
        user = check(email, password)

    assert user is None
    assert encode.call_count == 1


def test_a_wrong_password_of_128_code_points_computes_one_hash():
    account()

    with counted_hashes() as encode:
        user = check(EMAIL, "ñ" * 128)

    assert user is None
    assert encode.call_count == 1


def test_an_email_without_at_sign_is_looked_up():
    account()

    with counted_hashes() as encode, CaptureQueriesContext(connection) as queries:
        user = check("ana", PASSWORD)

    assert user is None
    assert len(queries) == 1
    assert encode.call_count == 1


# --- Aciertos -----------------------------------------------------------------


@pytest.mark.parametrize(
    "email", ["  Ana@Correo.ES ", EMAIL], ids=["spaces-and-case", "normalized"]
)
def test_equivalent_spellings_of_the_email_return_the_account(email):
    created = account()

    assert check(email, PASSWORD) == created


def test_a_correct_password_with_a_null_character_returns_the_account():
    created = account(password="vela\x00roja")

    assert check(EMAIL, "vela\x00roja") == created


def test_a_correct_password_stored_with_an_old_hasher_is_rehashed(settings):
    settings.PASSWORD_HASHERS = [FAST_PBKDF2, MD5]
    created = User.objects.create(
        email=EMAIL, password=make_password(PASSWORD, hasher="md5")
    )
    assert identify_hasher(created.password).algorithm == "md5"

    assert check(EMAIL, PASSWORD) == created

    stored = User.objects.get(pk=created.pk).password
    assert identify_hasher(stored).algorithm == "pbkdf2_sha256"
    assert stored.split("$")[1] == str(FastPBKDF2PasswordHasher.iterations)


# --- Normalización ------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    ["  Ana@Correo.ES ", DIAERESIS + "ana@correo.es"],
    ids=["spaces-and-case", "diaeresis"],
)
def test_the_pair_key_and_the_lookup_receive_the_same_raw_email(raw, monkeypatch):
    account()
    normalized, looked_up = [], []
    original_normalize = UserManager.normalize_email.__func__
    original_lookup = UserManager.get_by_natural_key

    def spy_normalize(cls, email):
        normalized.append(email)
        return original_normalize(cls, email)

    def spy_lookup(self, email):
        looked_up.append(email)
        return original_lookup(self, email)

    monkeypatch.setattr(UserManager, "normalize_email", classmethod(spy_normalize))
    monkeypatch.setattr(UserManager, "get_by_natural_key", spy_lookup)

    login_pair_key("203.0.113.7", raw)
    check(raw, PASSWORD)

    assert looked_up == [raw]
    assert normalized == [raw, raw]


# --- Señales y errores --------------------------------------------------------


def test_user_login_failed_is_sent_once_with_the_raw_email_and_the_password_hidden(
    failed_logins,
):
    account()

    check("  Ana@Correo.ES ", WRONG_PASSWORD)

    assert failed_logins == [{"email": "  Ana@Correo.ES ", "password": HIDDEN}]


ODD_CREDENTIALS = {
    "email-null-inside": ("ana\x00@correo.es", PASSWORD),
    "email-lone-surrogate": (f"ana{SURROGATE}@correo.es", PASSWORD),
    "email-4000-characters": ("a" * 4000 + "@correo.es", PASSWORD),
    "email-quotes-and-percent": ("a'\"%_\\@correo.es", PASSWORD),
    "password-null-inside": (EMAIL, "vela\x00azul"),
    "password-lone-surrogate": (EMAIL, f"vela{SURROGATE}"),
}


@pytest.mark.parametrize(
    ("email", "password"), ODD_CREDENTIALS.values(), ids=ODD_CREDENTIALS.keys()
)
def test_no_content_of_the_email_or_password_raises(email, password):
    account()

    assert check(email, password) is None


# --- Variables sensibles ------------------------------------------------------


def test_the_error_report_hides_the_email_and_the_password(settings, monkeypatch):
    # El filtro de Django solo tapa con DEBUG desactivado
    settings.DEBUG = False

    def explode(*args, **kwargs):
        raise RuntimeError("authentication failed")

    monkeypatch.setattr(login, "authenticate", explode)
    request = RequestFactory().post("/")

    with pytest.raises(RuntimeError) as raised:
        check_credentials(
            request, email=f"{MARK}@correo.es", password=f"{MARK} vela roja"
        )

    reporter = ExceptionReporter(request, raised.type, raised.value, raised.tb)
    frame = next(
        frame
        for frame in reporter.get_traceback_frames()
        if frame["function"] == "check_credentials"
    )
    shown = dict(frame["vars"])
    assert shown["email"] == HIDDEN
    assert shown["password"] == HIDDEN
    assert MARK not in repr(frame["vars"])
