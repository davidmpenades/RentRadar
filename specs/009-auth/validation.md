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

## CSRF explícito y lectura acotada del cuerpo (T3)
Fecha: 2026-11-04 · Ficheros: `backend/{conftest.py, apps/core/csrf.py, apps/core/request_body.py, apps/core/tests/{csrf_views.py, csrf_urls.py, test_csrf.py, test_request_body.py, test_api_import.py}}`. Sin migraciones; `openapi.json` no cambia.

| Comprobación | Orden | Resultado |
|---|---|---|
| Tests nuevos antes del código | `docker compose exec backend pytest -q apps/core/tests/test_csrf.py apps/core/tests/test_request_body.py apps/core/tests/test_api_import.py` | 2 errores de recolección y ejecución interrumpida (ver abajo) |
| Tests de la tarea tras el código | la misma orden | 101 passed |
| Suite completa con la BD de test recreada | `docker compose exec backend pytest -q --create-db` | 1918 passed |
| Estilo y formato | `docker compose exec backend sh -c "ruff check . && ruff format --check ."` | Sin incidencias; 130 ficheros formateados |
| Modelos y migraciones cuadran | `docker compose exec backend python manage.py makemigrations --check --dry-run` | No changes detected |
| Contrato | `docker compose exec -u "$(id -u)" backend python manage.py spectacular --format openapi-json --file openapi.json --validate --fail-on-warn --lang en` y `git diff --stat backend/openapi.json` | Sin avisos; diff vacío |
| Tipos del cliente | `cd frontend && npm run api:check` | Sin cambios |
| Caracteres invisibles | Detección por categoría Unicode (Cc, Cf, Cs, Mn, Mc, Me, Zl, Zp y Zs salvo el espacio) sobre los ocho ficheros de código y tests tocados | 0 hallazgos |

`migrate` no se ha ejecutado en la BD de desarrollo.

### Tests que fallaron primero
| Fichero | Fallo | Razón |
|---|---|---|
| `apps/core/tests/test_csrf.py` | `ModuleNotFoundError: No module named 'apps.core.csrf'` | El módulo no existe |
| `apps/core/tests/test_request_body.py` | `ModuleNotFoundError: No module named 'apps.core.request_body'` | El módulo no existe |
| `apps/core/tests/test_api_import.py` | No se ejecutó por separado antes del código: los dos errores de recolección anteriores interrumpieron la sesión. Con `MODULES` ampliado y los módulos creados pasa (5 casos) | Mismo motivo; su valor lo da la importación en un proceso nuevo |

Tras crear los módulos, 3 tests fallaron por defectos de los propios tests (no del código) y se corrigieron: `GET` y `HEAD` enviaban el cuerpo como cadena de consulta (`ValueError` en `urlencode`) y el cuerpo vacío con tipo JSON no llevaba `CONTENT_TYPE`, porque `RequestFactory` solo lo pone si hay cuerpo.

### Lo observado
| # | Comprobación | Observado |
|---|---|---|
| 1 | Orden de DRF | `APIView.dispatch` ejecuta `initial()` (negociación, autenticación, permisos, límites) y después busca el manejador; si el método no está en `http_method_names` o no existe, responde 405. Por eso el mixin comprueba CSRF tras `super().initial()` y solo si el manejador existe. Los tests lo fijan: un PUT sin token da 405 con y sin manejador de otro método, y con el límite superado un POST y un PUT sin token dan 429, no 403 |
| 2 | Clientes de prueba | El `Client` de Django y `APIRequestFactory` marcan la petición con `_dont_enforce_csrf_checks = True` y `CSRFCheck` lo respeta: con ellos nunca se vería un 403. De ahí la fixture `csrf_client` (`Client(enforce_csrf_checks=True)`) y, en el test unitario, `_dont_enforce_csrf_checks = False` a mano |
| 3 | Cuerpo no leído | Con `LimitedStream.read` parcheado para lanzar, la petición sin token da 403 limpio, también con un cuerpo de formulario: `POST = QueryDict()` evita que `CSRFCheck` lo analice. Sin esa línea, un token solo en `csrfmiddlewaretoken` se aceptaba (mutación 6) |
| 4 | Otras vistas | Un POST a la lista pública con `csrf_client` da 405 `method_not_allowed`, no 403: las vistas DRF son `csrf_exempt` y la lista no usa el mixin |
| 5 | Motivo del rechazo | `CSRFCheck._reject` devuelve el motivo en vez de registrarlo; `enforce_csrf` lanza `ApiError("csrf_failed")` sin él y sin `__context__`. Ni el cuerpo ni el log (DEBUG) lo contienen ni llevan los valores recibidos |
| 6 | Límite de lectura | `LimitedStream` de Django corta la lectura en el `Content-Length` declarado: bajo WSGI nunca se leen más bytes de los declarados. La rama «se leen más de 4096 bytes» solo se alcanza con un flujo inyectado (`request._stream = BytesIO(...)` con un `CONTENT_LENGTH` pequeño; `read(4097)` devuelve 4097 bytes), que es lo que usan sus tests |
| 7 | `Content-Length` | No numérico, vacío o ausente cuenta como 0; uno negativo (`-5`) hace que `read` devuelva `b""` sin error. Todos dan un cuerpo vacío, es decir `{}` con tipo JSON |
| 8 | `Content-Type` | Sin cabecera, Django da `application/octet-stream`. `Application/JSON; charset=latin-1` da `content_type == "application/json"`: el charset se ignora y se lee siempre como UTF-8 |
| 9 | Analizador | Con `JSONParser().parse(BytesIO(raw), "application/json", {})`: BOM, `NaN`, UTF-8 inválido y un cuerpo de solo espacios dan `ParseError` (400; el caso de solo espacios queda documentado por un test); `"[" * 2048 + "]" * 2048` se analiza sin `RecursionError` y da una lista (400 por la raíz); con claves duplicadas gana la última; un objeto anidado unos 600 niveles en una clave desconocida (3602 bytes) se analiza y es un `dict` |
| 10 | `RecursionError` | Con datos reales no se produce en este Python: la captura es defensiva y su test la simula parcheando `JSONParser` donde se usa (`apps.core.request_body`) |
| 11 | Objeto anidado | Un objeto válido anidado en una clave desconocida se acepta por definición de la spec («Demasiado anidado»): no hay límite de profundidad propio y esa clave se ignora como cualquier campo desconocido |
| 12 | Guarda del URLconf | Queda para la T5: aquí el mixin solo se aplica a las vistas de prueba |

### Pruebas de mecanismo
Mutaciones sobre una copia hecha junto al fichero (`<fichero>.orig`), restaurada con `cp` y borrada; sha256 idéntico antes y después en las once y ninguna copia sin versionar. Ejecución sobre `test_csrf.py` y `test_request_body.py`. Los tokens de `test_csrf.py` salen de `get_token()` (API pública: token enmascarado y secreto en `META["CSRF_COOKIE"]`); las seis mutaciones de `csrf.py` se repitieron con ese origen y los recuentos son los de la tabla.

| # | Fichero | Mutación | Tests que fallan |
|---|---|---|---|
| 1 | `apps/core/csrf.py` | Comprobar CSRF solo si `request.user.is_authenticated` | 25: `test_a_request_without_a_valid_token_gets_csrf_failed` (9), `test_the_rejection_never_shows_the_reason_nor_the_values` (9), `test_a_foreign_origin_with_a_valid_token_is_rejected`, `test_the_body_is_never_read_to_decide`, `test_a_form_body_is_never_parsed_to_decide`, `test_the_token_in_a_form_field_does_not_count`, `test_the_handler_of_a_listed_method_is_still_protected`, `test_the_post_of_the_same_view_does_need_it` y `test_the_csrf_check_comes_before_the_body_is_read` |
| 2 | `apps/core/csrf.py` | `PermissionDenied` en vez de `ApiError("csrf_failed")` | 17: los mismos que la 1, salvo los 9 de `test_the_rejection_never_shows_the_reason_nor_the_values` (el 403 genérico tampoco filtra el motivo), y más `test_enforce_csrf_raises_without_context_or_reason` |
| 3 | `apps/core/csrf.py` | Ignorar el motivo del `CSRFCheck` (`if reason and False`) | 26: los de la 1 y `test_enforce_csrf_raises_without_context_or_reason` |
| 4 | `apps/core/csrf.py` | Leer el cuerpo (`http_request.body`) antes de comprobar CSRF | 3: `test_the_body_is_never_read_to_decide`, `test_a_form_body_is_never_parsed_to_decide` y `test_the_csrf_check_comes_before_the_body_is_read` |
| 5 | `apps/core/csrf.py` | CSRF antes de `super().initial()` | 1: `test_the_throttle_answers_before_csrf[post]`. El PUT sigue en verde porque no tiene manejador y no se comprueba CSRF; es lo esperado |
| 6 | `apps/core/csrf.py` | Quitar `http_request.POST = QueryDict()` | 2: `test_a_form_body_is_never_parsed_to_decide` y `test_the_token_in_a_form_field_does_not_count` |
| 7 | `apps/core/request_body.py` | Quitar la comprobación de `Transfer-Encoding` | 9: `test_a_transfer_encoding_header_is_too_large_whatever_it_says` (4), `test_a_transfer_encoding_header_wins_over_a_wrong_content_type` (2), `test_a_transfer_encoding_header_is_rejected_without_reading`, `test_no_rejection_carries_a_context_nor_the_received_text[chunked]` y `test_the_whole_path_over_a_view` |
| 8 | `apps/core/request_body.py` | Quitar la comprobación de la longitud declarada | 4: `test_a_declared_length_over_the_limit_is_rejected_without_reading`, `test_a_huge_declared_length_wins_over_a_wrong_content_type` (2) y `test_no_rejection_carries_a_context_nor_the_received_text[too-large-declared]` |
| 9 | `apps/core/request_body.py` | `read(max_bytes + 1)` pasa a `read(max_bytes)` | 2: `test_more_bytes_than_the_limit_are_rejected_even_if_fewer_were_declared` y `test_exactly_one_byte_over_the_limit_is_read_as_too_large` |
| 10 | `apps/core/request_body.py` | Quitar `RecursionError` de la captura | 2: `test_a_parser_that_runs_out_of_recursion_is_an_invalid_request` y `test_the_recursion_rejection_carries_no_context` |
| 11 | `apps/core/request_body.py` | `read_text_fields` acepta también `int` y `float` como texto | 5: `test_text_fields_of_another_type_are_an_invalid_request` (int, float, true, false) y `test_the_whole_path_over_a_view` |

sha256 antes y después:

