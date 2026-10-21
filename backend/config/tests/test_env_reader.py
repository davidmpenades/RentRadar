import ast

from django.conf import settings

BACKEND_DIR = settings.BASE_DIR
ENV_READER = BACKEND_DIR / "config" / "env.py"
ENVIRONMENT_NAMES = {"environ", "environb", "getenv", "getenvb", "putenv", "unsetenv"}
SKIPPED_DIRS = {"tests", ".venv", "venv", "__pycache__", "node_modules"}


def production_sources():
    for path in BACKEND_DIR.rglob("*.py"):
        relative = path.relative_to(BACKEND_DIR)
        if SKIPPED_DIRS.isdisjoint(relative.parts) and path.name != "conftest.py":
            yield path


def environment_accesses(tree):
    """Líneas donde el módulo toca el entorno del proceso, con o sin alias de `os`."""
    os_aliases = set()
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            # "import os.path" sin alias también deja el nombre "os" disponible
            os_aliases |= {
                a.asname or "os"
                for a in node.names
                if a.name == "os" or (a.name.startswith("os.") and a.asname is None)
            }
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module == "os"
            and any(a.name in ENVIRONMENT_NAMES for a in node.names)
        ):
            lines.append(node.lineno)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and node.attr in ENVIRONMENT_NAMES
            and isinstance(node.value, ast.Name)
            and node.value.id in os_aliases
        ):
            lines.append(node.lineno)
    return lines


def test_only_env_module_reads_the_environment():
    offenders = {
        str(path.relative_to(BACKEND_DIR)): lines
        for path in production_sources()
        if path != ENV_READER
        and (lines := environment_accesses(ast.parse(path.read_text(encoding="utf-8"))))
    }
    assert offenders == {}


def test_scan_covers_entrypoints_and_detects_the_reader():
    scanned = {p.name for p in production_sources()}
    assert {"manage.py", "wsgi.py", "asgi.py", "env.py"} <= scanned
    assert environment_accesses(ast.parse(ENV_READER.read_text(encoding="utf-8")))


def test_detector_catches_every_access_form():
    forms = [
        "import os\nos.getenv('A')",
        "import os\nos.environ['A']",
        "import os as o\no.environ.get('A')",
        "import os.path\nos.environ['A']",
        "from os import environ",
        "from os import getenv as g",
    ]
    for source in forms:
        assert environment_accesses(ast.parse(source)), source
    assert not environment_accesses(ast.parse("import os\nos.path.join('a')"))
