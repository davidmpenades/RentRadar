from django.conf import settings

CLEANER = "apps.core.middleware.CleanMarkedResponseMiddleware"
SESSION = "django.contrib.sessions.middleware.SessionMiddleware"
CSRF = "django.middleware.csrf.CsrfViewMiddleware"
AUTHENTICATION = "django.contrib.auth.middleware.AuthenticationMiddleware"

VALIDATORS_EXPECTED = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        ),
        "OPTIONS": {"user_attributes": ("email",)},
    },
]


def test_authentication_middleware_comes_right_after_csrf():
    # Exacto y no solo «después»: la lista pública no lo usa y funciona igual sin él
    middleware = settings.MIDDLEWARE

    assert AUTHENTICATION in middleware
    assert middleware.index(AUTHENTICATION) == middleware.index(CSRF) + 1


def test_session_and_csrf_stay_before_authentication():
    middleware = settings.MIDDLEWARE

    assert middleware.index(SESSION) < middleware.index(CSRF)
    assert middleware.index(CSRF) < middleware.index(AUTHENTICATION)


def test_the_cookie_cleaner_stays_first():
    assert settings.MIDDLEWARE[0] == CLEANER


def test_password_validators_and_their_order():
    assert settings.AUTH_PASSWORD_VALIDATORS == VALIDATORS_EXPECTED


def test_session_lasts_fourteen_days_without_renewal():
    assert settings.SESSION_COOKIE_AGE == 14 * 24 * 60 * 60
    assert settings.SESSION_SAVE_EVERY_REQUEST is False
    assert settings.SESSION_EXPIRE_AT_BROWSER_CLOSE is False


def test_the_csrf_cookie_and_header_names_are_the_ones_the_client_uses():
    assert settings.CSRF_COOKIE_NAME == "csrftoken"
    assert settings.CSRF_HEADER_NAME == "HTTP_X_CSRFTOKEN"