| Fichero | sha256 |
|---|---|
| `apps/core/csrf.py` (mutaciones 1 a 6) | `c101904bf51fc56767f140b96ff4e903e6b3b74195e2569fb3f90f12c5942f92` |
| `apps/core/request_body.py` (mutaciones 7 a 11) | `ef62c3c6bf4c4358ecaa9968423e88cb85c1e9770c024f070cc0cc0b2243b20b` |

## Límite de registro por IP con IPv6 por /64 (T4)
Fecha: 2026-11-04 · Ficheros: `backend/apps/users/{throttling.py, tests/test_throttling.py, tests/throttle_views.py, tests/throttle_urls.py}`. Sin migraciones; `openapi.json` no cambia.

| Comprobación | Orden | Resultado |
|---|---|---|
| Tests nuevos antes del código | `docker compose exec backend pytest -q apps/users/tests/test_throttling.py` | Sin `throttling.py`: `ModuleNotFoundError: No module named 'apps.users.throttling'`. Con un esbozo que usaba la IP recibida como clave, sin agrupar: 44 fallan (agrupación por /64, IPv4 mapeada, zona, cubo fijo, clave de caché y cupos compartidos) y 29 pasan (los que el propio `SimpleRateThrottle` ya cumple) |
| Tests de la tarea tras el código | la misma orden | 77 passed |
| Suite completa con la BD de test recreada | `docker compose exec backend pytest -q --create-db` | 1995 passed |
| Estilo y formato | `docker compose exec backend sh -c "ruff check . && ruff format --check ."` | Sin incidencias; 134 ficheros formateados |
| Modelos y migraciones cuadran | `docker compose exec backend python manage.py makemigrations --check --dry-run` | No changes detected |
| Contrato | `docker compose exec -u "$(id -u)" backend python manage.py spectacular --format openapi-json --file openapi.json --validate --fail-on-warn --lang en` y `git diff --stat backend/openapi.json` | Sin avisos; diff vacío |
| Tipos del cliente | `cd frontend && npm run api:check` | Sin cambios (código de salida 0) |
| Caracteres invisibles | Detección por categoría Unicode (Cc, Cf, Cs, Mn, Mc, Me, Zl, Zp y Zs salvo el espacio) sobre los cuatro ficheros | 0 hallazgos; las cifras no ASCII del test van como escapes |

`migrate` no se ha ejecutado en la BD de desarrollo.

### Lo observado
| # | Comprobación | Observado |
|---|---|---|
| 1 | Origen de la IP | Con `NUM_PROXIES = 0`, `get_ident` de DRF devuelve `REMOTE_ADDR` y no lee `X-Forwarded-For`. El valor por defecto de DRF es `None`, que sí se fiaría de la cabecera |
| 2 | Orden | `check_throttles()` corre en `APIView.initial()`, antes de elegir el manejador (405) y antes de la comprobación CSRF del mixin, que va tras `super().initial()`. La anotación se hace al pasar el límite, antes de leer el cuerpo: cuentan las 405 (PUT, HEAD, OPTIONS, GET), las 403 de CSRF, las 413 (declarada y `Transfer-Encoding`) y las 400 de `invalid_request`. Las 400 de `invalid_fields` se prueban en la T5, con la vista real |
| 3 | Las 429 no cuentan | `throttle_failure` no anota: seguir llamando tras el 429 no alarga la espera |
| 4 | Ventana | Deslizante: 5 + 5 peticiones separadas media hora agotan el cupo, y al pasar otra media hora se liberan solo las 5 primeras |
| 5 | Zona IPv6 | `ip_network((dirección, 64), strict=False)` solo crea una dirección nueva, sin zona, cuando hay bits de host. Con la parte de host a cero conserva la dirección original: `fe80::%eth0` daba `fe80::%eth0/64` y `fe80::%eth1` daba `fe80::%eth1/64`, de modo que cada zona tenía su propio cupo y la zona entraba en la clave. Es un fallo de corrección, no explotable con `NUM_PROXIES = 0`: `REMOTE_ADDR` lo rellena el servidor a partir de la conexión y la zona solo aparece en direcciones de la red local, así que un cliente de internet no puede elegirla. Por eso la dirección se reconstruye desde su entero, sin zona, antes de truncar; una zona de cualquier longitud se acepta y se descarta. Comprobado en el contenedor con los ajustes de test, sin conexión a la BD |
| 6 | Valores que no son una dirección | `ip_address(5)` se acepta como `0.0.0.5`, por eso se exige texto antes de analizar. Lo vacío, lo no válido y lo que no es texto van al cubo `unknown`; el texto recibido nunca entra en la clave |
| 7 | Usuario con sesión | La vista de registro no autentica (`authentication_classes = []`), así que ahí el usuario es siempre anónimo. Para que el test distinga un límite que eximiera a los autenticados, usa una vista de prueba con `SessionAuthentication` (mutación m11) |
| 8 | Reloj | `SimpleRateThrottle.timer` es un atributo de clase; el test lo sustituye con `staticmethod`, porque una función normal recibiría la instancia como primer argumento. La caducidad interna de la caché sigue en tiempo real, pero la ventana la decide la lista de marcas con el reloj inyectado |
| 9 | Aislamiento | El fixture `clear_default_cache` de `backend/conftest.py`, ya existente y de uso automático, vacía la caché antes de cada test; el cliente de pruebas siempre sale de `127.0.0.1` |

### Pruebas de mecanismo
Mutaciones sobre una copia hecha junto al fichero (`throttling.py.orig`), escritas sobre el mismo inode, restauradas desde la copia y con la copia borrada; sha256 idéntico antes y después y ninguna copia sin versionar. Ejecución sobre `apps/users/tests/test_throttling.py`, todas sobre la versión final del fichero.

| # | Mutación | Tests que fallan |
|---|---|---|
| m1 | Agrupar IPv6 en /48 | 14: `test_ip_bucket_groups_ipv6_by_64_and_keeps_ipv4` (los 10 casos IPv6), `test_an_address_of_another_64_has_another_bucket`, `test_a_very_long_zone_is_dropped_too`, `test_the_cache_key_of_a_valid_address_uses_its_bucket` y `test_an_address_of_another_64_has_its_own_quota` |
| m2 | Agrupar IPv6 en /128 | 16: `test_ip_bucket_groups_ipv6_by_64_and_keeps_ipv4` (los 10 casos IPv6), `test_two_addresses_of_the_same_64_share_a_bucket`, `test_a_zone_is_dropped_and_the_address_groups_like_any_other`, `test_a_very_long_zone_is_dropped_too`, `test_the_received_text_never_becomes_part_of_the_bucket`, `test_the_cache_key_of_a_valid_address_uses_its_bucket`, `test_two_addresses_of_the_same_64_share_the_limit` y `test_an_address_of_another_64_has_its_own_quota` |
| m3 | Tomar `X-Forwarded-For` antes que `get_ident` | 1: `test_x_forwarded_for_is_ignored` |
| m4 | Heredar de `AnonRateThrottle` sin clave propia | 7: `test_a_logged_in_visitor_is_limited_too`, los dos de la clave de caché, los cupos por mismo y otro /64, el de la IPv4 mapeada y el del cubo fijo |
| m5 | Anotar también las rechazadas por el límite | 4: `test_ten_requests_pass_and_the_eleventh_is_throttled`, `test_the_wait_shrinks_as_the_clock_advances`, `test_throttled_requests_do_not_count_and_do_not_extend_the_wait` y `test_the_window_slides_instead_of_resetting` |
| m6 | No desenvolver la IPv4 mapeada | 6: los 4 casos de `test_a_mapped_ipv4_has_the_bucket_of_the_direct_ipv4`, `test_a_mapped_ipv4_is_not_grouped_by_its_64` y `test_a_mapped_ipv4_shares_the_quota_of_the_direct_ipv4` |
| m7 | El texto recibido como cubo si no es una dirección | 20: los 17 casos de texto de `test_anything_that_is_not_an_address_goes_to_the_fixed_bucket`, `test_the_received_text_never_becomes_part_of_the_bucket`, `test_the_cache_key_carries_the_scope_and_the_bucket_only` y `test_unusable_addresses_share_the_fixed_bucket_without_failing` |
| m8 | No exigir texto antes de analizar | 2: `test_anything_that_is_not_an_address_goes_to_the_fixed_bucket` con `5` y `0` |
| m9 | Conservar la zona (truncar la dirección analizada, sin reconstruirla desde su entero) | 5: `test_ip_bucket_groups_ipv6_by_64_and_keeps_ipv4` con `fe80::%eth0`, `fe80::%eth1` y `2001:db8:0:1::%x`, `test_a_zone_is_dropped_and_the_address_groups_like_any_other` y `test_the_received_text_never_becomes_part_of_the_bucket`. Los casos con bits de host (`fe80::1%eth0`) no la detectan: ahí `strict=False` ya crea una dirección sin zona |
| m10 | Tasa `11/hour` | 26: los 25 tests sobre las vistas de prueba (los 11 casos de `test_every_kind_of_request_counts_whatever_the_answer` incluidos) y `test_the_limit_is_declared_on_the_class_and_not_read_from_settings` |
| m11 | Eximir a los autenticados (`return None` si `request.user.is_authenticated`) | 1: `test_a_logged_in_visitor_is_limited_too` |

sha256 antes y después:

| Fichero | sha256 |
|---|---|
| `apps/users/throttling.py` (m1 a m11) | `0389bea04c600d585b0a44bc759781f29521e09dc65fee560f3759234ea482a5` |

## Vista de registro, URL, guarda del URLconf y contrato (T5a)
Fecha: 2026-11-04 · Ficheros: `backend/{apps/users/serializers.py, apps/users/views.py, apps/users/urls.py, config/urls.py, apps/users/tests/test_register_api.py, apps/users/tests/test_auth_contract.py, apps/core/tests/test_csrf_guard.py, openapi.json}` y `frontend/src/api/schema.gen.ts`. Sin migraciones.

