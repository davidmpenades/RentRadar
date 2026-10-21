# Tareas 004 — Usuarios y categorías
Requisitos previos:
- Rama `feature/004-users-and-categories` creada desde `dev`.
- Spec actualizada con D1, D2, D3 y RF-23 (`/sdd-change` del 2026-10-21).

Antes de cada tarea:
- Claude presenta Qué, Por qué, RF, Cómo se prueba y Qué te toca revisar.
- Todas tocan modelos, validaciones o reglas, salvo T9. Claude espera tu OK antes de empezar y explica línea a línea la lógica de dominio antes de que la aceptes.

Antes de cada commit:
- `docker compose exec backend pytest -q` y `docker compose exec backend sh -c "ruff check . && ruff format --check ."` en verde.
- Si cambian modelos, también `manage.py check` y `makemigrations --check --dry-run`.
- El test se escribe primero y debe fallar por la razón esperada.

Prohibido sin tu OK explícito en ese momento: `migrate` en la BD de desarrollo, órdenes de git que descarten cambios, push.

- [ ] **T1. Caracteres de control y error de dominio.** RF-4, RF-12, RF-16
  - Quién: Claude escribe `apps/core/text.py` y `apps/core/errors.py` (funciones puras) y sus tests en `apps/core/tests/`. La normalización del email no va aquí: vive en `UserManager`, que nace en T2.
  - Cómo se prueba:
    - Detección de Cc, incluidos `\x00` y tabulador interno.
    - El validador lanza `control_char` sin `params`.
    - `translate_validation_error` descarta `params` y envía lo no mapeado a `validation_failed`.
    - `DomainValidationError` solo contiene campos y códigos en `str()`, `repr()` y `message_dict`.
  - Qué toca revisar: que `DomainValidationError` no guarda nada más que códigos.
  - Commit: `feat(core): add control character rule and domain validation error`
  - Hecho cuando: los tests nuevos fallaron antes de existir las funciones y ahora pasan; `pytest -q` y ruff en verde.

- [ ] **T2. Modelo de usuario por email, normalización del email, instalación de auth y migración inicial.** RF-1, RF-2, RF-5, RF-7, RF-12
  - Quién:
    - Claude escribe primero `apps/users/tests/test_models.py` (estructura de RF-1, `__str__` sin email, `DataError` de RF-5 en BD, `IntegrityError` de RF-7 con el nombre de la restricción y fechas con zona horaria) y `apps/users/tests/test_emails.py` (normalización: recorte con `str.strip()` incluido NBSP, NFKC, minúsculas enteras y el orden de los tres pasos).
    - El usuario escribe `apps/users/models.py`: `User` y `UserManager`, con `normalize_email` (el código que hace pasar `test_emails.py`), `get_by_natural_key` normalizando y sin los métodos de creación todavía.
    - Claude escribe `apps.py`, añade a `base.py` contenttypes, auth, `apps.users` y `AUTH_USER_MODEL` en un único commit con la migración, y genera `0001_initial` con `makemigrations -u "$(id -u)"` + `ruff format`.
  - Cómo se prueba:
    - Tests en rojo antes del modelo (por app no instalada, no por otro motivo); `docker compose restart backend`.
    - `sqlmigrate users 0001` confirma `users_user_email_key` y `users_user_email_lower_unique`.
    - `test_entrypoints.py` (check en desarrollo) y `test_migrations.py` en verde.
    - Sin `migrate` en desarrollo.
  - Qué toca revisar: Claude revisa línea a línea tu modelo (sin `blank` en `email`, `unique=True`, `REQUIRED_FIELDS = []`, orden DJ012, y en `normalize_email` el orden recorte, NFKC y `lower()`). Tú revisas el SQL de la migración.
  - Commit: `feat(users): add email-based custom user model`
  - Hecho cuando: `pytest -q`, ruff, `manage.py check` y `makemigrations --check --dry-run` en verde; la migración solo crea `users_user` y sus tablas M2M.

