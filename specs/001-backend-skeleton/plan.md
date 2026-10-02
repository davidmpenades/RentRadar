# Plan 001 — Esqueleto del backend
Spec: specs/001-backend-skeleton/spec.md (aprobada)

## Resumen
Proyecto Django 5.2 sin DRF, con un paquete de settings por entorno (`development`, `test`, `production`). Un resolvedor compartido por `manage.py`, `wsgi.py` y `asgi.py` traduce `DJANGO_ENV` al módulo de settings. Un único módulo, `config/env.py`, lee `os.environ`. Sus funciones son puras (reciben el entorno como parámetro), acumulan todos los errores y nunca incluyen valores en los mensajes.

Para la base de datos se usa PostGIS 18-3.6 en Docker Compose. La extensión se crea con una migración en una app mínima, `apps/core` (las apps de dominio irán también en `apps/`), que también aloja la espera a la base de datos (`wait_for_db`, con reloj y `sleep` inyectados). La imagen del backend es `python:3.13-slim-trixie`, con usuario no root y las dependencias fijadas con hashes (pip-tools). Producción usa las vistas de error genéricas de Django, un LOGGING explícito con un formatter que redacta secretos y cookies endurecidas. La estructura del backend queda documentada en `docs/architecture.md`.

## Archivos y responsabilidades
| Archivo | Crea/Modifica | Responsabilidad | RF |
|---|---|---|---|
| `.gitignore` | Modifica | `.env*`, `*.env`, `!.env.example`, `.pytest_cache/`, `.ruff_cache/`, `.venv/` | RF-8 |
| `.env.example` | Modifica | Bloque del backend con descripción por variable y valores `insecure-…`, aviso de que Compose interpola `$`, y bloque comentado "Ajeno al backend" con `CONTEXT7_API_KEY` vacía | RF-26, RF-27, RF-28 |
| `docker-compose.yml` | Crea | Servicios `db` (postgis/postgis:18-3.6, healthcheck `pg_isready -h 127.0.0.1`, volumen con nombre en `/var/lib/postgresql`, `127.0.0.1:5432`) y `backend` (build `backend/` target `dev`, `environment:` explícito con `${VAR:?}` en las obligatorias, sin `env_file`, `127.0.0.1:8000`, bind `./backend:/app`, `./.env.example:/.env.example:ro`, `RUFF_NO_CACHE=true`, `depends_on: service_healthy`) | RF-1, RF-2, RF-3, RF-7 |
| `AGENTS.md` | Modifica | Añade a "Comandos" la orden de lint: `docker compose exec backend sh -c "ruff check . && ruff format --check ."` (aprobado) | RF-35 |
| `docs/architecture.md` | Crea | Estructura del backend: `config/` (settings, env, logging), `apps/<app>/` por dominio, capas (servicios, selectores, serializers, vistas), ubicación de tests y migraciones | — |
| `backend/Dockerfile` | Crea | `python:3.13-slim-trixie` con `libgdal36`, `libgeos-c1t64` y `libproj25` (`--no-install-recommends`). Etapa `runtime` (requirements.txt) y etapa `dev` (+ requirements-dev.txt), `pip install --require-hashes`, `PYTHONDONTWRITEBYTECODE=1`, código propiedad de root, `USER 10001`, `ENTRYPOINT` | RF-6, RNF reproducibilidad |
| `backend/.dockerignore` | Crea | Excluye `.env*`, `.git`, cachés y `__pycache__` | RNF seguridad |
| `backend/requirements.in` / `.txt` | Crea | Django 5.2.17 y psycopg[binary] 3.3.x; el `.txt` lleva hashes (pip-compile) | RNF reproducibilidad |
| `backend/requirements-dev.in` / `.txt` | Crea | pytest, pytest-django 4.14.0 y ruff 0.16.10, con `-c requirements.txt` y hashes | RF-33, RF-35 |
| `backend/pyproject.toml` | Crea | `[tool.ruff]` con select E, F, I, UP, B, SIM y DJ, más `[tool.ruff.format]`. `[tool.pytest.ini_options]` con `addopts = "--ds=config.settings.test -p no:cacheprovider"`, sin `-l` ni `--reuse-db` | RF-33, RF-35 |
| `backend/docker-entrypoint.sh` | Crea | `set -eu`, `python manage.py wait_for_db` y `exec "$@"`. Sin `set -x`, sin `env` y sin imprimir variables | RF-3, RF-4 |
| `backend/manage.py` | Crea | Resolvedor y carga forzada de settings dentro de `try`. Ante `ImproperlyConfigured`, sale con `sys.exit("Error de configuración: …")`, sin traza | RF-9, RF-10 |
| `backend/config/env.py` | Crea | Único lector de `os.environ`. Contiene `KNOWN_VARIABLES`, el resolvedor, `parse_bool`, los validadores y el cargador de producción | RF-9 a RF-15, RF-20, RF-26 |
| `backend/config/settings/base.py` | Crea | Comunes: `DEBUG=False`, `INSTALLED_APPS` (sessions, gis, `apps.core`), `MIDDLEWARE` (Security, Session, Common, Csrf, XFrame), `ROOT_URLCONF`, `USE_TZ`, `TIME_ZONE="UTC"`, `LANGUAGE_CODE="es"`, `USE_I18N`, cookies y `build_database()` (CONN_MAX_AGE 0, `connect_timeout` 5) | RF-16, RF-24, RF-25, RF-29 a RF-32 |
| `backend/config/settings/development.py` | Crea | Clave y base de datos desde el entorno, `DEBUG` según `DJANGO_DEBUG`, `ALLOWED_HOSTS` literal `["localhost", "127.0.0.1"]` | RF-18 |
| `backend/config/settings/test.py` | Crea | `SECRET_KEY` literal `insecure-test-only-not-a-secret` (excepción acotada al principio 6), `DEBUG=False`, `NAME` y `TEST["NAME"]` literales `rentradar_test`; valida `DJANGO_DEBUG` y la descarta | RF-17, RF-19, RF-20, RF-34 |
| `backend/config/settings/production.py` | Crea | Llama a `load_production_config()`, `DEBUG=False`, cookies `Secure` y `LOGGING` con redacción | RF-11 a RF-15, RF-19, RF-22, RF-23 |
| `backend/config/log_redaction.py` | Crea | `RedactingFormatter(secrets)` y `build_production_logging(secrets)` | RF-22 |
| `backend/config/urls.py` | Crea | `urlpatterns = []` (sin admin) | RF-21 |
| `backend/config/wsgi.py`, `asgi.py` | Crea | Resolvedor sin `setdefault` | RF-10 |
| `backend/apps/__init__.py`, `backend/apps/core/` (`apps.py` con `name = "apps.core"`, `migrations/0001_postgis_extension.py`) | Crea | App mínima con `CreateExtension("postgis")` | RF-5 |
| `backend/apps/core/db_wait.py` | Crea | `wait_until_available(check, clock, sleep, timeout, interval)` | RF-3, RF-4 |
| `backend/apps/core/management/commands/wait_for_db.py` | Crea | Llama a la función con `ensure_connection`, `time.monotonic` y `time.sleep` (atributos del módulo). Mensaje fijo y `CommandError` | RF-3, RF-4 |
| `backend/conftest.py` | Crea | Guarda de la base de datos de test (aborta si el nombre no contiene `test` o coincide con `DB_NAME`) y fixture autouse que bloquea la red | RF-34, RNF aislamiento |
| `backend/config/tests/` | Crea | `conftest.py` (fixture `load_settings`), `urls.py` y vistas de prueba, y tests por bloque | Ver estrategia |
| `backend/apps/core/tests/` | Crea | Tests de PostGIS, de `db_wait` y de `wait_for_db` | RF-3 a RF-5 |