| Comprobación | Orden | Resultado |
|---|---|---|
| Tests nuevos antes del código | `docker compose exec backend pytest -q apps/users/tests/test_register_api.py apps/users/tests/test_auth_contract.py apps/core/tests/test_csrf_guard.py` | Sin `views.py` ni `serializers.py`, los tres ficheros no se importan (`No module named 'apps.users.views'`). Con un esbozo sin ruta: 97 fallan (404 y serializers sin campos). Con la ruta y una vista sin el mixin que responde 501: la guarda falla (`assert [RegisterView] == []`), fallan 76 casos del registro y pasan 10 (los 405 que DRF ya da por `http_method_names` y `public_field_errors`) |
| Tests de la tarea tras el código | la misma orden | 105 passed: 86 en `test_register_api.py`, 11 en `test_auth_contract.py` y 8 en `test_csrf_guard.py` (recuento con `--collect-only`) |
| Suite completa con la BD de test recreada | `docker compose exec backend pytest -q --create-db` | 2100 passed (1995 tras la T4 más los 105 nuevos) |
| Estilo y formato | `docker compose exec backend sh -c "ruff check . && ruff format --check ."` | Sin incidencias; 140 ficheros formateados |
| Modelos y migraciones cuadran | `docker compose exec backend pytest -q config/tests/test_migrations.py` | 1 passed (en la BD de test) |
| Contrato | `docker compose exec -u "$(id -u)" backend python manage.py spectacular --format openapi-json --file openapi.json --validate --fail-on-warn --lang en` | Sin avisos; regenerarlo de nuevo no cambia el fichero (sha256 igual). Con `DB_HOST` apuntando a un host inexistente genera el mismo fichero: no usa la BD |
| Tipos del cliente | `cd frontend && npm run api:gen`, `npm run api:check`, `npm run build` y `npx eslint src/api/schema.gen.ts` | `api:gen`, `api:check` y `build` en verde (código de salida 0). `eslint` también sale con 0, pero solo avisa de que la configuración ignora `schema.gen.ts`: no lo analiza |
| Caracteres invisibles | Detección por categoría Unicode sobre los nueve ficheros | 0 hallazgos |

`migrate` no se ha ejecutado en la BD de desarrollo.

`makemigrations --check --dry-run` lanzado con `manage.py` consulta `django_migrations` en la BD configurada (`check_consistent_history`), que es la de desarrollo: las filas «Modelos y migraciones cuadran» de T1 a T4 la leyeron. Desde la T5a esa comprobación se hace solo con `config/tests/test_migrations.py`, que ejecuta la misma orden dentro de pytest, sobre la BD de test.

### Contrato
`/api/v1/auth/register/`, solo `post`, `operationId` `registerAccount` y tag `auth`; cabecera `X-CSRFToken` obligatoria; cuerpo `RegistrationRequest`; 201 `Session` con la cabecera `Set-Cookie` documentada, 400 `RegistrationError` y 403, 405, 413 y 429 `ApiError`. Componentes nuevos: `Session` (`user` anulable), `SessionUser`, `RegistrationRequest` y `RegistrationError` (`params` opcional, listas de códigos). En el cliente, `user` es `SessionUser | null` y `params`, `{[key: string]: string[]}`.

### Lo observado
| # | Comprobación | Observado |
|---|---|---|
| 1 | Nombre del componente de la petición | Con `COMPONENT_SPLIT_REQUEST`, drf-spectacular añade «Request» al nombre: el serializer lleva `component_name="Registration"` para que el componente sea `RegistrationRequest` |
| 2 | Afirmaciones del plan | Verificadas: `Set-Cookie` como cabecera de respuesta de 201 pasa `--fail-on-warn`; `DictField(ListField)` sin `read_only` queda opcional (`required: ["code"]`); `login()` tras `flush()` crea la fila de sesión dentro del `atomic`, junto con la cuenta y `last_login` |
| 3 | Cuenta huérfana | El usuario de la sesión lo escribe `SessionMiddleware` al responder, fuera de la transacción: es el riesgo aceptado en la spec. Si falla la creación de la fila de sesión dentro del `atomic`, no queda cuenta (`test_a_failure_opening_the_session_leaves_no_account`) |
| 4 | Sesión de la misma cuenta | Un registro no puede crear una cuenta que ya tenga sesión: el test usa una sesión de esa cuenta y `register_user` parcheado en `apps.users.views`. Ahí solo `flush()` cambia la clave; `login()` la conservaría |
| 5 | Email de 4 KB | Da `email_invalid` y `email_too_long`: el validador de email de Django rechaza más de 320 caracteres |
| 6 | Guarda del URLconf | Recorre el URLconf real y exige el mixin a toda vista con un método no seguro listado y con manejador, también a las vistas de Django; respeta `as_view(http_method_names=...)` y marca como no protegida una vista función, cuyos métodos no se pueden inspeccionar. Una ViewSet de DRF tampoco expone `view_class` (DRF la marca con `cls` y `actions`): la guarda también la marca, aunque herede el mixin, y un test lo fija. Si se monta el admin o se añade una ViewSet, fallará y habrá que decidir |
| 7 | `public_field_errors` | Solo publica `email`, `password` y `__all__` (como `non_field`); el traductor de errores manda a `__all__` todo lo no mapeado |
| 8 | `Vary: Cookie` en el 201 | Lo pone `SessionMiddleware`, no la vista |
| 9 | Logs | El test comprueba antes que `django.db.backends` está en INFO o más y que `force_debug_cursor` está apagado, sube el registro a DEBUG, exige que `django.request` haya registrado algo y busca la marca en logs, respuestas y claves del contador |

### Pruebas de mecanismo
Mutaciones sobre una copia hecha junto al fichero (`<fichero>.orig`), escritas sobre el mismo inode, restauradas desde la copia y con la copia borrada; sha256 idéntico antes y después y ninguna copia sin versionar. Ejecución sobre `test_register_api.py`, `test_auth_contract.py` y `test_csrf_guard.py`.

| # | Fichero | Mutación | Tests que fallan |
|---|---|---|---|
| m1 | `apps/users/views.py` | Quitar `flush()` del registro | 2: `test_an_anonymous_session_with_data_is_discarded` y `test_a_session_of_the_same_account_is_discarded_too` |
| m2 | `apps/users/views.py` | `flush()` al principio de `post`, antes de leer y validar | 3: `test_a_rejected_registration_leaves_the_session_untouched` (sin sesión, anónima y con cuenta) |
| m3 | `apps/users/serializers.py` | `SessionUserSerializer` como `ModelSerializer` con `fields = "__all__"` | 6: `test_a_valid_registration_answers_201_with_only_the_normalized_email`, `test_privileged_fields_ids_and_unknown_fields_are_ignored`, `test_credentials_at_the_root_next_to_a_nested_unknown_key_are_registered`, `test_the_success_carries_only_the_new_email_even_after_a_staff_session`, `test_the_session_component_has_a_nullable_user_with_only_the_email` y `test_serializers_are_explicit_white_lists[SessionUserSerializer-fields0]` |
| m4 | `apps/users/views.py` | Quitar `no-store` del éxito | 2: `test_a_valid_registration_answers_201_with_only_the_normalized_email` y `test_no_answer_can_be_stored_by_a_cache[201]` |
| m5 | `apps/users/views.py` | Dar `is_staff` a la cuenta si la petición lo trae | 1: `test_privileged_fields_ids_and_unknown_fields_are_ignored` |
| m6 | `apps/users/views.py` | Quitar el mixin de `RegisterView` | 21: los 12 casos de `test_without_a_valid_token_nothing_is_created_and_the_session_is_untouched`, `test_a_foreign_origin_is_rejected_even_with_a_valid_token`, `test_the_body_is_not_read_before_the_csrf_check`, los 2 casos CSRF del cupo, `[403]` de caché y de cabeceras entre orígenes, `test_errors_carry_only_their_planned_keys[csrf-failed]`, `test_neither_the_email_nor_the_password_reach_the_logs_or_the_counter` y la guarda `test_every_project_view_that_changes_state_has_the_explicit_csrf_check` |
| m7 | `apps/users/views.py` | `throttle_classes = []` | 11: los 7 casos de `test_ten_rejected_requests_use_up_the_quota_of_the_real_endpoint`, `test_ten_registrations_use_up_the_quota_and_the_eleventh_creates_nothing`, `[429]` de caché y de cabeceras entre orígenes y el de logs (no hay clave de contador) |
| m8 | `apps/users/views.py` | Leer el cuerpo en un `initial()` propio antes de `super().initial()` | 32, entre ellos los casos `declared-too-large`, `chunked` e `invalid-json` del cupo (el rechazo sale antes del límite y no cuenta) y `test_the_body_is_not_read_before_the_csrf_check`; el resto falla porque el cuerpo ya leído llega vacío a `post` |
| m9 | `apps/users/views.py` | Comprobar CSRF en una clase de autenticación, que corre antes del límite | 4: los casos `no-csrf-header` y `token-differs-from-cookie` del cupo (los 403 no cuentan y la 11.ª da 201) y `[429]` de caché y de cabeceras entre orígenes. Además, 7 errores en `test_auth_contract.py`: la clase de la mutación no tiene extensión de drf-spectacular y el esquema no se genera con `--fail-on-warn`; es un efecto lateral, no la detección |

sha256 antes y después:

| Fichero | sha256 |
|---|---|
| `apps/users/views.py` (m1, m2 y m4 a m9) | `0c762a3c0781554c59f8bcc2c3f4da88f49d9a7a52df4890d77c00f5fe65d423` |
| `apps/users/serializers.py` (m3) | `b920a82411634b97b2af1a61428d0e369abfc1d66dcdd157a02614302108ddd0` |

## Vistas de «quién soy» y salida, y contrato (T5b)
Fecha: 2026-11-04 · Ficheros: `backend/{apps/users/views.py, apps/users/urls.py, apps/users/tests/test_session_api.py, apps/users/tests/test_logout_api.py, apps/users/tests/test_auth_contract.py, apps/users/tests/test_register_api.py, apps/users/tests/helpers.py, apps/core/tests/test_csrf_guard.py, openapi.json}` y `frontend/src/api/schema.gen.ts`. Sin migraciones.

| Comprobación | Orden | Resultado |
|---|---|---|
| Tests nuevos antes del código | `docker compose exec backend pytest -q` sobre los ficheros de la tarea | `test_csrf_guard.py` no se importa (`cannot import name 'LogoutView'`). En el resto fallan 90 por la razón esperada: 404 en las rutas que faltan y `KeyError` en el esquema. Cinco tests de la salida pasaban sin comprobar el estado de la respuesta; con la comprobación del 204 fallan también: 95 fallan y pasan los 11 de contrato de la T5a |
| Tests de la tarea tras el código | la misma orden | 201 passed: 40 en `test_session_api.py`, 48 en `test_logout_api.py`, 18 en `test_auth_contract.py` (7 nuevos), 9 en `test_csrf_guard.py` (1 nuevo) y los 86 de `test_register_api.py` (recuento con `--collect-only`) |
| Suite completa con la BD de test recreada | `docker compose exec backend pytest -q --create-db` | 2196 passed (2100 tras la T5a más 96 nuevos) |
| Estilo y formato | `docker compose exec backend sh -c "ruff check . && ruff format --check ."` | Sin incidencias; 142 ficheros formateados |
| Modelos y migraciones cuadran | `docker compose exec backend pytest -q config/tests/test_migrations.py` | 1 passed (en la BD de test) |
| Contrato | `docker compose exec -u "$(id -u)" backend python manage.py spectacular --format openapi-json --file openapi.json --validate --fail-on-warn --lang en` | Sin avisos; regenerarlo de nuevo no cambia el fichero (sha256 igual) |
| Tipos del cliente | `cd frontend && npm run api:gen`, `npm run api:check` y `npm run build` | En verde (código de salida 0). `npx eslint src/api/schema.gen.ts` solo avisa de que la configuración ignora el fichero |
| Caracteres invisibles | Detección por categoría Unicode sobre los diez ficheros tocados | 0 hallazgos |