- [ ] **T3. Servicio de alta de usuarios.** RF-1, RF-2, RF-3, RF-4, RF-5, RF-6, RF-7, RF-8, RF-9, RF-10
  - Quién:
    - Claude escribe primero `apps/users/tests/test_services.py` y después `apps/users/services.py` (`create_user`, mapa de códigos, guardado protegido) y `PASSWORD_HASHERS` en `settings/test.py` (D7).
    - El usuario añade a `UserManager.create_user` la delegación en el servicio, con un import diferido.
  - Cómo se prueba:
    - Los casos de la Estrategia de tests para RF-1 (`authenticate`) a RF-10.
    - Carrera simulada con `full_clean` anulado: da `email_taken` y la conexión sigue usable.
    - `make_password` no se llama ante ningún rechazo.
    - Prueba de mecanismo de la captura con un test temporal sin commitear.
  - Qué toca revisar: el orden "validar todo, después hashear"; que el `raise` está fuera del `except`; la firma solo con nombre (RF-10).
  - Commit: `feat(users): add user creation service`
  - Hecho cuando: los tests de RF-1 a RF-10 pasan; `pytest -q` y ruff en verde.

- [ ] **T4. Superusuario y cambio de email.** RF-2, RF-4, RF-6, RF-8, RF-11
  - Quién:
    - Claude escribe primero `apps/users/tests/test_superuser.py` y los casos de cambio de email, y después `create_superuser` y `change_user_email` en el servicio.
    - El usuario añade a `UserManager.create_superuser` la delegación en el servicio.
  - Cómo se prueba:
    - `create_superuser` concede los permisos de administración.
    - `createsuperuser --noinput` sin `DJANGO_SUPERUSER_PASSWORD` da `CommandError` y no crea nada; con la variable, crea un superusuario.
    - El cambio de email normaliza, rechaza duplicados y Cc, acepta el propio email con otras mayúsculas, y ante un rechazo deja la instancia y la BD como estaban.
  - Qué toca revisar: que el rechazo no modifica nada, ni la instancia ni la BD.
  - Commit: `feat(users): add superuser creation and email change`
  - Hecho cuando: los tests pasan; `pytest -q` y ruff en verde.

- [ ] **T5. Credenciales fuera de errores y logs.** RF-12
  - Quién:
    - Claude escribe `apps/users/tests/test_leaks.py` y `config/tests/test_logging.py`.
    - Claude añade `LOGGING` a `base.py` y `django.db.backends` a INFO a `build_production_logging` (D5).
  - Cómo se prueba:
    - `test_logging.py` falla antes del cambio y pasa después.
    - Para cada rechazo: el email recibido y normalizado y la contraseña no aparecen en `str()`, `repr()`, `format_exception()`, `message_dict` ni `caplog.text` (DEBUG), y `__context__` y `__cause__` son `None`.
    - Prueba de mecanismo con un test temporal sin commitear que parchea el servicio para encadenar el `IntegrityError`: el test de fugas falla.
    - `test_log_redaction.py` sigue en verde.
  - Qué toca revisar: la configuración de log en los tres entornos.
  - Commit: `feat(config): keep credentials out of errors and logs`
  - Hecho cuando: `pytest -q` y ruff en verde; la prueba de mecanismo queda descrita en el mensaje de la tarea y no en el repositorio.

