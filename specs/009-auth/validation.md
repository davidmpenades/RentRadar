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
| Tipos del cliente | `cd frontend && npm run api:gen`, `npm run api:check`, `npm run build` y `npx eslint src/api/schema.gen.ts` | En verde (código de salida 0) |
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