`migrate` no se ha ejecutado en la BD de desarrollo. Durante la tarea se reinició el backend con `docker compose restart backend`, sin necesidad: al arrancar, `runserver` comprueba las migraciones pendientes y lee `django_migrations` de la BD de desarrollo, y el arranque espera a la BD con `wait_for_db`, que solo abre la conexión. No hubo escrituras.

### Contrato
`/api/v1/auth/session/`: solo `get` (drf-spectacular no publica HEAD), `operationId` `getCurrentSession`, tag `auth`, `security: [{"cookieAuth": []}, {}]`; 200 `Session` con `Set-Cookie` documentada y 405 `ApiError`. `/api/v1/auth/logout/`: solo `post`, `operationId` `logout`, tag `auth`, `X-CSRFToken` obligatoria, sin cuerpo; 204 sin cuerpo con `Set-Cookie` documentada, y 403 y 405 `ApiError`. Componente nuevo: `securitySchemes.cookieAuth` (`apiKey` en la cookie `sessionid`). El registro no cambia.

### Lo observado
| # | Comprobación | Observado |
|---|---|---|
| 1 | Fila caducada en la salida | Desaparece: `flush()` llama a `delete()` con la clave de la cookie, sin filtrar por caducidad, porque nada ha cargado antes la sesión |
| 2 | `auth.logout()` en la salida | No cargaría la sesión en esta vista: con `authentication_classes = []`, DRF pone un `AnonymousUser` en la petición de Django durante `initial()` (el setter de `Request.user` escribe también `_request.user`), y `logout()` ya no evalúa el usuario perezoso. Una sonda lo confirmó: la sesión no se ha cargado antes de `logout()`. Lo que rompe el mecanismo es leer la sesión antes de `flush()` (mutación m3b) |
| 3 | Borrado de `sessionid` en «quién soy» | Lo hace `SessionMiddleware`: al cargar, una sesión caducada, con clave mal formada (corta o larga) o sin fila deja la clave en `None`, la sesión queda vacía y la cookie se borra con `Max-Age=0`. La fila caducada no se borra en «quién soy», solo se ignora |
| 4 | Cuenta desactivada | `ModelBackend.get_user` devuelve `None` sin vaciar la sesión: «quién soy» responde `null`, sin `Set-Cookie` de sesión, y la fila sigue (riesgo aceptado en el plan) |
| 5 | 405 de «quién soy» | `initial()` rechaza el método antes de autenticar: con sesión, con y sin token, y sin sesión, POST, PUT, PATCH, DELETE y OPTIONS dan 405 con `Allow: GET, HEAD` y sin cookie `csrftoken`, porque `get_token` solo se llama en `get` |
| 6 | Borrado de la cookie en la salida | Con cookie en la petición, `SessionMiddleware` emite su propio borrado y pisa el de la vista. El de la vista se prueba sin cookie, con la configuración del proyecto y con otra (`SESSION_COOKIE_PATH="/api/"`, `SESSION_COOKIE_DOMAIN="rentradar.test"`, `SAMESITE="Strict"`), para que un `delete_cookie` sin argumentos no pase. Va sin `Secure`, como el de `SessionMiddleware`; se revisa en la 011 |
| 7 | Extracciones | `set_cookie_header()` en `views.py` (tercera cabecera `Set-Cookie` documentada) y `assert_no_store` en `tests/helpers.py` (tercer fichero que la usa); el esquema del registro sale idéntico |
| 8 | `Vary: Cookie` y 204 | El `Vary: Cookie` explícito de «quién soy» también lo ponen `CsrfViewMiddleware` y `SessionMiddleware`; el 204 sale sin cuerpo y sin `Content-Type` |

### Pruebas de mecanismo
Mutaciones sobre una copia hecha junto al fichero (`views.py.orig`), escritas sobre el mismo inode, restauradas desde la copia y con la copia borrada; sha256 idéntico antes y después y ninguna copia sin versionar. Ejecución sobre `test_session_api.py`, `test_logout_api.py`, `test_auth_contract.py` y `test_csrf_guard.py`, todas sobre la versión final de `views.py`.

| # | Mutación | Tests que fallan |
|---|---|---|
| m1 | Quitar `flush()` de la salida | 3: `test_logging_out_destroys_the_session_row`, `test_the_previous_identifier_no_longer_authenticates` y `test_an_expired_session_row_is_deleted_too` |
| m2 | Quitar `delete_cookie` de la salida | 3: `test_without_a_valid_session_it_answers_204_and_removes_the_cookie[no-cookie]` y los 2 casos de `test_without_a_session_cookie_the_view_deletes_it_with_its_settings` |
| m3 | `django.contrib.auth.logout(request._request)` en vez de `flush()` | 0: equivalente en esta vista (observación 2) |
| m3b | Leer la sesión (`session.get("_auth_user_id")`) antes de `flush()` | 1: `test_an_expired_session_row_is_deleted_too` |
| m4 | Quitar el mixin de `LogoutView` | 15: los 8 casos de `test_without_a_valid_token_nothing_changes`, los 2 de `test_the_body_is_not_read_before_the_csrf_check`, `test_a_foreign_origin_is_rejected_even_with_a_valid_token`, los 2 de `[403]` en `test_no_answer_can_be_stored_or_grants_cross_origin_access`, `test_errors_carry_only_their_code_even_with_a_staff_session[csrf-failed]` y la guarda `test_every_project_view_that_changes_state_has_the_explicit_csrf_check` |
| m5 | Quitar el rechazo del método antes de autenticar en «quién soy» | 5: `test_every_other_method_gets_405_before_authenticating` con POST con sesión (con y sin token) y PUT, PATCH y DELETE con sesión sin token |
| m6 | `authentication_classes = []` en «quién soy» | 10: `test_a_valid_session_gets_its_email_and_keeps_its_cookie`, `test_after_a_real_registration_the_session_answers_with_its_email`, los casos `expired`, `long-malformed` y `key-without-row` de `test_an_expired_malformed_or_unknown_session_is_null_and_its_cookie_deleted`, `test_a_staff_session_gets_only_its_email`, `test_the_previous_identifier_no_longer_authenticates`, `test_only_the_session_of_the_cookie_is_closed`, `test_the_session_reads_the_session_cookie_and_takes_no_input` y `test_only_the_session_declares_the_cookie_authentication` |

El `Vary: Cookie` explícito de «quién soy» es una mutación equivalente (observación 8) y no se ejecuta.

sha256 antes y después:

| Fichero | sha256 |
|---|---|
| `apps/users/views.py` (m1 a m6 y m3b) | `6e03be3ddda932922645e42936b13a0d1ae6e2e6d9b23ed3af94b052ff3cc12c` |

## Cliente de sesión, tiempo máximo común y proxy de Vite (T6)
Fecha: 2026-11-05 · Ficheros: `frontend/{src/api/timeout.ts, src/api/timeout.test.ts, src/api/session.ts, src/api/session.test.ts, src/api/publicAssets.ts, src/map/loadStyle.ts, src/i18n/format.ts, src/i18n/format.test.ts, src/i18n/es.ts, vite.config.ts}`. Sin cambios en el backend, en `package*.json` ni en el contrato.

| Comprobación | Orden (desde `frontend/`) | Resultado |
|---|---|---|
| Tests nuevos antes del código | `npx vitest run src/i18n/format.test.ts`, `npx vitest run src/api/timeout.test.ts` y `npx vitest run src/api/session.test.ts` | `format.test.ts`: 14 fallan y 37 pasan; `timeout.test.ts` y `session.test.ts` no se cargan (ver abajo) |
| Tests de la tarea tras el código | `npx vitest run --reporter=verbose src/api/timeout.test.ts src/api/session.test.ts src/i18n/format.test.ts` | 15 en `timeout.test.ts`, 239 en `session.test.ts` y 51 en `format.test.ts` (14 nuevos), todos en verde |
| Módulos de la 006 sin cambiar su comportamiento | `npx vitest run src/api/timeout.test.ts src/api/publicAssets.test.ts src/map/loadStyle.test.ts` | 102 passed; `publicAssets.test.ts` y `loadStyle.test.ts` pasan sin editarse |
| Suite completa | `npx vitest run` | 21 ficheros, 832 passed (564 antes de la tarea, más 239, 15 y 14) |
| Análisis estático de los diez ficheros | `npx eslint src/api/session.ts src/api/session.test.ts src/api/timeout.ts src/api/timeout.test.ts src/api/publicAssets.ts src/map/loadStyle.ts src/i18n/format.ts src/i18n/format.test.ts src/i18n/es.ts vite.config.ts` | Sin incidencias (código de salida 0) |
| Tipos y empaquetado | `npm run build` (`tsc -b && vite build`) | Código de salida 0 |
| Tipos del cliente | `npm run api:check` | Código de salida 0, sin cambios |

No se ha levantado, parado ni reiniciado Vite ni Docker, y no se ha tocado la BD de desarrollo.

Tests que no se editan, con el mismo sha256 antes y después de la tarea:

| Fichero | sha256 |
|---|---|
| `src/api/publicAssets.test.ts` | `801327dc525cedd73b117fa5701941f5941021345569aa518f9c9e44db8f8546` |
| `src/map/loadStyle.test.ts` | `1a76aac5c98e808364bb5f770236e04548fe25a3f3a01eb4c659ebaf7c439c04` |
| `src/api/http.test.ts` | `7ef1b4f921a23430eeb7d1af66814ab2b2244e5f177b7029c220ce5cfef75849` |
| `src/api/validate.test.ts` | `1f4c6dceed962e8f0ab6376f43c656546454061e0eba329160868c159ddc342e` |

### Tests que fallaron primero
| Fichero | Fallo | Razón |
|---|---|---|
| `src/i18n/format.test.ts` (14) | `TypeError: waitMinutes is not a function` (9) y `throttledMessage is not a function` (5) | Las funciones no existen |
| `src/api/timeout.test.ts` | `Cannot find module './timeout'` | El módulo no existe |
| `src/api/session.test.ts` | `Cannot find module './session'` | El módulo no existe |

Con los módulos creados, dos tests de `session.test.ts` fallaron por el propio test y se corrigieron: el fetch simulado de «un fallo de red que llega con el temporizador ya disparado» solo escuchaba el aborto y no miraba si la señal ya estaba abortada (el temporizador vence antes de que el simulado reciba la petición), y el de nombres heredados esperaba dos «unknown» cuando Zod descarta la clave `__proto__` (ver «Lo observado», 6).

