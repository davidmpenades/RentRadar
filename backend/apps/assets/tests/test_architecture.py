import ast
from pathlib import Path

import pytest
from django.db.migrations.loader import MigrationLoader

BACKEND = Path(__file__).resolve().parents[3]
EXCLUDED_DIRECTORIES = {"migrations", "tests"}
SERVICES = "apps/assets/services.py"
MODELS = "apps/assets/models.py"
SELECTORS = "apps/assets/selectors.py"
ASSET_MODULES = {MODELS, SELECTORS, SERVICES}
ASSET_PACKAGE = "apps/assets/"
SERVICES_MODULE = "apps.assets.services"
WRITE_METHODS = {
    "save",
    "create",
    "update",
    "delete",
    "bulk_create",
    "bulk_update",
    "get_or_create",
    "update_or_create",
}
WRITE_FUNCTIONS = {"create_asset", "update_asset"}
# (código, paquete del fichero, ¿obtiene el modelo?)
IMPORT_FORMS = {
    "name": ("from apps.assets.models import Asset", "apps.core", True),
    "name_with_alias": ("from apps.assets.models import Asset as A", "apps.core", True),
    "star": ("from apps.assets.models import *", "apps.core", True),
    "module": ("from apps.assets import models", "apps.core", True),
    "module_with_alias": ("from apps.assets import models as m", "apps.core", True),
    "dotted_module": ("import apps.assets.models", "apps.core", True),
    "dotted_module_with_alias": ("import apps.assets.models as m", "apps.core", True),
    "relative_name": ("from .models import Asset", "apps.assets", True),
    "relative_module": ("from . import models", "apps.assets", True),
    "enum_only": ("from apps.assets.models import AssetStatus", "apps.core", False),
    "other_module": ("from apps.assets.rules import clean_title", "apps.core", False),
    "other_app": ("from apps.categories import models", "apps.core", False),
    "relative_in_other_app": ("from . import models", "apps.categories", False),
}
LOCATION_FORMS = {
    "name": ("from apps.assets.location import approximate_location", True),
    "module": ("from apps.assets import location", True),
    "module_with_alias": ("from apps.assets import location as place", True),
    "dotted_module_with_alias": ("import apps.assets.location as place", True),
    "constants_only": ("from apps.assets.location import PRIVACY_RADII", False),
}
# (código, paquete del fichero, ¿usa los servicios de bienes de forma no permitida?)
SERVICE_FORMS = {
    "writers": (
        "from apps.assets.services import create_asset, update_asset",
        "apps.users",
        False,
    ),
    "writer_with_alias": (
        "from apps.assets.services import create_asset as create",
        "apps.users",
        False,
    ),
    "model": ("from apps.assets.services import Asset", "apps.users", True),
    "approximation": (
        "from apps.assets.services import approximate_location",
        "apps.users",
        True,
    ),
    "writer_and_model": (
        "from apps.assets.services import create_asset, Asset",
        "apps.users",
        True,
    ),
    "private_function": (
        "from apps.assets.services import _public_location",
        "apps.users",
        True,
    ),
    "star": ("from apps.assets.services import *", "apps.users", True),
    "module": ("from apps.assets import services", "apps.users", True),
    "module_with_alias": ("from apps.assets import services as s", "apps.users", True),
    "dotted_module": ("import apps.assets.services", "apps.users", True),
    "dotted_module_with_alias": (
        "import apps.assets.services as s",
        "apps.users",
        True,
    ),
    "attribute_of_the_package": (
        "import apps.assets\nmodel = apps.assets.services.Asset",
        "apps.users",
        True,
    ),
    "attribute_of_the_app": (
        "from apps import assets\nmodel = assets.services.Asset",
        "apps.users",
        True,
    ),
    "services_of_another_app": (
        "from apps.categories.services import save_category",
        "apps.users",
        False,
    ),
    "relative_services_of_another_app": (
        "from .services import save_category",
        "apps.categories",
        False,
    ),
    "other_module_of_assets": (
        "from apps.assets.rules import clean_title",
        "apps.users",
        False,
    ),
}


def source_files():
    files = {}
    for root in ("apps", "config"):
        for path in (BACKEND / root).rglob("*.py"):
            relative = path.relative_to(BACKEND)
            if not EXCLUDED_DIRECTORIES & set(relative.parts):
                files[relative.as_posix()] = path.read_text()
    return files


def package_of(relative):
    return ".".join(Path(relative).parent.parts)


def origin_of(node, package):
    if node.level == 0:
        return node.module
    parts = package.split(".")[: len(package.split(".")) - (node.level - 1)]
    return ".".join([*parts, *([node.module] if node.module else [])])


