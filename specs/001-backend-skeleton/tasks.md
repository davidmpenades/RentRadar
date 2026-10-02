# Tareas 001 — Esqueleto del backend
Antes de cada commit: `docker compose exec backend pytest -q` y `docker compose exec backend sh -c "ruff check . && ruff format --check ."` en verde (T1 y T2 usan `docker compose run --rm backend …` porque aún no hay `manage.py`). Test primero, fallando por la razón esperada.

- [ ] **T1. Imagen, dependencias fijadas, Compose y plantilla.** RF-2, RF-6, RF-7, RF-8, RF-27, RF-28
  - Sin test automático (infraestructura sin aplicación todavía); se verifica con órdenes.
  - Ficheros: `backend/Dockerfile` (`runtime` y `dev`, UID 10001), `.dockerignore`, `requirements*.in/.txt` con hashes, `pyproject.toml` (ruff y pytest sin `--ds`), `docker-compose.yml`, `.gitignore`, `.env.example` (bloques del backend y ajeno) y la orden de lint en `AGENTS.md`.
  - Commit: `build: add backend image, pinned deps and compose stack`
  - Hecho cuando: `docker compose build` termina con `--require-hashes`; `db` queda healthy; `docker compose run --rm backend python -c "from django.contrib.gis.gdal import gdal_version; from django.contrib.gis.geos import geos_version; print(gdal_version(), geos_version())"` imprime las versiones; `docker compose run --rm backend id -u` da 10001; `ruff check .` y `ruff format --check .` dan 0; `git check-ignore` cumple la lista de RF-8; `docker compose config` muestra los puertos en 127.0.0.1.

- [ ] **T2. Lectura y validación del entorno.** RF-9, RF-11, RF-12, RF-13, RF-14, RF-15, RF-20
  - `config/env.py` con funciones puras y tests unitarios en `config/tests/test_env.py`, sin Django configurado.
  - Commit: `feat(config): add environment variable parsing and validation`
  - Hecho cuando: `docker compose run --rm backend pytest -q config/tests/test_env.py` pasa; los tests cubren todos los faltantes a la vez, vacío o solo espacios, puerto `abc`, `0` y `70000`, clave de 49 y 50 caracteres, `insecure-` en la clave y la contraseña, hosts `*`, `http://example.com`, `.example.com`, IP y espacios, y `parse_bool` con `yes` y `on`; ningún mensaje contiene el valor recibido.

- [ ] **T3. Settings por entorno, resolvedor y arquitectura.** RF-9, RF-10, RF-18, RF-19, RF-20, RF-29, RF-30, RF-31, RF-32
  - `base.py`, `development.py` y `test.py`; `manage.py`, `wsgi.py` y `asgi.py` con el resolvedor; `urls.py` vacío; `--ds=config.settings.test -p no:cacheprovider` en `addopts`; fixture `load_settings`.
  - `docs/architecture.md` con la estructura del backend: `config/` (settings por entorno, `env.py`, logging), `apps/<app>/` para cada app (`core` y las de dominio), capas (servicios, selectores, serializers y vistas), y ubicación de tests y migraciones.
  - Commit: `feat(config): add per-environment settings and resolver`
  - Hecho cuando: pasan la matriz de `DEBUG` en development y test, los tests de hora e idioma por módulo y los subprocesos de RF-10 (sin variable, `Production` y `prod`, con `manage.py check`, `config.wsgi` y `config.asgi`); `docker compose up -d` deja runserver respondiendo en 127.0.0.1:8000; `docs/architecture.md` describe la estructura real creada hasta aquí y la prevista en `apps/`.