Cuerpo cortado: se sustituyó el test que fijaba que un `TypeError` al leer el cuerpo se propaga por 21 nuevos (14 del cuerpo cortado en las tres operaciones y 7 de «un error que no es un `TypeError` se propaga») y se ejecutaron antes de tocar `session.ts`: 14 fallaron con `TypeError: terminated` propagado (`whoAmI` cortado, `register` con 400, 404, 413, 429, 403, 201 con sesión y 201 sin sesión, con 500 o con la red caída, y `logout` con 400, 403, 404 y 429) y los 7 de propagación de otro error pasaron ya en la versión anterior (son el candado de que el cambio no se pasa de largo).

### Lo observado
| # | Comprobación | Observado |
|---|---|---|
| 1 | `runWithTimeout` | Es la tercera repetición del enlace de la señal externa con el temporizador (`publicAssets.ts`, `loadStyle.ts` y el cliente de sesión). La señal externa es opcional: con ella se llama a `throwIfAborted()` antes de armar nada, y sin ella actúa solo el temporizador. Un fallo de la tarea tras vencer sigue siendo un tiempo vencido; un aborto externo sale tal cual. El envoltorio `TypeError` a `NetworkError` se queda en `publicAssets.ts`: sería la segunda copia |
| 2 | Credenciales | `session.test.ts` comprueba `same-origin` en `whoAmI`, registro, salida y sus reintentos (9 llamadas en un solo recorrido), y con `expectTypeOf`, que `tsc -b` verifica en el build, que `SessionFetchInit["credentials"]` es `"same-origin"` y `FetchInit["credentials"]` sigue siendo `"omit"`. El público sigue en `omit` con los tests que ya existen en `publicAssets.test.ts` («pide la ruta con los cuatro límites, sin credenciales» y «la instancia real usa fetch sin credenciales y un tiempo máximo de 10 s»), que no se tocan |
| 3 | Instancia real `sessionClient` | Solo se prueba `whoAmI` (fetch global, `setTimeout` de 5 s armado y cancelado): `readCookies` evalúa `document.cookie`, que no existe en vitest con entorno `node`, y los tests no lo tocan. El tiempo de 10 s del registro y de la salida de la instancia real no tiene test; se ve en la T9, en el navegador |
| 4 | Token CSRF | Se lee con `readCookies()` en cada envío (también en el reintento), nunca se guarda, y solo viaja en `X-CSRFToken` si cumple `^[A-Za-z0-9]{32}([A-Za-z0-9]{32})?$`; si no, no hay cabecera y el servidor responderá `csrf_failed` (un token corto, uno de 33 caracteres, uno con símbolos, sin cookie). `readCsrfToken` salta los `csrftoken=` mal formados y devuelve el primero válido |
| 5 | Reintento | Un solo reintento tras `csrf_failed`, con `whoAmI()` entre medias y el token releído. En el registro se reintenta aunque «quién soy» diga que hay sesión, falle por red o dé un 500; en la salida, aunque diga que no hay sesión. Un `csrf_failed` con estado 400 o un 403 `forbidden` no se reintentan. Cada intento arma su propio temporizador: `[10000, 5000, 10000]` |
| 6 | Errores por campo | La lista de códigos conocidos es cerrada por campo; un código desconocido en un campo conocido pasa a `"unknown"` en ese campo, una clave desconocida con al menos un código pasa a `"unknown"` en `other`, y ninguno de los dos da `failed("invalid")`. Solo es inválida la forma de `params`. Zod descarta la clave `__proto__` del registro (sondeado: `Object.entries` del resultado solo trae `constructor` y `email`), así que no llega a `other`; `constructor` sí es un campo desconocido |
| 7 | Esquemas | `z.strictObject` en la sesión, en el 201 del registro (con `user` obligatorio) y en `apiErrorSchema`. La aserción en compilación frente a `components["schemas"]["Session"]` es el tipo de retorno de `parseSession`; sondeado con `email: z.number()` en una copia: `tsc -b` da `TS2322` en `session.ts(103,27)`; restaurado con `cp` (sha256 igual, `22a68333…`). En `schema.gen.ts`, `ApiError.params` está tipado como `{[key: string]: string}` y la realidad (`invalid_fields`) son listas (`RegistrationError`): no se fuerza esa aserción y `apiErrorSchema` admite `string | string[]` |
| 8 | 429 | `retryAfterSeconds` sale del cuerpo (entero de 1 a 86400); la cabecera `Retry-After` se ignora. Sin `retry_after`, con 0, con 86401, decimal, como texto o con cuerpo que no es JSON: `failed("invalid")` |
| 9 | 5xx y estados inesperados | Un 5xx no lee el cuerpo (`bodyUsed` sigue en falso). Un 2xx distinto de 201 (en la salida, distinto de 204), un 3xx o un 1xx son `failed("invalid")` sin preguntar «quién soy» |
| 10 | Errores y cuerpo cortado | Dos orígenes dan fallo de red: el `TypeError` de `fetch` y el `TypeError` que sale de leer el cuerpo (`readJson` lo convierte en `SessionNetworkError`; un `SyntaxError` sigue siendo un cuerpo no JSON y cualquier otro error, un `RangeError` por ejemplo, se propaga también en `whoAmI`). `whoAmI` con el cuerpo cortado da `"anonymous"`. `register` con un 4xx cortado (también un 403, del que no se puede saber si era `csrf_failed`) da `failed("network")` sin preguntar «quién soy» y sin reintento. `register` con un 201 cortado pregunta «quién soy»: con sesión es `registered` y sin ella `failed("network")`. `logout` con un 4xx cortado da `failed("network")` sin reintento; su 204 y los 5xx no leen el cuerpo. En todos el temporizador se cancela una vez por intento y no se escribe en la consola. Un `AbortError` de quien lo pide sale tal cual |
| 11 | Consola | `whoAmI` no escribe en la consola en ninguno de sus fallos (los cinco métodos de `console` espiados) ni el registro ante un fallo de red |
| 12 | `invalid_fields` vacío | Sin ninguna entrada en ningún campo (`params` vacío, campos conocidos con listas vacías, un campo desconocido con lista vacía) da `failed("invalid")`: decisión conservadora |
| 13 | 429 con otro `code` | Un 429 con un `code` distinto de `throttled` (`algo_nuevo`, `rate_limited`) y un `retry_after` válido sigue siendo `throttled`: no se exige el `code`, solo el estado 429 y el `retry_after` del cuerpo. Lo fija «un 429 con el code %s también es throttled: no se exige el code» (`session.test.ts:710`); pasó desde el primer momento porque el código ya se comportaba así |

### Pruebas de mecanismo
Mutaciones sobre una copia hecha junto al fichero (`<fichero>.orig`), restaurada con `cp` y borrada; sha256 de antes y de después idéntico en todas y ninguna copia sin versionar (`git status -sb` limpio de copias tras cada una). Ejecución: `npx vitest run src/api/session.test.ts src/api/timeout.test.ts src/api/publicAssets.test.ts src/map/loadStyle.test.ts src/i18n/format.test.ts` (368 tests). Sobre `session.ts`, las mutaciones 1 a 4 se hicieron en cada copia del código por separado (registro y salida) y en conjunto cuando procede, para que una cobertura que solo viera una de las dos no pase.

| # | Mutación | Tests que fallan | sha256 durante |
|---|---|---|---|
| 1a | Quitar el reintento del registro | 8: los 7 de «register: el reintento ante csrf_failed» (reintenta una sola vez releyendo el token, error general tras el segundo `csrf_failed`, reintenta aunque «quién soy» responda con sesión, con un 500 o con la red caída, el resultado del reintento, reintento que vence) y «las credenciales de todas las llamadas» | `401af2d1c7a03b6bd7004ffabcad1bbe9bb5d408d5a5ecfa046d6eb737706e29` |
| 1b | Quitar el reintento de la salida | 7: «logout» ante `csrf_failed` reintenta y relee el token, reintenta aunque «quién soy» responda sin sesión, con un 500 o con la red caída, error general tras el segundo `csrf_failed`, reintento que vence, y «las credenciales de todas las llamadas» | `f94e35bd6497105f9f70b2dbf7aae298be944efcd6790205565503f612ee24de` |
| 1 | Quitar ambos reintentos | 14: la unión de 1a y 1b | `5e8f69572ba2ca2885eee44701a5b57fbd23fad0d74a5274b17de6fa9518410f` |
| 2a | Reintentar dos veces el registro | 1: «register: si el segundo intento vuelve a dar csrf_failed, es el error general y no hay un tercer envío» | `12385ac31a632b3354aad83e5f27ea5950a00c240229ca5ac016168065a8a103` |
| 2b | Reintentar dos veces la salida | 1: el mismo caso en «logout» | `544cb385c5fe2050cab8ba5f53e30922a9f478d569ee7b6eb0b19c71254c676d` |
| 2 | Reintentar dos veces ambos | 2: los dos anteriores | `0a46f341104fd8a2e2d343f8b6ee37b229f738ecdf7704d4f43500aa2d2f474d` |
| 3 | Guardar el token en una variable en vez de leerlo en cada envío | 4: «lee la cookie en cada envío, sin guardar el token» en el registro y en la salida, y el reintento que relee el token en ambos | `6116ee0f6b09da6aa5c6f4f59817c050acf052464e080461ab8196c864794aeb` |
| 4a | `credentials: "omit"` en «quién soy» | 3: «whoAmI: hace un GET…», «las credenciales de todas las llamadas» y «sessionClient: la instancia real» | `a4f00e685bfc1060cd98b0944f788413d1d821d43f59f5b10d63b7504571dc96` |
| 4b | `credentials: "omit"` en el registro | 2: «register: hace un POST JSON…» y «las credenciales de todas las llamadas» | `8245dcab10faa20a459051d583a4082f2363a361beda53795431bf51425b74f0` |
| 4c | `credentials: "omit"` en la salida | 2: «logout: hace un POST…» y «las credenciales de todas las llamadas» | `69e96f2b080f2c0ce48aad69e9213321f12a7ebd8d2b9c12c47ace228b0302e1` |
| 5 | Quitar el tiempo máximo de «quién soy» | 13: 6 de `whoAmI` (el temporizador de 5 s, fallo de red, vencimiento, cuerpo que no llega, cancelado, señal ya abortada), 2 del reintento del registro, 2 del tiempo máximo del registro (vence y la pregunta tiene su propio temporizador de 5 s), 2 de la salida y la instancia real | `cf2274f23419c7550a797bfbe8c8af22cf39b58311ec30cec6cc42e2c50c30e0` |
| 6 | Quitar el tiempo máximo del registro | 12: la petición (10 s), 2 del reintento, 8 de «register: el tiempo máximo» (vence con y sin sesión, con «quién soy» en 500, red o forma inválida, cuerpo a medias, error de red con el temporizador disparado, temporizador propio de «quién soy») y el `TypeError` de red (temporizador cancelado) | `998a8d69de3bbfe9f6fcc71e2891d961052049d2107193cee9cf605e0b84150a` |
| 7 | Quitar el tiempo máximo de la salida | 4: la petición (10 s), el reintento (tres temporizadores), «vencido a los 10 s es failed timeout…» y «si el reintento vence…» | `47f0c33fab40bf6479f12aec1b59cb9aafd28654769c9ef6502c950c6278a952` |
| 8 | No preguntar «quién soy» tras un registro vencido | 4: «espera 10 s, aborta la petición y, con sesión, es un éxito», «un cuerpo que llegó a medias también vence a los 10 s», «la pregunta de quién soy tras vencer tiene su propio temporizador de 5 s» y «si el reintento vence, pregunta quién soy…» | `b1a396d537129ecefc64a22077f01f32927a744912f74dec8cd59fa1b369a321` |

