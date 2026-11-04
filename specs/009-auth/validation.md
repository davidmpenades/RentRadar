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

## Servicio de registro con las reglas de contraseña y el sustituto suelto en el email (T2)
Fecha: 2026-11-04 · Ficheros: `backend/{apps/core/text.py, apps/users/services.py, apps/core/tests/test_text.py, apps/users/tests/helpers.py, apps/users/tests/test_registration_service.py, apps/users/tests/test_services.py, apps/users/tests/test_leaks.py}`. Sin migraciones; `openapi.json` no cambia.

| Comprobación | Orden | Resultado |
|---|---|---|
| Tests nuevos antes del código | `docker compose exec backend pytest -q apps/users/tests apps/core/tests/test_text.py` | `test_text.py`, `test_registration_service.py` y `test_leaks.py` no se importan (`register_user` y `contains_lone_surrogate` no existen). `test_services.py`, ejecutado antes de importar `register_user` en él: 9 fallan (ver abajo) y 109 pasan |
| Tests del paquete tras el código | `docker compose exec backend pytest -q apps/users apps/core/tests/test_text.py` | 228 passed |
| Suite completa con la BD de test recreada | `docker compose exec backend pytest -q --create-db` | 1820 passed |
| Estilo y formato | `docker compose exec backend sh -c "ruff check . && ruff format --check ."` | Sin incidencias; 124 ficheros formateados |
| Modelos y migraciones cuadran | `docker compose exec backend python manage.py makemigrations --check --dry-run` | No changes detected |
| Contrato | `docker compose exec -u "$(id -u)" backend python manage.py spectacular --format openapi-json --file openapi.json --validate --fail-on-warn --lang en` y `git diff --stat backend/openapi.json` | Sin avisos; diff vacío |
| Tipos del cliente | `cd frontend && npm run api:check` | Sin cambios |
| Caracteres invisibles | Detección por categoría Unicode (Cc, Cf, Cs, Mn, Mc, Me, Zl, Zp y Zs salvo el espacio) sobre los siete ficheros tocados | 0 hallazgos; los sustitutos se construyen con `chr(0xD800)` y `chr(0xDFFF)` |

`migrate` no se ha ejecutado en la BD de desarrollo.

### Tests que fallaron primero
| Fichero | Fallo | Razón |
|---|---|---|
| `apps/core/tests/test_text.py` | `ImportError: cannot import name 'contains_lone_surrogate'` | La función no existe |
| `apps/users/tests/test_registration_service.py`, `test_leaks.py` | `ImportError: cannot import name 'register_user'` | El servicio no existe |
| `apps/users/tests/test_services.py` (9) | `test_creation_rejects_invalid_emails` y `test_email_with_a_lone_surrogate_runs_no_query_on_creation` (user y superuser) y `test_change_user_email_rejects_invalid_emails_without_changes` y `test_email_with_a_lone_surrogate_runs_no_query_on_change`: `UnicodeEncodeError: 'utf-8' codec can't encode character '\ud800'` (6 en total: el error del servidor al consultar la unicidad con el email) | El sustituto suelto en el email no se rechaza antes de `full_clean` |
| ídem | `test_password_with_a_lone_surrogate_is_invalid_without_hashing` (user y superuser): `AssertionError: make_password no debe llamarse ante un rechazo` | Se calculaba el hash con un sustituto suelto |
| ídem | `test_error_codes_match_the_plan_table`: faltan en `ERROR_CODES` los cuatro códigos nuevos | Constantes sin añadir |

### Lo observado
| # | Comprobación | Observado |
|---|---|---|
| 1 | Validadores y hash ante NUL y sustitutos | Los cuatro validadores de Django devuelven vacío con una contraseña con `\x00` y con un sustituto suelto (con usuario): no los frenan. `make_password` lanza `UnicodeEncodeError` con un sustituto suelto (con el hasher de test y con PBKDF2) y hashea un NUL sin problema. Por eso el registro los comprueba antes de los validadores y antes del hash |
| 2 | `create_user` y `create_superuser` con un sustituto suelto en la contraseña | Daban un error del servidor (`UnicodeEncodeError` al calcular el hash). Ahora dan `password_invalid` sin calcularlo. Es la corrección de un 500 y no cambia la 004 (no hubo `/sdd-change`). El NUL de esa vía no se toca: un test fija que se sigue aceptando y hasheando |
| 3 | Validadores con más de 128 caracteres | Corren igualmente: 129 dígitos dan `password_too_long` y `password_entirely_numeric`, así que el cliente recibe todos los códigos. Ninguna ruta calcula el hash |
| 4 | `skip_validation` | Extraída a `apps/users/tests/helpers.py` por ser la tercera copia (`test_services.py`, `test_leaks.py` y el registro). `trap_make_password` y `codes_of` son la segunda copia y quedan en cada fichero |
| 5 | NUL en el email | Sin ninguna consulta SQL: el campo con errores queda fuera de la comprobación de unicidad, y el rechazo da `email_invalid` y `email_control_char`. El test lo fija con «ninguna consulta sobre `users_user`» |
| 6 | Rechazo de contraseña con el email válido | No se puede evitar toda consulta sobre `users_user`: se hacen las dos comprobaciones de unicidad (exacta y con `LOWER`), porque `email_taken` se informa junto con los errores de contraseña. El test comprueba que no hay ninguna escritura y que el rechazo es solo `password_invalid` |
| 7 | Email con sustituto suelto | `email_invalid` con cero consultas en `create_user`, `create_superuser`, `register_user` y `change_user_email`; en el cambio, el email del usuario queda como estaba. La similitud de la contraseña se ejecuta sin usuario en ese caso y cuando el email no es texto |