# Si el código obtiene alguno de los nombres del módulo, o el módulo entero
def obtains(source, package, module, names):
    parent, _, last = module.rpartition(".")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            if any(alias.name == module for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            origin = origin_of(node, package)
            imported = {alias.name for alias in node.names}
            if origin == module and imported & (names | {"*"}):
                return True
            if origin == parent and last in imported:
                return True
    return False


def called_names(source):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            yield node, getattr(node.func, "attr", getattr(node.func, "id", None))


def gets_an_assets_model(source):
    return any(
        name == "get_model"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and str(node.args[0].value).startswith("assets")
        for node, name in called_names(source)
    )


def gets_the_assets_app_config(source):
    return any(
        name == "get_app_config"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "assets"
        for node, name in called_names(source)
    )


def write_calls(source):
    return {name for _, name in called_names(source) if name in WRITE_METHODS}


def public_functions(source):
    return {
        node.name
        for node in ast.parse(source).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }


def holders(module, names):
    return {
        relative
        for relative, source in source_files().items()
        if obtains(source, package_of(relative), module, names)
    }


def outside_the_asset_app():
    return {
        relative: source
        for relative, source in source_files().items()
        if not relative.startswith(ASSET_PACKAGE)
    }


# Si usa los servicios de bienes de otra forma que importando por nombre las escrituras
def misuses_the_service(source, package):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            if any(alias.name == SERVICES_MODULE for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            origin = origin_of(node, package)
            imported = {alias.name for alias in node.names}
            if origin == SERVICES_MODULE and not imported <= WRITE_FUNCTIONS:
                return True
            if origin == "apps.assets" and "services" in imported:
                return True
        elif isinstance(node, ast.Attribute) and node.attr == "services":
            owner = getattr(node.value, "attr", getattr(node.value, "id", None))
            if owner == "assets":
                return True
    return False


def test_the_asset_migration_does_not_depend_on_the_category_seed():
    plan = MigrationLoader(None).graph.forwards_plan(("assets", "0001_initial"))

    assert ("categories", "0001_initial") in plan
    assert ("categories", "0002_seed_categories") not in plan


@pytest.mark.parametrize(
    ("source", "package", "expected"), IMPORT_FORMS.values(), ids=IMPORT_FORMS
)
def test_the_detector_sees_every_way_to_get_the_asset_model(source, package, expected):
    assert obtains(source, package, "apps.assets.models", {"Asset"}) is expected


@pytest.mark.parametrize(
    ("source", "expected"), LOCATION_FORMS.values(), ids=LOCATION_FORMS
)
def test_the_detector_sees_every_way_to_get_the_approximation(source, expected):
    found = obtains(
        source, "apps.core", "apps.assets.location", {"approximate_location"}
    )

    assert found is expected


@pytest.mark.parametrize(
    ("source", "package", "expected"), SERVICE_FORMS.values(), ids=SERVICE_FORMS
)
def test_the_detector_sees_every_way_to_misuse_the_service(source, package, expected):
    assert misuses_the_service(source, package) is expected


def test_the_detector_sees_the_app_config_lookup():
    assert gets_the_assets_app_config('apps.get_app_config("assets")')
    assert gets_the_assets_app_config('get_app_config("assets").get_model("Asset")')
    assert not gets_the_assets_app_config('apps.get_app_config("users")')
    assert not gets_the_assets_app_config("apps.get_app_configs()")


def test_the_detector_sees_a_model_lookup_by_name_and_a_write_call():
    assert gets_an_assets_model('apps.get_model("assets", "Asset")')
    assert gets_an_assets_model('get_model("assets.Asset")')
    assert not gets_an_assets_model('apps.get_model("users", "User")')
    assert write_calls("Asset.objects.filter(pk=1).update(title='x')") == {"update"}
    assert write_calls("asset.save(update_fields=['title'])") == {"save"}
    assert write_calls("Asset.objects.filter(pk=1)") == set()


def test_the_scan_covers_the_code_and_finds_the_known_importer():
    files = source_files()

    assert MODELS in files
    assert len(files) > 10
    assert obtains(
        files[SERVICES], package_of(SERVICES), "apps.assets.models", {"Asset"}
    )


def test_only_the_asset_modules_get_the_asset_model():
    found = holders("apps.assets.models", {"Asset"})

    assert SERVICES in found
    assert found <= ASSET_MODULES


def test_nobody_looks_the_asset_model_up_by_name():
    offenders = [
        relative
        for relative, source in source_files().items()
        if gets_an_assets_model(source)
    ]

    assert offenders == []


def test_the_model_and_the_selectors_do_not_write():
    files = source_files()

    for relative in (MODELS, SELECTORS):
        if relative in files:
            assert write_calls(files[relative]) == set(), relative


def test_the_only_public_functions_of_the_service_are_the_two_writers():
    assert public_functions(source_files()[SERVICES]) == WRITE_FUNCTIONS


def test_only_the_service_gets_the_approximation():
    found = holders("apps.assets.location", {"approximate_location"})

    assert found == {SERVICES}


def test_the_scan_outside_the_asset_app_sees_the_other_apps():
    files = outside_the_asset_app()

    assert "apps/users/services.py" in files
    assert not [relative for relative in files if relative.startswith(ASSET_PACKAGE)]


def test_outside_the_asset_app_the_service_is_used_only_through_its_two_writers():
    offenders = [
        relative
        for relative, source in outside_the_asset_app().items()
        if misuses_the_service(source, package_of(relative))
    ]

    assert offenders == []


def test_nobody_outside_the_asset_app_reaches_it_through_the_app_registry():
    offenders = [
        relative
        for relative, source in outside_the_asset_app().items()
        if gets_the_assets_app_config(source)
    ]

    assert offenders == []