Ninguna sobrevivió. En un primer intento las mutaciones 6 y 7 dejaban un error de sintaxis (una coma sobrante) y la suite entera no se cargaba: se descartaron, se corrigió la edición y se repitieron; la tabla es de la repetición. Las mutaciones 1 a 8 y las de `timeout.ts` se hicieron sobre la versión de `session.ts` anterior al cuerpo cortado (sha256 `22a68333431ecb2f8223d5a163b5c545146fbc7f7b9723ab536399dcdbdbe96c`, con 368 tests en la ejecución) y no se han repetido sobre la versión final; `timeout.ts` no ha cambiado desde entonces. Las nuevas (m9 a m11, más abajo) se hicieron sobre la versión final de `session.ts`. La mutación de quitar `.trim()` de `hasJsonContentType` no se usa: es equivalente (`Headers` ya normaliza los espacios de los extremos).

Mutaciones adicionales sobre `timeout.ts` (el módulo es nuevo y tiene sus propios tests; cada una la detecta además algún test de `publicAssets` o `loadStyle`):

| # | Mutación | Tests que fallan | sha256 durante |
|---|---|---|---|
| t1 | Sin `signal?.throwIfAborted()` | 4: señal ya abortada en `timeout`, `session`, `publicAssets` y `loadStyle` | `59d27e771261664931ca9eb58c64433191426afd213552a0d18a1991d9c220d7` |
| t2 | Sin `clearTimer(timer)` | 47: 6 de `timeout.test.ts` (los 5 de «limpieza del temporizador» y «abortada durante la tarea»), 12 de `session.test.ts`, 24 de `publicAssets.test.ts` y 5 de `loadStyle.test.ts` | `89c7556ca940dc4e119eeef9d8db717c92046bfb668936ae8abc154f6f40d6f5` |
| t3 | Sin retirar el listener de la señal externa | 5: 2 de `timeout.test.ts` (tras un éxito y tras un fallo) y 3 de `publicAssets.test.ts` | `515dd80f55314ab6fdd54667bbbf6bd15edb0bb6851183da163d1f79dd995b64` |
| t4 | Sin lanzar `onTimeout()` al vencer | 21: 3 de `timeout.test.ts`, 13 de `session.test.ts`, 3 de `publicAssets.test.ts` y 2 de `loadStyle.test.ts` | `4271f62d448d69810331ac81c5ba29980f8043848693af8e59022d43a2636645` |
| t5 | Sin enlazar la señal externa al controlador | 10: 3 de `timeout.test.ts`, 1 de `session.test.ts`, 5 de `publicAssets.test.ts` y 1 de `loadStyle.test.ts` | `1adc88d81cd6bba39125bf884e29dc717f5d97bca7eb802f0187ab22eb907351` |
| t6 | Un aborto externo marca el tiempo como vencido | 7: 2 de `timeout.test.ts`, 1 de `session.test.ts`, 3 de `publicAssets.test.ts` y 1 de `loadStyle.test.ts` | `c2b55132cd52745734e5b836ab913beafa2f2f9786b410d982e3cd90c5245c71` |
| t7 | El aborto externo pierde su motivo (`controller.abort()`) | 3: 2 de `timeout.test.ts` y «cancelado por quien lo pide…» de `session.test.ts` | `c91f2d9b1b65b30be7038510c8cc51dd99be705f0280d1780923271488e847bc` |
| t8 | El temporizador no aborta el controlador interno | 22: 4 de `timeout.test.ts`, 13 de `session.test.ts`, 3 de `publicAssets.test.ts` y 2 de `loadStyle.test.ts` | `5bd851d26efca1371b6b5870bcf688f8482c34dd00c05714a083f5379cbcc52f` |

Mutaciones del cuerpo cortado y de los dos tests posteriores, sobre la versión final de `session.ts` y, la m13, sobre `timeout.ts` (388 tests en la ejecución de los cinco ficheros en m9 a m11 y 392 en m12 y m13):

| # | Mutación | Tests que fallan | sha256 durante |
|---|---|---|---|
| m9 | Quitar la conversión `TypeError` a `SessionNetworkError` de `readJson` | 14: `whoAmI` con el cuerpo cortado, `register` con 400, 404, 413, 429 y 403, `register` con un 201 cortado (con sesión, sin sesión, con «quién soy» en 500 y con la red caída) y `logout` con 400, 403, 404 y 429 | `5826e54e47188fe5995252d9b46c08929bd021964fce11f86fffae09fd399ef3` |
| m10 | Un 201 con el cuerpo cortado da `failed("network")` sin preguntar «quién soy» | 4: los cuatro de «un 201 con el cuerpo cortado» (con sesión es `registered`, y sin sesión, con 500 y con la red caída esperan la pregunta) | `5d52a326ee2d84395421bef4a45639923823bbb980eaef00f237d467e10032d7` |
| m11 | Convertir cualquier error del cuerpo, no solo el `TypeError`, en `SessionNetworkError` | 7: «un error que no es un `TypeError` al leer el cuerpo se propaga» en `whoAmI`, en `register` (201, 400, 403 y 429) y en `logout` (400 y 403) | `1aee08495210ab40a100be4809798df004da95a93c9970933348ce30bdb11826` |
| m12 | Exigir `error.code === "throttled"` para entrar en la rama del 429 (`session.ts`) | 2: «un 429 con el code algo_nuevo también es throttled: no se exige el code» y el de `rate_limited`; ningún test anterior la mata | `6de83e6858512df6fc717869d2496fed649b514fb7674e38c1238ba1f5428c07` |
| m13 | `runWithTimeout` lanza `onTimeout()` también cuando la tarea termina bien con el temporizador vencido (`timeout.ts`) | 1: «un 201 cuyo cuerpo se corta con un TypeError al vencer el temporizador pregunta quién soy y, sin sesión, gana la etiqueta del valor devuelto». El caso «con sesión» no la detecta por sí solo: con sesión el resultado es `registered` con o sin la mutación; la distingue la etiqueta del caso sin sesión (`failed("network")` frente a `failed("timeout")`) | `6966056b304af34c518dd6d578a8d54cee60359b903a15195ac8e854fb864878` |

sha256 antes y después (idénticos en todas las mutaciones de cada fila):

| Fichero | sha256 |
|---|---|
| `src/api/session.ts`, versión anterior al cuerpo cortado (mutaciones 1 a 8) | `22a68333431ecb2f8223d5a163b5c545146fbc7f7b9723ab536399dcdbdbe96c` |
| `src/api/session.ts`, versión final (mutaciones m9 a m12) | `3fa041cef932d6b7b0d58e195bf58a7c0dc4d4feb696308e824ac0fae35f1eeb` |
| `src/api/timeout.ts` (mutaciones t1 a t8 y m13) | `540d138665201900595cff373353ab791ba7c5c590656d6bc2cebdc57f743edb` |

### Proxy de Vite (desviación de la T7 de la 006)
**a) La decisión de la 006 no se cumplía.** La T7 de la 006 decidió el proxy «sin `changeOrigin`», pero la configuración era la forma abreviada `"/api": "http://localhost:8000"`, que Vite convierte en `changeOrigin: true`: Django recibía `Host: localhost:8000` con `Origin: http://localhost:5173`. Pasó desapercibido porque Django no comprueba el `Origin` en los GET y la 006 solo hacía GET. Ahora el proxy es un objeto con `changeOrigin: false`, de modo que Django recibe `Host: localhost:5173` y el origen coincide con el host. Ningún test de vitest cubre `changeOrigin: false`: se valida en la T9 con un POST real a través del proxy (el registro funciona sin `CSRF_TRUSTED_ORIGINS` y Django recibe `Host: localhost:5173`). `CSRF_TRUSTED_ORIGINS` no está definido en ningún `settings` (comprobado con `grep -rn CSRF_TRUSTED_ORIGINS backend --include=*.py`: solo aparece en el código de Django del entorno virtual); `backend/config/settings/development.py:22` solo fija `ALLOWED_HOSTS = ["localhost", "127.0.0.1"]`, que Django compara sin el puerto.

**b) Código de Vite 8.3.5 que lo causa**, copiado de `frontend/node_modules/vite/dist/node/chunks/node.js` (indentado con tabuladores en el original). Líneas 19895 a 19898, que convierten la forma abreviada:

```js
		if (typeof opts === "string") opts = {
			target: opts,
			changeOrigin: true
		};
```

Líneas 19901 a 19907, que responden al error del proxy:

```js
		proxy.on("error", (err, _req, res) => {
			if ("req" in res) {
				config.logger.error(`${import_picocolors.default.red(`http proxy error: ${res.req.url}`)}\n${err.stack}`, {
					timestamp: true,
					error: err
				});
				if (!res.headersSent && !res.writableEnded) res.writeHead(502, { "Content-Type": "text/plain" }).end();
```

**c) Consecuencia para la T9.** Con el backend parado el proxy responde 502 `text/plain` sin cuerpo, así que el registro y la salida dan `failed("server")` y «quién soy» dice `"anonymous"`; `failed("network")` solo aparece si el propio Vite está caído.

**d) La cookie `csrftoken`** solo la fija `get_token` en `CurrentSessionView.get` (`backend/apps/users/views.py:144`): el primer POST sin un «quién soy» previo recibe 403 `csrf_failed` y el cliente depende del reintento tras `whoAmI`.

