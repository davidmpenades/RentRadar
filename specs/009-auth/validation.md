# Validación — 009-auth
Rama: `feature/009-auth` · Entorno: Docker Compose, `postgis/postgis:18-3.6`, Django 5.2.18, DRF 3.18.3, drf-spectacular 0.30.0, Python 3.13.16

## Ajustes de autenticación y base de errores de la API (T1)
Fecha: 2026-11-04 · Ficheros: `backend/{config/settings/base.py, apps/core/api.py, apps/core/serializers.py, apps/assets/serializers.py, apps/assets/views.py, config/tests/test_auth_settings.py, config/tests/test_http_hardening.py, apps/core/tests/test_api.py, apps/assets/tests/test_public_list_session.py}`. `openapi.json` no cambia.

| Comprobación | Orden | Resultado |
|---|---|---|
| Tests nuevos antes del código | `docker compose exec backend pytest -q <ficheros de la tarea>` | 17 fallan: 3 de `test_auth_settings.py` (middleware ausente, validadores vacíos), los 3 de `test_cookie_policy_in_every_environment` (`SESSION_COOKIE_AGE` inexistente en el módulo), 10 de `test_api.py` (códigos y estados) y 1 de `test_public_list_session.py` (ver abajo) |
| Suite completa con la BD de test recreada | `docker compose exec backend pytest -q --create-db` | 1743 passed |
| Estilo y formato | `docker compose exec backend sh -c "ruff check . && ruff format --check ."` | Sin incidencias; 122 ficheros formateados |
| Modelos y migraciones cuadran | `docker compose exec backend python manage.py makemigrations --check --dry-run` | No changes detected |
| Contrato | `docker compose exec -u "$(id -u)" backend python manage.py spectacular --format openapi-json --file openapi.json --validate --fail-on-warn --lang en` y `git diff --stat backend/openapi.json` | Sin avisos; diff vacío |
| Tipos del cliente | `cd frontend && npm run api:check` | Sin cambios |

`migrate` no se ha ejecutado en la BD de desarrollo.

### Lo observado
| # | Comprobación | Observado |
|---|---|---|
| 1 | Lista pública con el middleware nuevo | Los tests de `test_public_list_session.py` pasan antes y después de añadir el middleware: la vista no declara autenticación, así que no hay nada que fallar hasta que se rompa. Su valor se demuestra con la mutación a. El único que falló antes del código fue la comprobación de la consulta de partida, por una zona mal elegida en el propio test (corregida) |
| 2 | Consultas de la lista | La lista une con `users_user` para filtrar al propietario activo, así que buscar esa tabla en el SQL no distingue una lectura de la sesión. El test exige una sola consulta, que toque `assets_asset`, y ninguna a `django_session` |
| 3 | Cookie `short` | Django la descarta por formato sin consultar la tabla de sesiones; por eso el test añade una de 40 caracteres inválidos y una de 32 con el formato correcto y sin fila |
| 4 | `SESSION_COOKIE_AGE` | El valor por defecto de Django ya son 14 días; el test lo fija igualmente para que un cambio futuro falle |
| 5 | Cabeceras de la lista | La respuesta se marca como sin cookies y borra `Set-Cookie` y `Vary: Cookie`: mirar solo cabeceras no detectaría una lectura de la sesión, por eso se cuentan las consultas |

### Pruebas de mecanismo
Mutaciones sobre una copia hecha junto al fichero (`<fichero>.orig`), restaurada con `cp` y borrada; sha256 idéntico antes y después en las cuatro y ninguna copia sin versionar. Ejecución sobre `config/tests`, `test_public_list_session.py`, `test_public_list_api.py` y `test_api.py`.

| # | Fichero | Mutación | Tests que fallan |
|---|---|---|---|
| a | `apps/assets/views.py` | `authentication_classes = [SessionAuthentication]` en `PublicAssetListView` | 7: en `test_public_list_session.py`, `test_a_valid_session_is_never_read_and_the_answer_is_the_same`, `test_an_expired_session_is_never_read_and_the_answer_is_the_same` y los dos de `test_a_malformed_or_unknown_cookie_changes_nothing` (cookie de 40 caracteres y de 32); en `test_public_list_api.py`, `test_a_logged_in_visitor_counts_like_an_anonymous_one`, `test_the_view_declares_its_own_authentication_permissions_and_methods` y `test_the_session_is_never_read_and_the_answer_is_the_same` |
| b | `config/settings/base.py` | `DEFAULT_AUTHENTICATION_CLASSES` con `SessionAuthentication` | 2: `test_api_settings.py::test_rest_framework_setting[DEFAULT_AUTHENTICATION_CLASSES-expected5]` y `test_tooling.py::test_ruff_accepts_the_backend_code` (este por la longitud de la línea mutada, no por el ajuste). La lista pública no falla: la vista declara `authentication_classes = []` y no usa el valor por defecto, equivalente |
| c | `config/settings/base.py` | Quitar `AuthenticationMiddleware` de `MIDDLEWARE` | 2: `test_auth_settings.py::test_authentication_middleware_comes_right_after_csrf` y `test_session_and_csrf_stay_before_authentication`. La lista pública no falla, como se esperaba: sin «quién soy» todavía no depende del middleware |
| d | `apps/core/api.py` | `csrf_failed` con estado 400 | 2: `test_api.py::test_each_code_has_its_status[csrf_failed-403]` y `test_csrf_failed_is_not_the_general_forbidden` |

sha256 antes y después:

| Fichero | sha256 |
|---|---|
| `apps/assets/views.py` | `1e64747d58f4977df739674a4daf043b935ce1301623bfcf49dbb3b4714a5388` |
| `config/settings/base.py` (mutaciones b y c) | `f6bcc6a1b307fc6d9af589e12b3552c1dca88e6150fd700d673fcdb2890f566f` |
| `apps/core/api.py` | `8102e9b6935556d36eea3a141eb8b5f4784fd624cab59858e9f268353403d594` |