## Modelo de datos y migraciones
- `apps/core/migrations/0001_postgis_extension.py`: `CreateExtension("postgis")`. **Aprobada por el usuario (P3).** Funciona igual en local, en CI y en una base de datos gestionada. Antes del commit se revisa con `sqlmigrate`.
- `django.contrib.sessions` crea la tabla `django_session` con su migración propia. Hace falta para que RF-24 y RF-25 se prueben con una cookie de sesión real. **Aprobada por el usuario (D11).**
- No hay modelos de dominio. `makemigrations --check --dry-run` debe quedar limpio.
- En desarrollo, las migraciones se aplican a mano (`docker compose exec backend python manage.py migrate`). Aplicarlas al arrancar está fuera de alcance.

## Contrato de API
No hay endpoints propios y DRF no entra en esta spec (P6). En producción, las respuestas de error son las vistas por defecto de Django con `DEBUG=False`:
| Caso | Código | Cuerpo |
|---|---|---|
| Host no permitido | 400 | HTML genérico "Bad Request (400)" |
| Ruta inexistente | 404 | HTML genérico "Not Found", sin la ruta |
| Método no permitido | 405 | Vacío, con cabecera `Allow` |
| Error no controlado | 500 | HTML genérico "Server Error (500)" |
No hay plantillas 4xx/5xx ni handlers propios.