### Decisiones sin cobertura en el plan
- `invalid_fields` sin ninguna entrada, y un campo desconocido cuya lista de códigos está vacía, dan `failed("invalid")` o no aportan `"unknown"` (la entrada es un código, no una clave).
- Cada código desconocido, y cada clave desconocida con al menos un código, aporta un `"unknown"`; no se agrupan los repetidos.
- Un `TypeError` al leer el cuerpo es un fallo de red (`readJson` lo convierte en `SessionNetworkError`); cualquier otro error al leerlo se propaga. Con un 4xx cortado, `register` y `logout` dan `failed("network")` sin «quién soy» y sin reintento, también con un 403 que podría ser `csrf_failed`. Con un 201 cortado, `register` pregunta «quién soy» y, sin sesión, da `failed("network")`. Si el `TypeError` del cuerpo de un 201 llega con el temporizador ya vencido, la etiqueta es `failed("network")` y no `failed("timeout")`; ambas preguntan antes «quién soy». Está fijado por «un 201 cuyo cuerpo se corta con un TypeError al vencer el temporizador pregunta quién soy y, con sesión / sin sesión, gana la etiqueta del valor devuelto» (`session.test.ts:556`): con sesión da `registered` y sin sesión `failed("network")`.
- Se exportan las listas `EMAIL_ERROR_CODES`, `PASSWORD_ERROR_CODES` y `OTHER_ERROR_CODES`, de las que salen los tipos, para que el catálogo de mensajes pueda comprobar «un texto por código».

### Repetición de mutaciones sobre la versión final de `session.ts`
Las mutaciones 1 a 4 de arriba se hicieron sobre la versión anterior al cuerpo cortado. Aquí se repiten sobre la versión final (sha256 `3fa041cef932d6b7b0d58e195bf58a7c0dc4d4feb696308e824ac0fae35f1eeb`), junto con la del 429. Cada una con copia junto al fichero (`session.ts.orig`), restaurada con `cp` y borrada; el sha256 de antes y después es el mismo en todas y no queda ninguna copia (`git status -sb` limpio de copias). Las cinco primeras con `npx vitest run --reporter=verbose src/api/session.test.ts` (235 tests entonces); r6, con los cinco ficheros de la tarea (392 tests).

| # | Mutación | Tests que fallan | sha256 durante |
|---|---|---|---|
| r1 | Quitar el reintento del registro | 8: 7 de «register: el reintento ante csrf_failed» (reintento y token releído, tras un segundo `csrf_failed`, aunque «quién soy» responda con sesión, con la red caída o con un error del servidor, resultado del reintento, reintento que vence) y «las credenciales de todas las llamadas». Los dos de ese bloque que no fallan son los que comprueban que no se reintenta (403 con otro código, `csrf_failed` con otro estado) | `37e338fd95b698a581ce710384fd4ef16ec4df243101bdbe1356f81f942a71d2` |
| r2 | Quitar el reintento de la salida | 7: 6 de «logout» (reintenta y relee el token, aunque «quién soy» responda sin sesión, con la red caída o con un error del servidor, reintento que vence, segundo `csrf_failed`) y «las credenciales de todas las llamadas» | `6288cdf468b8349ad0e46dc85ecf6570c93e9f7a45f852fbdbca3b5076d0b106` |
| r3 | Reintentar dos veces el registro | 1: «si el segundo intento vuelve a dar csrf_failed, es el error general y no hay un tercer envío» (registro) | `8654baae91e3115f700da73d2f2c83c3379f1b522738c9f7c03954477fba934e` |
| r4 | Reintentar dos veces la salida | 1: el mismo caso en «logout» | `093eb62e491aa6cf3172a0d21b1f958bd0050efbb408a2be5ea3b021cb404bae` |
| r5 | Guardar el token en una variable en vez de leerlo en cada envío | 4: «lee la cookie en cada envío, sin guardar el token» en el registro y en la salida, y el reintento que relee el token en ambos | `d4bcd83aaa0d6ab44c27b513a8d77ed8306d566af4d407506bacd71064c6143f` |
| r6 | Exigir `error.code === "throttled"` en la rama del 429 | 2: los dos casos de «un 429 con el code %s también es throttled: no se exige el code» (`algo_nuevo` y `rate_limited`). Ningún test anterior la mata | `6de83e6858512df6fc717869d2496fed649b514fb7674e38c1238ba1f5428c07` |

r6 repite m12. m13 también se repitió, sobre `timeout.ts` (sha256 de antes y después `540d138665201900595cff373353ab791ba7c5c590656d6bc2cebdc57f743edb`), con el mismo sha256 durante que el registrado arriba (`6966056b304af34c518dd6d578a8d54cee60359b903a15195ac8e854fb864878`) y el mismo único test que la mata, el caso «sin sesión» del 201 cortado con el temporizador vencido.

## Navegación interna, barra superior, estado de sesión y zona de contenido (T7)
Fecha: 2026-11-05 · Ficheros: `frontend/src/{app/navigation.ts, app/navigation.test.ts, app/AppShell.tsx, app/TopBar.tsx, app/TopBar.test.ts, app/LogoutNotice.tsx, app/NotFoundPage.tsx, session/sessionState.ts, session/sessionState.test.ts, session/SessionProvider.tsx, main.tsx, pages/MapPage.tsx, i18n/es.ts}`. Sin cambios en el backend, en `package*.json` ni en el contrato. La comprobación en el navegador queda para la T9.

| Comprobación | Orden (desde `frontend/`) | Resultado |
|---|---|---|
| Tests nuevos antes del código | `npx vitest run src/app/navigation.test.ts`, y después `npx vitest run src/session/sessionState.test.ts src/app/TopBar.test.ts` | No se cargan: `Cannot find module './navigation'`, `'./sessionState'` y `'./LogoutNotice'` |
| Tests de la tarea tras el código | `npx vitest run src/app/navigation.test.ts src/session/sessionState.test.ts src/app/TopBar.test.ts` | 68 passed: 15 en `navigation.test.ts`, 37 en `sessionState.test.ts` y 16 en `TopBar.test.ts` |
| Suite completa | `npx vitest run` | 900 passed (832 antes de la tarea más 68); ningún test existente cambia |
| Análisis estático de los trece ficheros | `npx eslint <los trece ficheros>` | Sin incidencias (código de salida 0) |
| Tipos y empaquetado | `npm run build` (`tsc -b && vite build`) | Código de salida 0; solo el aviso del chunk de maplibre-gl, que ya existía |
| Tipos del cliente | `npm run api:check` | Código de salida 0, sin cambios |

No se ha levantado, parado ni reiniciado Vite ni Docker, y no se ha tocado la BD de desarrollo.

Con los módulos creados, un test de `TopBar.test.ts` falló por el propio test: buscaba `aria-disabled` en todo el botón y encontraba la clase `aria-disabled:opacity-60`. Ahora busca el atributo.

### Lo observado
| # | Comprobación | Observado |
|---|---|---|
| 1 | React StrictMode | `main.tsx` monta la aplicación dentro de `<StrictMode>`. En desarrollo, React monta, desmonta y vuelve a montar cada efecto, así que al cargar la página salen **dos GET a `/api/v1/auth/session/`**: el primero lo cancela la limpieza del efecto (en la pestaña Red aparece como cancelado) y el segundo decide el estado. No es un fallo: `loadSessionStatus` devuelve `null` con la señal abortada y no escribe estado ni consola. En el build de producción sale uno solo. Lo mismo pasa ya con el mapa (`MapView` lo crea y lo libera dos veces en desarrollo) |
| 2 | Aviso de fallo de «Salir» (desviación del plan) | El plan lo ponía como franja bajo la barra que hacía ceder alto a la zona de contenido (`flex-1 min-h-0`). Va **superpuesto** en la parte superior de la zona (`absolute inset-x-0 top-0 z-20`), sin cambiar su alto. Motivo: la región del aviso se vacía al empezar cada intento y se rellena al fallar, para que un segundo fallo igual vuelva a anunciarse; si ocupara alto, el mapa se redimensionaría dos veces en cada reintento. La región `role="status"` está siempre montada y, vacía, no mide nada ni capta clics (`pointer-events-none`; la tarjeta, `pointer-events-auto`). Mientras se ve tapa la parte superior del mapa, incluidos los botones de zoom: se mira en la T9 |
| 3 | Alto de la zona | Columna `flex h-dvh flex-col`; barra `h-14 shrink-0`; zona `relative min-h-0 flex-1`. La columna tiene un alto definido (`h-dvh`) y la zona recibe el alto sobrante por `flex-1` (`flex: 1 1 0%`): el tamaño de un elemento flexible en un contenedor de alto definido cuenta como definido, así que `h-full` de `MapPage` (`relative h-full overflow-hidden`) se resuelve contra él. `min-h-0` quita el `min-height: auto` del elemento flexible, que si no impediría encogerlo por debajo del contenido y provocaría scroll de página. `shrink-0` mantiene los 56 px de la barra |
| 4 | «Página no encontrada» | El plan decía `min-h-full`, pero con eso el contenido que no cupiera crecería fuera de la zona y daría scroll de página. Va `flex h-full flex-col items-center justify-center-safe gap-6 overflow-y-auto p-4 text-center`: se desplaza dentro de la zona, y `justify-center-safe` (`justify-content: safe center`, presente en el CSS generado) evita que el centrado corte el principio del contenido |
| 5 | Rechazo de «quién soy» | `whoAmI` resuelve por su cuenta la red y el tiempo vencido sin escribir en la consola, así que lo que rechaza es un fallo del código: `loadSessionStatus` lo registra con `logError` (`console.error` en `main.tsx`) y deja el estado sin sesión, de modo que la barra nunca se queda sin acciones. Con la señal abortada devuelve `null`, tanto si `whoAmI` rechaza como si resuelve tarde: el resultado de una petición cancelada nunca se aplica |
| 6 | Carrera entre el arranque y el registro | `statusAfterWhoAmI` solo aplica la respuesta en `unknown`. El formulario de registro se pinta sin esperar a «quién soy», y una respuesta sin sesión que salió antes del registro y llega después no deshace `markRegistered`; tampoco una con sesión que llega después de salir |
| 7 | `markRegistered` | Pasa a `authenticated`, retira el aviso de salida y anuncia «Cuenta creada.» en la región global (`sr-only`), que vive en `AppShell` y sobrevive al `replace("/map")` de la página de registro. La lógica es `registrationResult`, con su test; el cableado en el contexto se comprueba al usarlo en la T8 y en el navegador en la T9 (vitest corre en `node`, sin efectos de React) |
| 8 | Rechazo de la salida (decisión sin cobertura en el plan) | `logout()` del cliente propaga un error que no es de red ni de tiempo. `settleLogout` lo registra y lo trata como un fallo más (`failed("unexpected")`): sin eso, «Salir» quedaría en `aria-disabled` para siempre. Cualquier fallo da el mismo resultado: la sesión sigue, foco en «Salir» y el aviso con «Reintentar». No se pregunta «quién soy»: reintentar sin sesión también responde 204 |
| 9 | Anuncios | «Has salido» y «Cuenta creada.» van a la región global; el fallo de salida lo anuncia solo la región del aviso, para no anunciarlo dos veces. La región global se vacía al empezar cada salida |
| 10 | Foco | El foco a «Registrarse» tras salir se aplica en un efecto de `AppShell`, después de pintar el nuevo estado (el enlace no existe antes y el botón «Salir» desaparece enfocado). Al cambiar de página, el foco va a la zona (`tabIndex=-1`), pero no en la carga inicial. La regla global `:focus-visible` de `index.css` no está en una capa de Tailwind, así que también dibujará el contorno de la zona si se llega a ella con el teclado: se mira en la T9 |
| 11 | Ruta del registro | Hasta la T8, `resolveRoute` no conoce `/register` y el enlace «Registrarse» lleva a «Página no encontrada» |
| 12 | Panel | `ResultsPanel` sigue con `h-[40dvh]`, una unidad del viewport y no de la zona: a 375×667 ocupa unos 267 px de los 611 de la zona (≈44 %). No cambia en esta tarea; se mira en la T9 |