- [ ] **T4. Producción rechaza la configuración insegura.** RF-11, RF-12, RF-13, RF-14, RF-15, RF-19, RF-20
  - `production.py` con `load_production_config()` y `DEBUG=False`; tests en subproceso con entorno limpio y centinelas.
  - Commit: `feat(config): reject unsafe production configuration`
  - Hecho cuando: cada caso inseguro sale con código ≠0, nombra la variable y ningún centinela aparece en stdout ni stderr; una configuración válida de centinelas pasa `manage.py check` con código 0; `DEBUG` es `False` en producción con `DJANGO_DEBUG=true`.

- [ ] **T5. BD de test aislada con PostGIS.** RF-5, RF-17, RF-34
  - App `apps/core` (`name = "apps.core"`) con `0001_postgis_extension` (aprobada, revisada con `sqlmigrate`), `NAME` y `TEST["NAME"]` literales y guarda en `conftest.py`. Reiniciar el backend al añadir la app.
  - Commit: `feat(core): enable postgis in an isolated test database`
  - Hecho cuando: el test de distancia Madrid-Barcelona pasa (505 km ±1 %), el de nombre de BD y el de la guarda también; `makemigrations --check --dry-run` está limpio; `migrate` en desarrollo aplica 0001.

- [ ] **T6. Respuestas de error genéricas y cookies endurecidas.** RF-16, RF-21, RF-23, RF-24, RF-25
  - Urlconf y vistas de test; cookies en `base.py` y `production.py`; `django.contrib.sessions` (migración aprobada, D11).
  - Commit: `feat(config): harden error responses and cookies`
  - Hecho cuando: 400, 404, 405 y 500 son genéricos y sin marcadores prohibidos; `sessionid` lleva `HttpOnly` y `SameSite=Lax`; `csrftoken` no lleva `HttpOnly` y sí `SameSite=Lax`; con los valores de producción ambas llevan `Secure`. Prueba de mecanismo: quitar `CommonMiddleware` hace fallar RF-16, y después se restaura.

- [ ] **T7. Log de producción sin secretos.** RF-22
  - `config/log_redaction.py` y `LOGGING` en `production.py` con `StreamHandler` para `django.request` y `django.security`, sin ADMINS.
  - Commit: `feat(config): redact secrets from production logs`
  - Hecho cuando: el test con la clave y la contraseña centinela en el mensaje de la excepción no las encuentra en el log y sí encuentra "Internal Server Error". Prueba de mecanismo: con el formatter estándar, el test falla.

- [ ] **T8. Espera a la base de datos al arrancar.** RF-1, RF-3, RF-4
  - `apps/core/db_wait.py`, comando `wait_for_db` y `docker-entrypoint.sh` con `ENTRYPOINT` en el Dockerfile.
  - Commit: `feat(core): wait for the database on startup`
  - Hecho cuando: pasan los tests de espera con éxito tardío y de plazo vencido (con reloj falso) y el del comando con centinelas de host y usuario; `docker compose up -d` desde cero arranca la aplicación; con la BD parada el contenedor falla a los 60 s con el mensaje fijo.

- [ ] **T9. Plantilla y lector único del entorno.** RF-26, RF-27, RF-28
  - Tests de comparación con la plantilla montada en `/.env.example`, test AST y valores `insecure-`.
  - Commit: `test(config): check env template against variables read`
  - Hecho cuando: los tests pasan. Prueba de mecanismo: añadir una variable a `KNOWN_VARIABLES` sin ponerla en la plantilla hace fallar el test, y un `os.getenv` fuera de `env.py` hace fallar el AST; después se restaura.

- [ ] **T10. Ejecución de tests, lint y aislamiento de red.** RF-6, RF-33, RF-35, RNF aislamiento
  - Fixture autouse de red en `conftest.py`, test `geteuid`, y subprocesos de pytest y ruff.
  - Commit: `test: cover test runner, linter and network isolation`
  - Hecho cuando: el subproceso de pytest con un test que falla y sin `DJANGO_ENV` sale con código ≠0; ruff sale con ≠0 sobre un fichero con infracciones y con 0 sobre el backend; `create_connection` a `example.com` falla en un test; toda la suite y el lint están en verde.