## Lógica
Todo está en `config/env.py`, que es el único módulo que toca `os.environ`. Cada función recibe `environ: Mapping[str, str] | None` y usa `os.environ` cuando es `None`:
- `KNOWN_VARIABLES`: `DJANGO_ENV`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`. El lector interno lanza un error de programación si se pide un nombre que no está en el conjunto. Eso hace que el test de RF-26 tenga sentido.
- `resolve_settings_module(environ) -> str`: admite exactamente `development`, `test` y `production`. En otro caso lanza `ImproperlyConfigured`, que lista los valores válidos.
- `configure_settings_module(environ)`: escribe `DJANGO_SETTINGS_MODULE` y siempre sobrescribe un valor previo.
- `parse_bool(name, raw) -> bool`: un valor ausente o vacío es `False`. Admite `true`, `false`, `1` y `0` sin distinguir mayúsculas. Cualquier otro valor lanza un error que nombra la variable.
- `require(environ, names) -> dict`: aplica strip, trata el vacío como ausente y acumula todos los que faltan.
- `parse_port(name, raw)`: entero entre 1 y 65535. Usa `raise … from None`.
- `parse_allowed_hosts(name, raw) -> list[str]`: separa por comas, ignora los vacíos y acepta un dominio, `.dominio` o una IP (`ipaddress`). Rechaza `*`, esquemas, puertos y rutas.
- `load_production_config(environ) -> ProductionConfig` (dataclass congelada): reúne todos los problemas (faltantes, puerto, longitud de la clave, `insecure-` en la clave o la contraseña, hosts) y lanza una sola `ImproperlyConfigured` que solo contiene nombres y motivos.
- `read_optional(environ, name)`: la usa la guarda de `conftest.py`.

Fuera de `config/env.py`:
- `apps/core/db_wait.py`: `wait_until_available(check, clock, sleep, timeout=60.0, interval=1.0) -> bool`. Captura solo `OperationalError` y no guarda ni devuelve la excepción.
- `config/log_redaction.py`: `RedactingFormatter.format()` sustituye cada secreto no vacío por `[REDACTED]` en el texto final, traza incluida.

Orden de arranque: el resolvedor y los settings (que validan) van primero, después `wait_for_db` y por último `exec` del proceso.

## Interfaz
No aplica: no hay interfaz de usuario. Los mensajes para el desarrollador van en castellano.

## Decisiones
| Decisión | Opciones | Elegida | Qué evita | Coste |
|---|---|---|---|---|
| D1 Motor de BD | PostgreSQL normal / postgis desde ya | `django.contrib.gis.db.backends.postgis` (P1) | Cambiar de motor cuando llegue el dominio; cumple RF-5 | Se necesitan GDAL, GEOS y PROJ en la imagen |
| D2 Imagen de BD | 17-3.4 (congelada, bullseye) / 17-3.5 (bullseye) / 18-3.6 (trixie) | `postgis/postgis:18-3.6` (P2), la misma etiqueta en CI (spec 002) | Imágenes congeladas o sin mantenimiento | **Riesgo:** PostGIS 3.6 queda fuera del rango 3.1-3.4 que declara Django 5.2 ("pueden funcionar"). Mitigación: el test de RF-5 corre en cada suite. Vuelta atrás: 17-3.5, también fuera de rango y sobre bullseye. En PG18 el volumen se monta en `/var/lib/postgresql` |
| D3 Extensión postgis | Script de initdb / migración | Migración `CreateExtension` (P3, aprobada) | Diferencias entre local, CI y BD gestionada | Una migración en `apps/core`; exige superusuario o extensión permitida |
| D4 Espera a la BD | Solo `depends_on` / script con `pg_isready` / comando de gestión | `wait_for_db` con reloj y `sleep` inyectados, 60 s y mensaje fijo (P4) | Arranques fallidos por carrera; fugas de host y usuario vía `str(exc)`; binarios cliente en la imagen | Un comando y su test |
| D5 Locks | `pip freeze` / uv / pip-tools | pip-tools 7.6.1 con `--generate-hashes`, compilado dentro de `python:3.13-slim-trixie` (P5, aprobada) | Instalaciones no reproducibles; marcadores de otra plataforma | Herramienta nueva que no se instala en la imagen. Orden documentada al principio de cada `.in` |
| D6 DRF | Ahora / con el primer endpoint | Fuera de la 001 (P6) | Una dependencia sin uso | La spec 003 o la primera de dominio la añade |
| D7 Lectura del entorno | django-environ / environs / módulo propio | `config/env.py` propio | django-environ acepta `yes` y `on` (contradice RF-20); dependencias no aprobadas | Unas 100 líneas propias con tests puros |
| D8 Selección de settings | Un fichero con condicionales / paquete por entorno + `DJANGO_ENV` | Paquete y resolvedor que siempre sobrescribe `DJANGO_SETTINGS_MODULE` | Defaults inseguros de `startproject` (`setdefault`, `django-insecure`, `DEBUG=True`) | Tres puntos de entrada usan el resolvedor |
| D9 Clave de test | Leerla del entorno / literal | Literal `insecure-test-only-not-a-secret` (P7). **Excepción acotada al principio 6**, coherente con RF-14: producción la rechazaría | Depender de `.env` para correr los tests (RF-33) | Ninguno, no es un secreto |
| D10 Cookies | — | Sesión `HttpOnly`; CSRF legible por el frontend (`CSRF_COOKIE_HTTPONLY=False`, `CSRF_USE_SESSIONS=False`); `SameSite=Lax` en ambas; `Secure` solo en `production` | Que el frontend no pueda enviar el token CSRF; robo de la sesión por XSS | **Riesgo aceptado:** un XSS puede leer el token CSRF |
| D11 Backend de sesión | BD (por defecto) / cookies firmadas / caché | BD por defecto, con la migración de `django.contrib.sessions` (aprobada) | Cookies firmadas con datos en el cliente; caché compartida (dependencia) | Una tabla más |
| D12 Plantilla en tests | Comprobarla solo en el host / copiarla a `backend/` / montarla en solo lectura | Montaje `./.env.example:/.env.example:ro`; el test la busca en `BASE_DIR.parent / ".env.example"` (vale en el host, en CI y en el contenedor) (aprobada) | Montar la raíz del repo (expondría `.env`); duplicar la plantilla | Un montaje extra en Compose |
| D13 Secretos en logs | Confiar en que no aparezcan / formatter que redacta | `RedactingFormatter` con la clave y la contraseña de BD (aprobada) | Que el mensaje de una excepción filtre la contraseña (RF-22) | Una clase pequeña |
| D14 Red en tests | pytest-socket / fixture propio | Fixture autouse que parchea `socket.socket.connect`, `create_connection` y `getaddrinfo` para AF_INET y AF_INET6 | Una dependencia no aprobada | No cubre libpq (deseado) ni los subprocesos (límite declarado) |
| D15 BD de test | `test_` + `DB_NAME` / literal | `NAME = TEST["NAME"] = "rentradar_test"` y guarda en `conftest.py`; sin `--reuse-db` | Tocar la BD de desarrollo (RF-34) | Ninguno |
| D16 Errores en producción | Plantillas propias / vistas por defecto | Vistas por defecto con `DEBUG=False` | Mantener plantillas que podrían filtrar datos | Cuerpo HTML en inglés, aceptable para 4xx/5xx sin interfaz |
| D17 Usuario del contenedor | root / UID del host / UID fijo | UID 10001 fijo, sin `chown` ni `gosu` | Escalada en el contenedor (RF-6) | `makemigrations` no puede escribir en el bind mount; se usa `docker compose exec -u "$(id -u)" backend …` |
| D18 Ubicación de apps | Raíz de `backend/` / `backend/apps/` | `backend/apps/<app>/`; `core` es la primera y las de dominio irán ahí (decisión del usuario) | Mezclar apps con `config/` en la raíz | `name = "apps.<app>"` en cada `AppConfig` |

## Blast radius
- Se modifican `.gitignore` (cambia la línea `.env`), `.env.example` (se reorganiza y conserva `CONTEXT7_API_KEY` en el bloque ajeno) y `AGENTS.md` (orden de lint).
- Se crea `docs/architecture.md`, al que ya remite la skill django-drf.
- Todo lo demás es nuevo: `backend/**`, `docker-compose.yml`, `backend/.dockerignore` y el entrypoint. No hay tests previos que puedan romperse.
- El implementer no toca `MEMORY.md`.
- Contratos que heredan las specs 002 y 003:
  - nombres de variables: `DJANGO_ENV`, `DJANGO_*` y `DB_*`;
  - BD de test `rentradar_test`;
  - etiqueta `postgis/postgis:18-3.6`;
  - órdenes de test y lint;
  - orden de arranque: validar, esperar y ejecutar.
- Para la spec de despliegue: `SECURE_PROXY_SSL_HEADER`, `CSRF_TRUSTED_ORIGINS`, servidor e imagen de producción.

## Riesgos
| Riesgo | Mitigación |
|---|---|
| PostGIS 3.6 y PG18 fuera del rango declarado por Django 5.2 | El test de RF-5 corre en cada suite; vuelta atrás documentada en D2 |
| GeoDjango no encuentra `libgdal.so.36` o `libgeos_c` sin los paquetes `-dev` | T1 comprueba `gdal_version()` y `geos_version()`. Si falla, `GDAL_LIBRARY_PATH` y `GEOS_LIBRARY_PATH` literales en `base.py` (no por entorno) |
| Valores filtrados en mensajes o trazas (`int()`, `ipaddress`, psycopg) | `raise … from None`, mensajes con solo nombres, `manage.py` sin traza, tests en subproceso con centinelas |
| `ManagementUtility` captura `ImproperlyConfigured` en algunos subcomandos | `manage.py` fuerza la carga de settings dentro de su propio `try` antes de `execute_from_command_line` |
| BD de test huérfana tras una ejecución abortada | pytest-django no interactivo la recrea; se verifica en la validación |
| La recarga de módulos de settings en tests deja estado cruzado | La fixture `load_settings` usa `monkeypatch` y saca los módulos de `sys.modules` antes y después |
| Permisos del bind mount con UID 10001 | Sin `.pyc` ni cachés de pytest y ruff; `makemigrations` con `-u` (D17) |
| La etiqueta de imagen se mueve (`python:3.13-slim-trixie`, `18-3.6`) | Se acepta en la 001; fijar por digest se puede valorar en la spec de despliegue |
| Un XSS lee la cookie CSRF | Riesgo aceptado (D10); la sesión es `HttpOnly` |
| `.env` sin una variable obligatoria: Compose se niega a arrancar | Es lo deseado (`${VAR:?}`); el mensaje nombra la variable, no su valor |

## Estrategia de tests
| RF | Cómo se verifica |
|---|---|
| RF-1 | Validación: clon nuevo, `cp .env.example .env`, `docker compose up -d` y respuesta en `127.0.0.1:8000` |
| RF-2 | Validación: fila centinela en la BD de desarrollo, `down` y `up`, la fila sigue; `down -v` la borra |
| RF-3 | pytest: `wait_until_available` con un `check` que falla dos veces y luego funciona devuelve `True` y llama a `sleep`. Validación: `up --no-deps backend` con la BD parada y arranque de la BD antes de 60 s |
| RF-4 | pytest: un `check` que siempre falla, con reloj falso, devuelve `False` a los 60 s; `call_command("wait_for_db")` con un `OperationalError` que contiene host y usuario centinela lanza `CommandError` con mensaje fijo y sin centinelas |
| RF-5 | pytest: `ST_Distance` en geography entre Madrid y Barcelona da 505 km ±1 %. Validación: `migrate` en desarrollo aplica 0001 |
| RF-6 | pytest: `os.geteuid() != 0` dentro del contenedor. Validación: `docker compose exec backend id -u` da 10001 |
| RF-7 | Validación: `docker compose config --format json` analizado sin imprimirlo; los puertos publicados tienen `host_ip` 127.0.0.1 |
| RF-8 | Validación: `git check-ignore` sobre `.env`, `.env.local`, `.env.production`, `.env.development.local`, `prod.env` y `backend/.env` (ignorados) y `.env.example` (no ignorado) |
| RF-9 | pytest: `resolve_settings_module` con los tres valores; `load_settings` importa los tres módulos |
| RF-10 | pytest en subproceso: `manage.py check` sin `DJANGO_ENV`, con `Production` y con `prod` sale con código ≠0 y lista los valores válidos; lo mismo al importar `config.wsgi` y `config.asgi` |
| RF-11 | pytest: `load_production_config({})` nombra las 8 variables obligatorias; vacío o solo espacios cuenta como ausente. Subproceso con centinelas |
| RF-12 | pytest: puerto `abc`, `0` y `70000`. Subproceso: el centinela no aparece en stdout ni en stderr |
| RF-13 | pytest: clave de 49 caracteres rechazada y de 50 aceptada. Subproceso sin el valor en la salida |
| RF-14 | pytest: `insecure-` en una clave de 50 o más caracteres y en la contraseña; la contraseña de la plantilla se rechaza. Subproceso |
| RF-15 | pytest: `*` y `http://example.com` rechazados; `.example.com`, `example.com` y una IP aceptados; espacios y vacíos ignorados. Subproceso |
| RF-16 | pytest: `CommonMiddleware` en `MIDDLEWARE`; con `ALLOWED_HOSTS=["example.com"]`, una petición a `evil.test` da 400 con cuerpo genérico |
| RF-17 | pytest: `connection.settings_dict["NAME"] == "rentradar_test"`. Validación: abortar una ejecución y relanzar sin intervención |
| RF-18 | pytest (matriz): en `development`, `DEBUG` sigue a `DJANGO_DEBUG` (`true`, `1`, `TRUE`, `false`, `0`, ausente y vacío) |
| RF-19 | pytest (matriz): en `test` y `production`, `DEBUG` es `False` con `DJANGO_DEBUG=true` |
| RF-20 | pytest: `parse_bool` con `yes` y `on` lanza error. Matriz: los tres entornos lanzan `ImproperlyConfigured` nombrando `DJANGO_DEBUG` |
| RF-21 | pytest con urlconf de test (`override_settings`): 400, 404, 405 y 500 sin `Traceback`, `/app/`, `SELECT` ni la clave de test |
| RF-22 | pytest: `dictConfig` con `build_production_logging` sobre `StringIO` y vista que lanza una excepción con la clave y la contraseña centinela; el log contiene "Internal Server Error" y no los centinelas |
| RF-23 | pytest: el módulo de producción cargado tiene `SESSION_COOKIE_SECURE` y `CSRF_COOKIE_SECURE`; `Set-Cookie` real con esos valores lleva `Secure` |
| RF-24 | pytest: `Set-Cookie` de `sessionid` con `HttpOnly`; `csrftoken` sin `HttpOnly` |
| RF-25 | pytest: `SameSite=Lax` en ambas cookies, en los tres módulos |
| RF-26 | pytest: `KNOWN_VARIABLES` coincide con las claves del bloque del backend de la plantilla. Test AST: `os.environ` y `os.getenv` solo aparecen en `config/env.py` (excluidos los tests) |
| RF-27 | pytest: la clave y la contraseña de la plantilla contienen `insecure-` |
| RF-28 | pytest: el bloque tras el marcador "Ajeno al backend" se ignora y `CONTEXT7_API_KEY` está vacía |
| RF-29 | pytest: `USE_TZ` en los tres módulos; `timezone.now().tzinfo` es UTC |
| RF-30 | pytest: `TIME_ZONE == "UTC"` en los tres módulos |
| RF-31 | pytest: `LANGUAGE_CODE == "es"` en los tres módulos |
| RF-32 | pytest: `USE_I18N` en los tres módulos |
| RF-33 | pytest: `settings.SETTINGS_MODULE == "config.settings.test"`; subproceso `pytest -c pyproject.toml` sobre un test que falla, sin `DJANGO_ENV` ni `DJANGO_SETTINGS_MODULE`, sale con código ≠0 |
| RF-34 | pytest: la guarda de `conftest.py` aborta con un nombre sin `test` o igual a `DB_NAME` (función pura). Validación: fila centinela en la BD de desarrollo intacta tras la suite |
| RF-35 | pytest en subproceso: `ruff check` y `ruff format --check` con la configuración del proyecto, sin `DJANGO_ENV`, dan ≠0 sobre un fichero con infracciones y 0 sobre el código del backend |
| RNF aislamiento | pytest: `socket.create_connection(("example.com", 80))` falla dentro de un test |
| RNF reproducibilidad | Validación: `pip install --require-hashes` en el build; lock sin entradas sin hash |

## Afirmaciones no verificadas
- Django 5.2.17 funciona con PostGIS 3.6, PG18, GDAL de trixie (libgdal36, 3.10.x), GEOS 3.13 y PROJ 9.x. Django no declara PostGIS 3.6.
- `ctypes.util.find_library` encuentra `libgdal.so.36` y `libgeos_c.so.1` en slim sin los paquetes `-dev`, a través de `ldconfig`.
- `manage.py check` en producción no abre conexión a la BD.
- pytest-django, en modo no interactivo, sustituye una BD de test huérfana sin preguntar.
- La migración `CreateExtension` funciona sobre la BD de test creada desde `template1` con el usuario `POSTGRES_USER` (superusuario en la imagen).
- La imagen postgis/postgis:18-3.6 crea la extensión en `POSTGRES_DB` en initdb, y `IF NOT EXISTS` la hace idempotente.
- `dictConfig` con `LOGGING` explícito sustituye los handlers de `DEFAULT_LOGGING` en `django` y `django.request`, y no queda `mail_admins` activo.
- Parchear `socket` no afecta a la conexión de psycopg con libpq.
- `RUFF_NO_CACHE=true` desactiva la caché de ruff en la versión 0.16.10.

## Skills que aplican
- sdd (flujo, plantillas y una tarea cada vez).
- django-drf: capas, migraciones (preguntar y `sqlmigrate`), dependencias con hashes, tests en `tests/` por app y reinicio al añadir apps. Las partes de DRF no aplican.
- testing: todavía no existe. Las reglas de red y de centinelas quedan en este plan.