### Pruebas de mecanismo
La tarea es de interfaz y no las exige. Se hacen dos, más dos variantes de la segunda que separan sus dos comprobaciones. Cada una sobre una copia hecha junto al fichero (`sessionState.ts.orig`), restaurada con `cp` y borrada; sha256 idéntico antes y después y ninguna copia sin versionar. Ejecución: `npx vitest run src/session/sessionState.test.ts src/app/TopBar.test.ts src/app/navigation.test.ts` (68 tests).

| # | Mutación | Tests que fallan | sha256 durante |
|---|---|---|---|
| m1 | Quitar `current === "unknown"` de `statusAfterWhoAmI` (`return result`) | 3: «una respuesta sin sesión que llega tras registrarse no deshace el registro», «una respuesta con sesión que llega tras salir no vuelve a mostrar Salir» y «la respuesta de quién soy del arranque que llega después no la deshace» | `0b2aeaf90a3d6f34e2eb7a2175ca3ec63746478f495890f7bb368003a61a9e7b` |
| m2 | Quitar las dos comprobaciones de la señal abortada de `loadSessionStatus` | 4: «cancelada y rechazada con su AbortError», «cancelada y rechazada con otro error» y «cancelada y resuelta después» con `anonymous` y con `authenticated` | `76591094c2461b8cc91ddda57ab986c653347e60e69a2e305e5fba3018cfe885` |
| m2a | Quitar solo la del resultado (`signal.aborted ? null : result`) | 2: «cancelada y resuelta después» con `anonymous` y con `authenticated` | `4b48f7f2d4b1c47b610b5a1a5bd159c24e8c4b642be597fe5a22896ba18e9e8c` |
| m2b | Quitar solo la del rechazo (`if (signal.aborted) return null`) | 2: «cancelada y rechazada con su AbortError» y «cancelada y rechazada con otro error» | `979d179553939e7f53ba67a6dd980a9a23763c05dc99829090e8949f8d01765e` |

sha256 antes y después:

| Fichero | sha256 |
|---|---|
| `src/session/sessionState.ts` (m1, m2, m2a y m2b) | `9fc3a770677d852efe37f2b21351fe6927e580d3a71971243558d4a52cfd545b` |

## Página de registro (T8)
Fecha: 2026-11-05 · Ficheros: `frontend/src/{register/registerForm.ts, register/registerForm.test.ts, register/RegistrationForm.tsx, register/RegistrationForm.test.ts, pages/RegisterPage.tsx, app/route.ts, app/route.test.ts, app/AppShell.tsx, main.tsx, i18n/es.ts, styles/index.css}`. Sin cambios en el backend, en `package*.json` ni en el contrato. Dos commits: la lógica (`registerForm.ts`, su test y `es.ts`) y la página con la ruta. La comprobación en el navegador queda para la T9.

| Comprobación | Orden (desde `frontend/`) | Resultado |
|---|---|---|
| Tests de la lógica antes del código | `npx vitest run src/register/registerForm.test.ts` | No se carga: `Cannot find module './registerForm'` |
| Tests de la lógica tras el código | la misma orden | 81 passed |
| Tests de ruta y marcado antes del código | `npx vitest run src/app/route.test.ts src/register/RegisterForm.test.ts` (el componente se llamaba aún `RegisterForm`) | `route.test.ts`: 2 fallan (`/register` y `/register/` daban `notFound`); el test del marcado no se carga: `Cannot find module './RegisterForm'` |
| Tests de ruta y marcado tras el código | `npx vitest run src/app/route.test.ts src/register/RegistrationForm.test.ts src/register/registerForm.test.ts` | 130 passed: 19 de `route.test.ts` (2 tests nuevos y 6 direcciones nuevas en la lista de `notFound`; los 11 anteriores no cambian), 30 del marcado y 81 de la lógica |
| Suite completa | `npx vitest run` | 26 ficheros, 1019 passed (900 antes de la tarea más 119 nuevos: 81 de la lógica, 30 del marcado y 8 de la ruta). El único test existente que cambia es `route.test.ts` |
| Análisis estático | `npx eslint src/pages/RegisterPage.tsx src/register src/app/AppShell.tsx src/main.tsx src/app/route.ts src/app/route.test.ts src/i18n/es.ts` | Sin incidencias (código de salida 0) |
| Tipos y empaquetado | `npm run build` (`tsc -b && vite build`) | Código de salida 0; solo el aviso del chunk de maplibre-gl, que ya existía |
| Caracteres invisibles | Detección por categoría Unicode (Cc, Cf, Cs, Mn, Mc, Me, Zl, Zp y Zs salvo el espacio) sobre los once ficheros de código y tests de la tarea, `plan.md` y `tasks.md` | 0 hallazgos. En `validation.md` salen 11 líneas con tabuladores, todas del bloque de código de Vite de la T6 (líneas 440 a 455), ya presentes en `HEAD`; ninguna de esta sección |

No se ha levantado, parado ni reiniciado Vite ni Docker, y no se ha tocado la BD de desarrollo.

### Lo observado
| # | Comprobación | Observado |
|---|---|---|
| 1 | Tipos que vitest y eslint no ven | `tsc` rechazó en la lógica `catalog.unknown` (`string \| undefined` con `noUncheckedIndexedAccess`) cuando vitest y eslint ya estaban en verde; se corrigió con un texto de reserva explícito y se repitieron las cuatro comprobaciones |
| 2 | Nombre del componente (desviación) | El plan y la propuesta llamaban `RegisterForm.tsx` al componente y `registerForm.ts` a la lógica: solo se diferencian en las mayúsculas y `tsc -b` falla con TS1149 (y en macOS y Windows serían el mismo fichero). El componente pasó a `RegistrationForm.tsx`; plan y tasks actualizados |
| 3 | Atributos en el renderizado de servidor | `renderToStaticMarkup` conserva el nombre de la propiedad (`noValidate`, `autoComplete`, `inputMode`, `readOnly`, `tabIndex`) y no el atributo en minúsculas. Los siete primeros fallos del test del marcado eran del propio test (buscaba minúsculas, y `aria-invalid` casaba también con la clase `aria-invalid:border-danger`); ahora busca atributos reales (`\saria-invalid=`) sin distinguir mayúsculas |
| 4 | Contraseña fuera del HTML | La contraseña no tiene propiedad en `RegistrationForm` ni `value` en el campo, en ningún estado (vacío, con errores, enviando, visible, visible y enviando). La página la lee del `ref` al enviar y la borra con `input.value = ""` tras un éxito o un error de la contraseña. El email sí es un campo controlado |
| 5 | `formStateForEmpty` (añadido) | No estaba en la lista del plan. Los campos vacíos se avisan con los mismos textos, resumen y foco que un rechazo del servidor, sin enviar nada. Tiene 3 tests propios |
| 6 | Qué no cubre vitest | El cableado de `RegisterPage` (guarda en `ref`, `readOnly` durante el envío, foco, `replace("/map")` desde el efecto) corre en React y vitest usa entorno `node`: los tests cubren la lógica pura y el marcado. Por ejemplo, quitar `if (!guard.tryStart()) return;` de la página no lo detecta ningún test automático; el doble clic y el doble Intro se comprueban en la T9, en el navegador |
| 7 | Contraste de `--color-danger: #b3261e` | Calculado con la fórmula de WCAG: 6,54:1 sobre blanco y 5,64:1 sobre `sky` (AA en ambos); sobre `lemon` daría 4,51:1, por eso el error de campo no se pinta dentro del aviso amarillo. Se mira en la T9 |
| 8 | Tres desviaciones más del plan | `aria-disabled` en vez de `disabled` en el envío, etiqueta fija en «Mostrar contraseña» y el `replace("/map")` solo en el efecto: ver «Desviaciones de la T8» en `plan.md` |

### Pruebas de mecanismo
La tarea es de interfaz, pero toca la privacidad de la contraseña y el doble envío, y se hacen dos. Cada una sobre una copia hecha junto al fichero (`<fichero>.orig`), restaurada con `cp` y borrada; sha256 idéntico antes y después y ninguna copia sin versionar. Ejecución: `npx vitest run src/register/registerForm.test.ts src/register/RegistrationForm.test.ts src/app/route.test.ts` (130 tests).

| # | Fichero | Mutación | Tests que fallan |
|---|---|---|---|
| 1 | `src/register/registerForm.ts` | Quitar `if (busy) return false;` de `tryStart` (permite un segundo envío con el primero en curso) | 2: «createSubmitGuard: un envío a la vez > el primer envío pasa y el segundo, con el primero en curso, no» y «terminar dos veces no deja pasar dos envíos». Los demás casos de la guarda pasan: no dependen de esa comprobación |
| 2 | `src/register/RegistrationForm.tsx` | Volver a hacer controlado el campo de contraseña (`value=""` y `onChange` en el `<input id="register-password">`) | 5: «la contraseña nunca llega al HTML > con el formulario vacío / con errores / enviando / visible / visible y enviando el campo no lleva value ni defaultValue». `tsc -b` no la detecta (código de salida 0): solo la ve el test del marcado |

sha256 antes, durante y después:

| Fichero | Antes | Durante | Después |
|---|---|---|---|
| `src/register/registerForm.ts` (mutación 1) | `f520b33a5dbeb214ce7f4caea878a32235ae4d499a65e18e31b5323305271589` | `5a7b83d255e408a1ef1e2ad4ce2050c45cd325612888e969999207d654432998` | `f520b33a5dbeb214ce7f4caea878a32235ae4d499a65e18e31b5323305271589` |
| `src/register/RegistrationForm.tsx` (mutación 2) | `b83f1470378258d2434070dc66aae06c850bc1c0feb70cb48f285240fed97940` | `a18d5c1e2097e098a8fdd72f9982ff45a531f4e3c6ebcfcb6877badf089bbb5c` | `b83f1470378258d2434070dc66aae06c850bc1c0feb70cb48f285240fed97940` |