- [ ] **T6. Modelo de categoría y migración inicial.** RF-13, RF-15, RF-17
  - Quién:
    - Claude escribe primero `apps/categories/tests/test_models.py`: slug único; `IntegrityError` por slug repetido y por nombre repetido con otras mayúsculas; `DataError` con slug de 51 y nombre de 61 (D1).
    - El usuario escribe `apps/categories/models.py`.
    - Claude escribe `apps.py`, añade `apps.categories` a `INSTALLED_APPS` y genera `0001_initial`.
  - Cómo se prueba: `restart` del backend; `sqlmigrate categories 0001` confirma los nombres de las restricciones; `test_migrations.py` en verde; sin `migrate` en desarrollo.
  - Qué toca revisar: Claude revisa línea a línea tu modelo (regex con `[0-9]` y `\Z`, `violation_error_code`, `__str__`).
  - Commit: `feat(categories): add category model`
  - Hecho cuando: `pytest -q`, ruff, `manage.py check` y `makemigrations --check --dry-run` en verde.

- [ ] **T7. Servicio de validación y guardado de categorías.** RF-13, RF-14, RF-15, RF-16, RF-17, RF-18, RF-23
  - Quién:
    - Claude escribe primero `apps/categories/tests/test_models.py` (casos nuevos de `Category.normalize_name`: recorte con `str.strip()`, NFC y que no cambia mayúsculas) y `apps/categories/tests/test_services.py`.
    - El usuario escribe `Category.normalize_name` en `apps/categories/models.py` (el código que hace pasar esos tests; no requiere migración).
    - Claude escribe `apps/categories/services.py` (`save_category`, mapa de códigos y el mismo guardado protegido).
  - Cómo se prueba:
    - Casos de RF-14 a RF-18 de la Estrategia de tests, incluidos `"  piscina  "` frente a `Piscina` y 60 caracteres con tildes en NFC y NFD.
    - El conjunto de códigos coincide con la tabla del plan.
    - `makemigrations --check --dry-run` confirma que `normalize_name` no genera migración.
  - Qué toca revisar: Claude revisa línea a línea tu `normalize_name`; tú, que la inmutabilidad compara con el valor guardado y que el slug no se recorta.
  - Commit: `feat(categories): add category validation service`
  - Hecho cuando: los tests pasan; `pytest -q` y ruff en verde.

- [ ] **T8. Semilla de las once categorías.** RF-19, RF-20, RF-21, RF-22
  - Quién: Claude escribe primero `apps/categories/tests/test_seed.py` y después `0002_seed_categories.py` (`makemigrations categories --empty --name seed_categories -u "$(id -u)"`, editada a mano).
  - Cómo se prueba:
    - RF-19: las once de la spec, escritas en el test, y cada entrada pasa `save_category`.
    - RF-20 y RF-21: `apply_seed` y `reverse_seed` con las apps históricas en un test `django_db` normal, sin `transaction=True`.
    - RF-22, parte estructural: `RunPython(apply_seed, reverse_seed)`, `atomic` y un único `delete()`.
  - Qué toca revisar: que la migración no importa el modelo actual, usa el alias de la conexión, no usa `noop` y que `SEED` coincide letra a letra con RF-19.
  - Commit: `feat(categories): seed the closed category list`
  - Hecho cuando: `pytest -q`, ruff y `makemigrations --check --dry-run` en verde; la BD de test, creada desde cero, contiene la semilla.

- [ ] **T9. Validación y BD de desarrollo.** Todos
  - Quién: Claude.
  - Cómo se prueba:
    1. Suite completa, ruff, `manage.py check` y `makemigrations --check --dry-run`.
    2. **Con tu OK en ese momento**, `migrate` en la BD de desarrollo (D8: incremental, salvo que elijas recrearla).
    3. `showmigrations` y un recuento de las once categorías en desarrollo.
    4. `validation.md` con fecha, orden y resultado RF por RF; `docs/architecture.md` con las apps nuevas y `core/text.py` y `core/errors.py`.
  - Qué toca revisar: el veredicto de `validation.md` y los riesgos aceptados que quedan anotados.
  - Commit: `docs(spec): record spec 004 validation`
  - Hecho cuando: cada RF de RF-1 a RF-23 tiene su test en verde (RF-22 en parte, como prevé la spec); la BD de desarrollo contiene las once categorías; `validation.md` termina con un veredicto.