### Pruebas de mecanismo
Mutaciones sobre una copia hecha junto al fichero (`<fichero>.orig`), restaurada con `cp` y borrada; sha256 idéntico antes y después en las diez y ninguna copia sin versionar. Ejecución sobre `apps/users/tests` y `apps/core/tests/test_text.py` (y, en la 3a, también `config/tests/test_auth_settings.py`).

| # | Fichero | Mutación | Tests que fallan |
|---|---|---|---|
| 1 | `apps/users/services.py` | `set_password` antes de comprobar `errors` | 16: los 6 de `test_nul_or_surrogate_in_the_password_is_invalid_and_alone`, `test_password_of_129_characters_is_rejected_without_hashing`, `test_registration_only_rejections_do_not_leak[surrogate_in_the_password]`, 6 de `test_rejections_never_compute_the_hash` (email inválido, 129 caracteres y email repetido, en user y superuser) y `test_password_with_a_lone_surrogate_is_invalid_without_hashing` (2) |
| 2a | `apps/users/services.py` | Quitar la comprobación del sustituto del email en `_create_account` | 9: `test_creation_rejects_invalid_emails` (user y superuser), `test_email_with_a_lone_surrogate_runs_no_query_on_creation` (user, superuser y register), `test_surrogate_in_the_email_is_invalid_with_no_query[domain]` y `[needs-normalizing]`, `test_surrogate_email_and_weak_password_are_reported_together` y `test_registration_only_rejections_do_not_leak[surrogate_in_the_email]` |
| 2b | `apps/users/services.py` | Quitar la comprobación del sustituto de la contraseña en `_registration_password_errors` | 4: `test_nul_or_surrogate_in_the_password_is_invalid_and_alone` con `surrogate`, `low-surrogate`, `in-the-middle` y `too-long`. `nul` y `only-nul` siguen en verde: el NUL tiene su propia comprobación |
| 2c | `apps/users/services.py` | Quitar la comprobación del sustituto del email en `change_user_email` | 2: `test_change_user_email_rejects_invalid_emails_without_changes[...ud800...]` y `test_email_with_a_lone_surrogate_runs_no_query_on_change` |
| 2d | `apps/users/services.py` | Quitar la comprobación del sustituto de la contraseña en `_basic_password_errors` | 2: `test_password_with_a_lone_surrogate_is_invalid_without_hashing` (user y superuser) |
| 2e | `apps/users/services.py` | Quitar la comprobación del NUL de la contraseña en `_registration_password_errors` | 2: `test_nul_or_surrogate_in_the_password_is_invalid_and_alone` con `nul` y `only-nul`. Los casos con sustituto siguen en verde: tienen su propia comprobación |
| 3a | `config/settings/base.py` | Intercambiar `CommonPasswordValidator` y `NumericPasswordValidator` | 3: `test_every_password_rule_reports_in_the_documented_order`, `test_all_digit_common_password_gets_both_codes` y `config/tests/test_auth_settings.py::test_password_validators_and_their_order` |
| 3b | `apps/users/services.py` | Ordenar alfabéticamente los códigos de contraseña | 3: `test_password_of_129_characters_is_too_long_and_still_validated`, `test_every_password_rule_reports_in_the_documented_order` y `test_all_digit_common_password_gets_both_codes` |
| 4 | `apps/users/services.py` | `password_invalid` junto a los códigos de los validadores | 2: `test_nul_or_surrogate_in_the_password_is_invalid_and_alone[only-nul]` y `[low-surrogate]`, los dos casos que además serían demasiado cortos. Los demás valores hostiles pasan los validadores sin código, así que la mutación no les cambia el resultado |
| 5 | `apps/users/services.py` | Contraseña comprobada con `user=None` en el registro | 5: `test_every_password_rule_reports_in_the_documented_order`, `test_password_equal_to_the_email_is_too_similar`, `test_password_similar_to_the_normalized_email_is_too_similar` y `test_registration_only_rejections_do_not_leak` con `password_equal_to_the_email` y `password_close_to_another_email` |

sha256 antes y después:

| Fichero | sha256 |
|---|---|
| `apps/users/services.py` (mutaciones 1, 2a, 2b, 2c, 2d, 2e, 3b, 4 y 5) | `304f7a6b6115464971561a3dc5dba226ff2ce7a71685ff38eede3cbc5bae7569` |
| `config/settings/base.py` (mutación 3a) | `f6bcc6a1b307fc6d9af589e12b3552c1dca88e6150fd700d673fcdb2890f566f` |
