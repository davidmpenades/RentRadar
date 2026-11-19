# Plan 009 — Registro, sesión y salida
Spec: specs/009-auth/spec.md (aprobada, alineada con el comportamiento verificado en la investigación de este plan)

## Resumen
- Backend:
  - `POST /api/v1/auth/register/`, `GET|HEAD /api/v1/auth/session/` y `POST /api/v1/auth/logout/`, en `apps/users`;
  - sesión de Django con CSRF de doble envío;
  - límite de registro de 10 por hora por IP (IPv6 por /64);
  - cuerpo acotado a 4096 bytes;
  - formato único de errores con `no-store`.
- Núcleo en `apps/core`: CSRF explícito para vistas anónimas (`csrf.py`), lectura acotada del cuerpo (`request_body.py`), códigos generales nuevos con estado por código (`api.py`) y el serializer de error común (`serializers.py`).
- Ajustes: `AuthenticationMiddleware`, validadores de contraseña en el orden de RF-2 y sesión de 14 días sin renovación. `DEFAULT_AUTHENTICATION_CLASSES` sigue vacío.
- Frontend:
  - cliente de sesión con reintento único ante `csrf_failed`, «quién soy» con 5 s y registro y salida con 10 s, todos con el mismo helper de tiempo máximo;
  - navegación interna con la History API;
  - barra superior con la marca (enlace al mapa), «Registrarse» y «Salir», y zona de contenido bajo ella;
  - página `/register`.
- Sin dependencias nuevas, sin modelos y sin migraciones. Cambio de contrato (aprobado por el usuario): se regeneran `backend/openapi.json` y `frontend/src/api/schema.gen.ts`.
- Cambio posterior a la implementación (RF-14, cookie de sesión mal formada): un `SessionStore` propio y `SESSION_ENGINE`, sin cambio de contrato; ver «Cambio: clave de sesión (RF-14)».

## Archivos y responsabilidades
| Archivo | Crea/Modifica | Responsabilidad | RF |
|---|---|---|---|
| backend/config/settings/base.py | M | (T1) `django.contrib.auth.middleware.AuthenticationMiddleware` justo después de `CsrfViewMiddleware`; `AUTH_PASSWORD_VALIDATORS` (MinimumLength con `min_length=10`, Common, Numeric, UserAttributeSimilarity con `user_attributes=("email",)`, en ese orden); `SESSION_COOKIE_AGE = 60 * 60 * 24 * 14`; `SESSION_SAVE_EVERY_REQUEST = False`; `SESSION_EXPIRE_AT_BROWSER_CLOSE = False` | RF-2, RF-4, RF-6, RNF Sesión |
| backend/config/tests/test_auth_settings.py | C | (T1) Posición del middleware (tras Session y CSRF; el de cookies sigue el primero); validadores, orden y opciones; `CSRF_COOKIE_NAME == "csrftoken"`; `CSRF_HEADER_NAME == "HTTP_X_CSRFTOKEN"` | RNF Sesión |
| backend/config/tests/test_http_hardening.py | M | (T1) La política de cookies por entorno gana la edad, `SAVE_EVERY_REQUEST` y `EXPIRE_AT_BROWSER_CLOSE` | RNF Sesión |
| backend/apps/core/api.py | M | (T1) Códigos generales `invalid_fields`, `invalid_request`, `payload_too_large` y `csrf_failed`; estado por código (`STATUS_BY_CODE`, atributo de instancia); `params` admite listas | RNF Errores |
| backend/apps/core/serializers.py | C | (T1) `ApiErrorSerializer` movido desde assets (el componente sigue llamándose `ApiError`) | RNF Contrato |
| backend/apps/assets/serializers.py, views.py | M | (T1) Importan `ApiErrorSerializer` de core | — |
| backend/apps/core/tests/test_api.py | M | (T1) Conjunto de códigos; estados 403, 413 y 400; `params` con listas | RNF Errores |
| backend/apps/assets/tests/test_public_list_session.py | C | (T1) Lista pública con la pila real y el middleware nuevo | RNF Lista pública |
| backend/apps/core/text.py, tests/test_text.py | M | (T2) `contains_lone_surrogate(text)` | RF-2 |
| backend/apps/users/services.py | M | (T2) `register_user`; `_registration_password_errors`; `_create_account` recibe el comprobador de contraseña; `_create_account` y `change_user_email` rechazan el email con sustituto suelto con `email_invalid` antes de `full_clean` y de cualquier consulta; códigos nuevos | RF-1, RF-2 |
| backend/apps/users/tests/test_registration_service.py | C | (T2) Códigos, orden, hash, contenido hostil, carrera | RF-1, RF-2 |
| backend/apps/users/tests/test_services.py, test_leaks.py | M | (T2) `PLAN_ERROR_CODES`, caso del sustituto en `create_user`, `create_superuser` y `change_user_email`, `register_user` en la parametrización de fugas | RF-2, RNF Privacidad |
| backend/apps/core/csrf.py | C | (T3) `enforce_csrf(http_request)` y `CsrfEnforcedMixin` | RF-7 |
| backend/apps/core/request_body.py | C | (T3) `read_json_object(http_request, *, max_bytes)` y `read_text_fields(data, names)` | RF-8 |
| backend/apps/core/tests/test_csrf.py, test_request_body.py, csrf_views.py, csrf_urls.py | C | (T3) Vistas de prueba y tests del mixin y del lector | RF-7, RF-8 |
| backend/apps/core/tests/test_api_import.py | M | (T3) `MODULES` gana los dos módulos nuevos | — |
| backend/conftest.py | M | (T3) Fixture `csrf_client` (`Client(enforce_csrf_checks=True)`) | RF-7 |
| backend/apps/users/throttling.py, tests/test_throttling.py | C | (T4) `ip_bucket(address)` puro y `RegistrationThrottle` | RF-3 |
| backend/apps/users/serializers.py | C | (T5a) `SessionUserSerializer`, `SessionSerializer`, `RegistrationRequestSerializer` (solo documenta) y `RegistrationErrorSerializer` | RF-1, RF-6, RNF |
| backend/apps/users/views.py | C | (T5a) `RegisterView` y `public_field_errors(message_dict)`; (T5b) `CurrentSessionView` y `LogoutView` | RF-1…RF-8 |
| backend/apps/users/urls.py; backend/config/urls.py | C; M | (T5a) `auth/register/` y la inclusión bajo `api/v1/`; (T5b) `auth/session/` y `auth/logout/` | RF-1, RF-5, RF-6 |
| backend/apps/users/tests/test_register_api.py, test_session_api.py, test_logout_api.py, test_auth_contract.py | C | (T5a) `test_register_api.py` y el registro en `test_auth_contract.py`; (T5b) `test_session_api.py`, `test_logout_api.py` y el resto de `test_auth_contract.py`. Contrato HTTP, sesión, cookies, cabeceras y OpenAPI | RF-1…RF-8 |
| backend/apps/core/tests/test_csrf_guard.py | C | (T5a) Toda vista del URLconf que atiende métodos no seguros hereda el mixin; en la T5b cubre la salida sin tocarla | RF-7 |
| backend/openapi.json; frontend/src/api/schema.gen.ts | M | (T5a y T5b) Contrato regenerado | RNF Contrato |
| frontend/src/api/timeout.ts, timeout.test.ts | C | (T6) `runWithTimeout`; `publicAssets.ts` y `loadStyle.ts` pasan a usarlo | RF-9, RF-11, RF-12 |
| frontend/src/api/publicAssets.ts, frontend/src/map/loadStyle.ts | M | (T6) Usan `runWithTimeout`; su comportamiento y sus tests no cambian | — |
| frontend/src/api/session.ts, session.test.ts | C | (T6) Cliente de sesión: `readCsrfToken`, `createSessionClient` (`whoAmI` con 5 s; `register` y `logout` con 10 s), esquemas Zod y reintento único | RF-6, RF-7, RF-9, RF-10, RF-11, RF-12 |
| frontend/src/i18n/format.ts, format.test.ts | M | (T6) `waitMinutes(seconds)` y `throttledMessage(seconds)` | RF-3, RF-11 |
| frontend/vite.config.ts | M | (T6) Proxy `/api` como objeto con `changeOrigin: false` | RNF Mismo origen |
| frontend/src/app/navigation.ts, navigation.test.ts | C | (T7) `createNavigator` y `isPlainLeftClick` | RF-9, RF-10, RF-13 |
| frontend/src/session/sessionState.ts, sessionState.test.ts; SessionProvider.tsx | C | (T7) Estado `unknown \| anonymous \| authenticated`, acciones de la barra, resultado de la salida (anuncio, foco y aviso de fallo); contexto y «quién soy» al montar | RF-9, RF-12 |
| frontend/src/app/AppShell.tsx, TopBar.tsx, LogoutNotice.tsx, TopBar.test.ts | C | (T7) Columna con barra y zona de contenido; marca como enlace a `/map`; aviso visible de fallo de «Salir» con «Reintentar»; región de estado de la sesión | RF-9, RF-12 |
| frontend/src/main.tsx; pages/MapPage.tsx; app/NotFoundPage.tsx | M | (T7) Montan `AppShell`; las páginas ocupan la zona (`h-full` / `min-h-full`) en vez de `h-dvh` | RF-9, 006 RF-8/13/14 |
| frontend/src/i18n/es.ts | M | (T7, T8) Textos de la barra, de la salida, del formulario, del tiempo vencido y de los códigos | RF-9…RF-13 |
| frontend/src/app/route.ts, route.test.ts | M | (T8) `register` y `redirectToRegister` | RF-13 |
| frontend/src/main.tsx; frontend/src/app/AppShell.tsx | M | (T8) `main.tsx` normaliza `/register/` a `/register` con `replaceState`; `AppShell` pinta `RegisterPage` en `register` y `redirectToRegister` | RF-13 |
| frontend/src/register/registerForm.ts, registerForm.test.ts | C | (T8) Lógica del formulario: constantes de longitud, mensajes, foco, estado tras el resultado, `formStateForEmpty`, guarda de envío y `settleRegistration` | RF-10, RF-11, RF-13 |
| frontend/src/register/RegistrationForm.tsx, RegistrationForm.test.ts; pages/RegisterPage.tsx | C | (T8) `RegistrationForm`, solo marcado (probado con `react-dom/server`); `RegisterPage`, con el estado, la sesión, la guarda y el foco | RF-10, RF-11, RF-13 |
| frontend/src/styles/index.css | M | (T8) Token `--color-danger` para los errores del formulario | RF-11 |
| specs/009-auth/validation.md | C (T1), M | Evidencia de las mutaciones de cada tarea y validación final; incluye la nota de la desviación del proxy de Vite (T6, T9) | Todos |
| docs/architecture.md | M | (T9) Capa de autenticación, CSRF explícito, cuerpo acotado, límite /64, estructura del frontend | — |

## Modelo de datos y migraciones
- **No hay modelos ni migraciones nuevos.**
  - La sesión usa el motor de BD de `django.contrib.sessions` (ya instalado). Desde el cambio de RF-14 pasa por un `SessionStore` propio que solo cambia la validación de la clave, con la misma tabla y el mismo modelo (ver «Cambio: clave de sesión (RF-14)»).
  - El usuario es el de la 004, sin cambios.
  - Las cuentas se crean por el servicio.
- `config/tests/test_migrations.py` (`makemigrations --check`, en la BD de test) sigue en verde en T1, T5a y T5b.
- No se ejecuta `migrate`.

## Contrato de API
Rutas versionadas, con barra final y JSON. Ninguna acepta un identificador de usuario ni los campos `is_staff`, `is_superuser` o `is_active`. Sin cabeceras `Access-Control-*`. Aprobado por el usuario (cambio de contrato de la API).

### `POST /api/v1/auth/register/` (operationId `registerAccount`, tag `auth`)
- **Petición**
  - Cabeceras: `Content-Type: application/json`, `X-CSRFToken` (igual a la cookie `csrftoken`) y las cookies del mismo origen.
  - Cuerpo: `{"email": string, "password": string}`, de 4096 bytes como máximo. Los campos desconocidos se ignoran.
- **Orden**:
  1. límite: 10 por hora por IP, o por /64 en IPv6;
  2. método: solo POST; cualquier otro, también HEAD y OPTIONS, da 405 con `Allow: POST`;
  3. CSRF;
  4. tamaño y forma del cuerpo;
  5. validación;
  6. creación y sesión, dentro de `transaction.atomic()`.
- **201**
  - Cuerpo: `{"user": {"email": "<email normalizado>"}}`.
  - Cabeceras: `Cache-Control: no-store`, `Vary: Cookie`.
  - `Set-Cookie: sessionid` nueva (HttpOnly, SameSite=Lax, Max-Age=1209600, Path=/; Secure en producción) y `csrftoken` nueva.
- **Errores**: ver la tabla. Todos llevan `no-store` y nunca el valor recibido.

### `GET|HEAD /api/v1/auth/session/` («quién soy», operationId `getCurrentSession`)
- Autenticación por la sesión de la propia petición. Sin límite. Sin CSRF, porque solo admite métodos seguros.
- **200**
  - Cuerpo: `{"user": {"email": "..."}}` con una sesión válida (existe, no ha caducado y su cuenta está activa) o `{"user": null}` en cualquier otro caso.
  - Cabeceras: `Cache-Control: no-store` y `Vary: Cookie` (explícito).
  - Cookies: `Set-Cookie: csrftoken` siempre (`get_token`). `sessionid` se borra (`Max-Age=0`) cuando viene en la petición y la sesión queda vacía: caducada, mal formada, con una clave sin fila o con un hash obsoleto (lo hace `SessionMiddleware`). Con una sesión válida o de una cuenta desactivada no lleva `Set-Cookie` de sesión.
- **405** con `Allow: GET, HEAD` para cualquier otro método.

### `POST /api/v1/auth/logout/` (operationId `logout`)
- **Orden**: método (405, `Allow: POST`) → CSRF → cierre. Sin límite.
- **204** sin cuerpo y con `no-store`.
  - `flush()` borra la fila de la sesión si existe, también si está caducada.
  - `Set-Cookie: sessionid=""; Max-Age=0` siempre, con `path`, `domain` y `samesite` de los ajustes.
  - `csrftoken` no se toca.

### Permisos (constitución, punto 5)
| Operación | Anónimo | Usuario con sesión | Propietario | Staff y superusuario |
|---|---|---|---|---|
| POST register | 201, o error | 201: su sesión se sustituye (RF-4) | No hay recursos por objeto | Como el usuario |
| GET/HEAD session | 200 `{"user": null}` | 200 con su propio email | — | Como el usuario |
| POST logout | 204 sin cambios (con CSRF) | 204: cierra solo la sesión de su cookie | — | Como el usuario |
| Otros métodos | 405 (429 si el límite de registro está superado) | ídem | ídem | ídem |

No hay 404 ni 403 por objeto: no existen recursos por identificador.

### Errores
Formato: `{"code": "<general>", "params"?: {...}, "retry_after"?: <entero ≥ 1>}`. Los produce `api_exception_handler`, que pone `no-store`.
| Estado | `code` | Extra | Cuándo |
|---|---|---|---|
| 400 | `invalid_request` | — | Registro: `Content-Type` distinto de `application/json`, JSON inválido (también UTF-8 inválido, BOM, `NaN` o `Infinity`), `RecursionError` al analizar, raíz que no es un objeto, `email` o `password` con un tipo que no es texto (número, booleano, lista u objeto) |
| 400 | `invalid_fields` | `params`: `{"email"?: [códigos], "password"?: [códigos], "non_field"?: [códigos]}`, en ese orden | RF-2 |
| 403 | `csrf_failed` | — | Registro o salida sin token válido: sin cabecera, vacía, sin cookie, cookie mal formada, cabecera distinta u Origin ajeno |
| 405 | `method_not_allowed` | `Allow` | Método no admitido |
| 413 | `payload_too_large` | — | `Content-Length` declarado > 4096, cabecera `Transfer-Encoding` presente o más de 4096 bytes leídos |
| 429 | `throttled` | `retry_after` y `Retry-After` | Registro: más de 10 por hora desde la IP o el /64 |

- Siguen los de la 006: `invalid_parameters`, `zone_inverted`, `zone_too_large`, `not_found`, `forbidden` y `bad_request`. `csrf_failed` nunca se confunde con `forbidden`.
- Códigos de campo, en el orden de las listas:
  - `email`: `email_empty`, `email_invalid`, `email_control_char`, `email_too_long`, `email_taken`;
  - `password`: `password_required` | `password_invalid` (va solo) | `password_too_long`, `password_too_short`, `password_too_common`, `password_entirely_numeric`, `password_too_similar`;
  - `non_field`: `constraint_violated` y `validation_failed`. Hoy no se alcanzan con ninguna entrada; existen para no devolver un 500 si aparece una restricción nueva. El cliente los muestra como error general.
- Fuera de la capa de DRF, sin formato ni `no-store` hasta la 011: los 5xx de Django y las redirecciones de `APPEND_SLASH`. El cliente usa siempre la barra final.

### Descripción OpenAPI
- `extend_schema` en cada vista, con `request=` y `responses=`:
  - registro: 201 `Session`, 400 `RegistrationError`, y 403, 405, 413 y 429 `ApiError`;
  - «quién soy»: 200 `Session` y 405 `ApiError`;
  - salida: 204 sin cuerpo, y 403 y 405 `ApiError`.
- `X-CSRFToken` como `OpenApiParameter` de cabecera, obligatorio en el registro y en la salida. `Set-Cookie` como cabecera de respuesta documentada en 201, 200 y 204.
- Componentes nuevos: `Session`, `SessionUser`, `RegistrationRequest` (por `COMPONENT_SPLIT_REQUEST`) y `RegistrationError`. Esquema de seguridad `cookieAuth` en «quién soy».
- Se genera con `docker compose exec -u "$(id -u)" backend python manage.py spectacular --format openapi-json --file openapi.json --validate --fail-on-warn --lang en` y `cd frontend && npm run api:gen`. Los controles de desfase de la CI no cambian.

## Lógica
**Backend**
- `contains_lone_surrogate(text) -> bool`: categoría `Cs`. Es la segunda repetición; la privada de `assets/rules.py` no se toca.
- `register_user(*, email, password) -> User` llama a `_create_account(email, password, is_admin=False, password_errors=_registration_password_errors)`. `create_user` y `create_superuser` siguen con el comprobador actual, que devuelve un solo código.
- `_create_account` y `change_user_email`:
  - si el email es texto con un sustituto suelto, dan `email` → `[email_invalid]`, no llaman a `full_clean` (ni, en el cambio, a ninguna consulta) y la similitud usa `user=None`;
  - si es texto o `None`, siguen como hoy;
  - con otro tipo, `email_invalid`;
  - después, en `_create_account`, `password_errors(password, user=...)`;
  - sin errores, `set_password` y `run_guarded`, que en una carrera devuelve `email_taken`;
  - el error se lanza fuera de cualquier `except`.
- `_registration_password_errors(password, *, user) -> list[str]`:
  - `None` o `""` → `[password_required]`;
  - no es texto, o contiene `\x00` o un sustituto suelto → `[password_invalid]`, sin ejecutar los validadores;
  - si no: `password_too_long` si pasa de 128, más los `error.code` de `validate_password(password, user=user)` en el orden de `AUTH_PASSWORD_VALIDATORS`. Solo se usa el código, nunca `messages` ni `params`, que llevan datos.
  - Nunca calcula un hash. No recorta ni normaliza.
- `enforce_csrf(http_request)`:
  - `http_request.POST = QueryDict()`;
  - `check = CSRFCheck(lambda request: None)`; `check.process_request(http_request)`; `reason = check.process_view(http_request, None, (), {})`;
  - si hay `reason`, `raise ApiError("csrf_failed")` sin el motivo.
- `CsrfEnforcedMixin.initial(request, *args, **kwargs)`:
  - `super().initial(...)`;
  - después, si `request.method` no está en `SAFE_METHODS`, está en `http_method_names` y la vista tiene su manejador, `enforce_csrf(request._request)`.
- `read_json_object(http_request, *, max_bytes) -> dict`:
  1. `HTTP_TRANSFER_ENCODING` presente → `payload_too_large`;
  2. `CONTENT_LENGTH` declarado > `max_bytes` → `payload_too_large` sin leer (uno no numérico cuenta como 0, como en Django);
  3. `http_request.content_type != "application/json"` → `invalid_request`;
  4. `raw = http_request.read(max_bytes + 1)`; si `len(raw) > max_bytes` → `payload_too_large`;
  5. vacío → `{}`;
  6. `JSONParser().parse(BytesIO(raw), "application/json", {})` capturando `ParseError` y `RecursionError` → `invalid_request`;
  7. raíz que no es `dict` → `invalid_request`.
  - Nunca usa `request.data` ni `request.body`.
  - Sin límite de profundidad propio: un objeto anidado en una clave desconocida se acepta. La captura de `RecursionError` es defensiva (en este Python, 2048 listas anidadas caben en 4 KiB y se analizan sin error): su test la simula.
- `read_text_fields(data, names) -> dict[str, str | None]`: cada nombre ausente da `None`; `str` o `None` pasan; otro tipo → `invalid_request`.
- `ip_bucket(address) -> str`:
  - IPv4 → tal cual;
  - IPv6 con IPv4 mapeada → la IPv4;
  - otra IPv6 (sin zona: `fe80::1%eth0` → `fe80::/64`) → `str(ip_network((addr, 64), strict=False))`;
  - vacía, `None` o inválida → el cubo fijo `unknown`, sin lanzar; el texto recibido no se usa como clave.
- `RegistrationThrottle(SimpleRateThrottle)`:
  - `rate = "10/hour"` en la clase y `scope = "register"`;
  - `get_cache_key` = `throttle_register_<ip_bucket(get_ident)>`; con `NUM_PROXIES = 0` es `REMOTE_ADDR`;
  - solo anota las peticiones permitidas;
  - limita también a quien tiene sesión;
  - `timer` sustituible en los tests.
- `RegisterView(CsrfEnforcedMixin, APIView)`:
  - `authentication_classes = []`, `permission_classes = [AllowAny]`, `throttle_classes = [RegistrationThrottle]`, `http_method_names = ["post"]`;
  - `post`: `read_json_object(max_bytes=4096)` → `read_text_fields(("email", "password"))`;
  - después, `with transaction.atomic(): user = register_user(...); session.flush(); login(http_request, user)`;
  - si hay `DomainValidationError`, se captura fuera de `atomic` y se lanza `ApiError("invalid_fields", public_field_errors(...))` fuera del `except`;
  - 201 con `SessionSerializer` y `no-store`.
  - Un registro rechazado no accede a la sesión.
- `public_field_errors(message_dict)`: claves en orden `email`, `password` y `non_field` (renombra `__all__`); conserva el orden de los códigos.
- `CurrentSessionView(APIView)`:
  - `authentication_classes = [SessionAuthentication]`, `AllowAny`, `http_method_names = ["get", "head"]`;
  - `get_token(request._request)`; `user` si `is_authenticated`, si no `None`;
  - `no-store` y `patch_vary_headers(("Cookie",))`;
  - `initial` rechaza con 405 un método no admitido antes de `super().initial()`: `SessionAuthentication` exige CSRF a quien tiene sesión, y sin esto un POST sin token daría 403 `forbidden`.
- `LogoutView(CsrfEnforcedMixin, APIView)`: `authentication_classes = []`, `AllowAny`, `["post"]`; `request._request.session.flush()`; 204; `delete_cookie(SESSION_COOKIE_NAME, path=..., domain=..., samesite=...)`; `no-store`. No llama a `django.contrib.auth.logout()`, así que no emite `user_logged_out`: la 015 debe tenerlo en cuenta si algo escucha esa señal.
- Ninguna de las tres marca su respuesta como sin cookies.
- Serializers en lista blanca, nunca `ModelSerializer`:
  - `SessionUserSerializer`: solo `email`;
  - `SessionSerializer`: `user`, que admite nulo;
  - `RegistrationErrorSerializer`: `code`, más `params` como `DictField(child=ListField(child=CharField()), required=False)`, sin `read_only`, por la regla de drf-spectacular.

**Frontend** (funciones puras con sus dependencias inyectadas; vitest en node)
- `runWithTimeout({signal, timeoutMs, setTimer, clearTimer, onTimeout}, task)`:
  - enlaza la señal externa y el temporizador en un `AbortController` propio;
  - si vence, aborta y lanza `onTimeout()`;
  - limpia el temporizador y el listener en `finally`.
  - `publicAssets.ts` (`RequestTimeoutError`, 10 s) y `loadStyle.ts` (`StyleLoadError`, 10 s) pasan a usarlo sin cambiar su comportamiento.
- `readCsrfToken(cookies: string) -> string | null`: el primer `csrftoken=` que cumpla `^[A-Za-z0-9]{32}([A-Za-z0-9]{32})?$`.
- `createSessionClient({fetch, readCookies, setTimer, clearTimer, whoAmITimeoutMs: 5000, writeTimeoutMs: 10000})`:
  - Peticiones:
    - todas con `credentials: "same-origin"`, con un tipo propio distinto del `FetchInit` público, que sigue en `"omit"`;
    - todas pasan por `runWithTimeout`: «quién soy» con 5 s; registro y salida con 10 s;
    - URLs con barra final;
    - el token se lee de la cookie en **cada** envío, nunca se guarda y solo va a `X-CSRFToken` si tiene la forma correcta.
  - `whoAmI(signal) -> "authenticated" | "anonymous"`:
    - 200, `Content-Type` JSON y `sessionSchema` válido → según `user`;
    - cualquier fallo, tiempo agotado o forma inválida → `"anonymous"`, sin escribir en la consola.
  - `register({email, password})`:
    - un 403 con `csrf_failed` → `whoAmI()` y **un** reintento;
    - 201 válido → `registered`;
    - 201 con forma inválida, o tiempo vencido → `whoAmI()`: con sesión `registered`, sin ella `failed("invalid")` o `failed("timeout")`;
    - 400 `invalid_fields` → `fieldErrors {email, password, other}`;
    - 429 → `throttled(retryAfter)`;
    - el resto → `failed(csrf | request | network | server | invalid | timeout)`.
  - `logout()`: el mismo reintento; 204 → `loggedOut`; si no, o si vence → `failed`.
  - Esquemas `z.strictObject`:
    - `sessionSchema`: `{user: null | {email: string no vacío}}`;
    - `apiErrorSchema`: `{code, params?: record<string, string | string[]>, retry_after?: int ≥ 1}`;
    - aserción en compilación frente a `components["schemas"]["Session"]`.
- `waitMinutes(seconds) = max(1, ceil(seconds / 60))`. `throttledMessage` da «Demasiados intentos. Inténtalo de nuevo en N minutos.», con «1 minuto» en singular.
- `createNavigator({history, getPathname, addPopStateListener})` → `{getPath, navigate(path), replace(path), subscribe}`:
  - `navigate` hace `pushState` y notifica, y no hace nada si la ruta es la actual;
  - `replace` hace `replaceState` y notifica;
  - un `popstate` notifica.
  - `isPlainLeftClick(event)`: botón 0, sin modificadores y sin `defaultPrevented`. Así los enlaces siguen abriéndose en otra pestaña.
- `resolveRoute`:
  - `/` y `/map/` → `redirectToMap`; `/map` → `map`;
  - `/register/` → `redirectToRegister`; `/register` → `register`;
  - cualquier otra dirección, incluidas `/register//` y `/REGISTER`, → `notFound`.
- `sessionState.ts`:
  - `SessionStatus = "unknown" | "anonymous" | "authenticated"`, sin email;
  - `topBarAction(status)` → `none | register | logout`;
  - `logoutResult(outcome)` → `{status, announcement, focus: "register" | "logout", notice: null | "logout_failed"}`. El aviso se mantiene hasta un nuevo intento o hasta que el estado cambie.
- `registerForm.ts`:
  - `emptyFieldErrors({email, password})`, con los mismos códigos que el servidor;
  - `fieldMessages(codes)`, desde el catálogo;
  - `firstFocusTarget(errors, hasGeneral)`: email → contraseña → región de estado;
  - `formStateAfter(outcome)`: conserva siempre el email; borra la contraseña solo si el resultado es `fieldErrors` con al menos un error de `password`, y la conserva en cualquier otro caso (`fieldErrors` solo del email o de `other`, `throttled` y cada `failed`); elige el mensaje general (también para `failed("timeout")`) y vuelve a habilitar el envío;
  - `formStateForEmpty(emptyFieldErrors(...))`: el mismo estado que `formStateAfter` para los campos vacíos, con los mismos textos, resumen y foco que un rechazo del servidor, pero sin enviar nada y sin borrar la contraseña (ya está vacía);
  - `PASSWORD_MIN_LENGTH = 10` y `PASSWORD_MAX_LENGTH = 128`: copia de `MinimumLengthValidator` en `backend/config/settings/base.py` y de `PASSWORD_MAX_LENGTH` en `backend/apps/users/services.py`, con su origen anotado en un comentario. Solo alimentan la pista y los mensajes de longitud, nunca una validación del cliente; el 10 lo fija en el backend `config/tests/test_auth_settings.py`, y la T9 comprueba en el navegador que una contraseña de 9 caracteres da el mensaje con «10»;
  - `settleRegistration({register, credentials, logError})`: como `settleLogout`, convierte un rechazo inesperado en `failed("unexpected")`, lo registra sin las credenciales y nunca lanza;
  - `shouldLeaveRegister(status)`: `authenticated` → sí;
  - `createSubmitGuard()`: `tryStart()` solo da paso si no hay un envío en curso y `finish()` lo libera; un envío a la vez.

## Interfaz
- **AppShell**: `div.flex.h-dvh.flex-col` con la barra (`header`), el aviso de salida cuando existe y la zona de contenido (`div.relative.min-h-0.flex-1`). Cada página pone su `<main>`.
  - Al cambiar de página, el foco va a la zona (`tabIndex=-1`), para no perderlo en un elemento que desaparece.
  - Una región `role="status"` (polite), solo para lectores de pantalla, anuncia «Has salido» y «Cuenta creada.». «Creando la cuenta…» y los errores los anuncia la región de estado del formulario.
- **Barra superior**: 56 px (`h-14`), móvil primero.
  - A la izquierda, la marca «RentRadar» como **enlace a `/map`** (`<a href="/map">` con `navigate` si es un clic simple), de al menos 44 px de alto.
  - A la derecha, la acción:
    - sin acción mientras el estado es `unknown`;
    - enlace «Registrarse» (`<a href="/register">` con `navigate` si es un clic simple);
    - o botón «Salir».
  - Controles `min-h-11 min-w-11`, foco visible como en la 006 (3 px tinta, 2 px de separación). Nunca muestra el email.
  - «Salir» en curso usa `aria-disabled` y no `disabled`, para conservar el foco.
  - Si la salida funciona, el foco va a «Registrarse»; si falla o vence a los 10 s, se queda en «Salir».
- **Aviso de fallo de «Salir»** (`LogoutNotice`): franja bajo la barra, `role="status"`, con «No se ha podido salir. Inténtalo de nuevo.» y un botón «Reintentar» de 44 px que repite la salida. Visible a 375 y a 1280 px. Mientras existe, la zona de contenido cede su alto (`flex-1 min-h-0`).
- **Página del mapa y «Página no encontrada»**:
  - `MapPage` pasa de `h-dvh` a `h-full`, dentro de la zona;
  - `NotFoundPage` pasa de `min-h-dvh` a `min-h-full`, con desplazamiento propio si no cabe;
  - el panel, la atribución y el error del estilo no cambian, solo su contenedor. Sin scroll de página.
- **`/register`**:
  - `<main>` con `h1` «Crear una cuenta» y un formulario de ancho máximo `max-w-sm` con `noValidate` y `method="post"`; el manejador de envío empieza con `preventDefault()`, para que un fallo previo no mande la contraseña por la URL en un envío nativo.
  - Email: `type="email"`, `autoComplete="email"`, `inputMode="email"`, `autoCapitalize="none"`, `spellCheck={false}`; campo controlado.
  - Contraseña: `autoComplete="new-password"` y campo **no controlado**: se lee de un `ref` al enviar y se borra con `input.value = ""`, porque React copia el valor de un campo controlado al atributo `value` del DOM, también en `type="password"`. Pista «Al menos 10 caracteres.» (con `PASSWORD_MIN_LENGTH`) enlazada con `aria-describedby`.
  - Botón «Mostrar contraseña» (`type="button"`) de 44 px: etiqueta fija, con `aria-pressed` y `aria-controls`; no cambia a «Ocultar contraseña», porque un lector leería «Ocultar contraseña, pulsado».
  - Envío «Crear cuenta» de 44 px; Intro en el último campo envía.
  - Se pinta sin esperar a «quién soy». Si el estado pasa a `authenticated`, `replace("/map")`.
  - Errores:
    - por campo, con `aria-invalid` y `aria-describedby`, uno o varios mensajes;
    - el general, en la región de estado del formulario (`role="status"`, `tabIndex=-1`); con errores en campos, la región lleva el resumen «Revisa los campos marcados.».
  - Al enviar:
    - se anuncia «Creando la cuenta…» en la región de estado del formulario;
    - el envío queda con `aria-disabled` (no `disabled`, que quitaría el foco y no frenaría el Intro) y los dos campos en `readOnly`, para que el email no cambie mientras dura la operación (unos 30 s en el peor caso: dos intentos y dos «quién soy»);
    - un doble clic o un doble Intro no envían dos veces: la guarda (`createSubmitGuard`) vive en un `useRef` y se libera en un `finally`;
    - si se rechaza, falla o vence a los 10 s: el email se conserva; la contraseña se borra solo si el resultado trae un error de la contraseña; el envío vuelve a habilitarse para reintentar y el foco va al primer campo con error o a la región.
  - Si el estado es `authenticated`, la página no pinta el formulario (devuelve `null`) mientras el efecto hace el `replace`.
  - Al registrarse: el manejador solo llama a `markRegistered` (estado `authenticated` y anuncio «Cuenta creada.»). El único `replace("/map")` lo hace el efecto de `shouldLeaveRegister`, sin entrada nueva en el historial.
- **Mensajes del catálogo (`es.ts`)**:
  - `email_taken`: «Ya existe una cuenta con este email.» (fijado por la spec);
  - `throttled`: el texto fijado por la spec;
  - `email_empty` «Escribe tu email.», `email_invalid` «Escribe un email válido.», `email_control_char` «El email tiene caracteres no permitidos.», `email_too_long` «El email es demasiado largo.»;
  - `password_required` «Escribe una contraseña.», `password_invalid` «La contraseña tiene caracteres no permitidos.», `password_too_long` «La contraseña no puede tener más de 128 caracteres.», `password_too_short` «La contraseña debe tener al menos 10 caracteres.», `password_too_common` «Esa contraseña es demasiado común.», `password_entirely_numeric` «La contraseña no puede tener solo números.», `password_too_similar` «La contraseña se parece demasiado al email.»;
  - generales: tiempo vencido, «La petición ha tardado demasiado. Inténtalo de nuevo.»; CSRF tras el reintento, «No se ha podido enviar el formulario. Recarga la página e inténtalo de nuevo.»; red, servidor e inesperado, como la 006 (con claves propias en `es.register`);
  - resumen con errores en campos, «Revisa los campos marcados.»; `fieldErrors` solo de `other` (`constraint_violated`, `validation_failed` o desconocido), «No se ha podido crear la cuenta. Inténtalo de nuevo.»; un código desconocido en un campo, «Revisa el email.» o «Revisa la contraseña.»;
  - `fieldMessages` no repite un mismo texto en un campo, porque el cliente no agrupa los códigos desconocidos repetidos.
- **Movimiento reducido**: sin transiciones. Contraste AA con los tokens de la 006 y `--color-danger: #b3261e` para los errores (6,54:1 sobre blanco y 5,64:1 sobre `sky`, calculados con la fórmula de contraste de WCAG; sobre `lemon` daría 4,51:1, así que no se usa dentro del aviso amarillo; se mira también en la T9).

## Decisiones
| Decisión | Opciones | Elegida | Qué evita | Coste |
|---|---|---|---|---|
| D1 CSRF anónimo | A) mixin en `initial()` con `CSRFCheck` sobre el `HttpRequest` con `POST` vacío; B) `csrf_protect`; C) clase de autenticación que llama a `enforce_csrf`; D) `CSRFCheck` con el `Request` de DRF | A | B: 403 en HTML sin `no-store` y antes del límite. C: corre antes del límite y da `forbidden`. D: 415 antes de decidir, y lee el cuerpo con formularios | Toca `request._request.POST`; la guarda del URLconf obliga a heredar el mixin a toda vista con un método no seguro, también a las vistas de Django, y marca como no protegida toda vista función, cuyos métodos no se pueden inspeccionar, y toda ViewSet de DRF, que no expone `view_class`, aunque herede el mixin: si se monta el admin o se añade una ViewSet, la guarda fallará y habrá que decidir |
| D2 Autenticación | A) middleware tras CSRF, defaults `[]` y `SessionAuthentication` de serie solo en «quién soy»; B) `SessionAuthentication` por defecto; C) leer la sesión a mano sin middleware | A | B: una vista nueva leería la sesión sin declararlo y cambia `test_api_settings`. C: duplica Django | Cada vista futura declara su autenticación |
| D3 Sesión al registrarse | A) `atomic{register_user → flush() → login()}`; B) solo `login()`; C) `cycle_key()` y `login()` | A | B conserva la clave con la misma cuenta y los datos con la anónima; C conserva los datos | Una fila de sesión más por registro |
| D4 Salida | A) `flush()` y `delete_cookie` siempre; B) `django.contrib.auth.logout()`; C) `flush()` sin `delete_cookie` | A | B no borra la fila de una sesión caducada y evalúa `request.user`; C solo borra la cookie si viajó en la petición | Duplica los atributos de la cookie de los ajustes |
| D5 Cuerpo | A) lectura acotada propia en core; B) `DATA_UPLOAD_MAX_MEMORY_SIZE=4096` global; C) parser de DRF con límite | A | B rompe la 010 y da `RequestDataTooBig` en HTML; C sigue leyendo `request.body` | No se puede usar `request.data` en esas vistas |
| D6 Límite | A) `SimpleRateThrottle` con clave /64 y `rate` en la clase; B) `AnonRateThrottle`; C) contador propio | A | B no limita a quien tiene sesión, evalúa `request.user` y usa la IPv6 completa; C reimplementa la ventana | Sin atomicidad y por proceso (riesgo aceptado) |
| D7 Errores | A) `invalid_fields` con `params` de listas, estado por código, `ApiErrorSerializer` a core, `RegistrationError` aparte y `__all__` → `non_field`; B) reutilizar `invalid_parameters` o `validation_failed`; C) el formato de DRF | A | B pierde la lista y choca con un código de campo; C lleva mensajes con datos | Un serializer más; `assets` cambia un import |
| D8 Éxito | A) `{"user": {...} \| null}` con 201, 200 y 204; B) objetos distintos por operación; C) 401 sin sesión | A | C deja errores en la consola en cada visita | Un nivel de anidación |
| D9 Rutas | A) `/api/v1/auth/{register,session,logout}/`; B) `/users/`, `/me/` y `DELETE /session/`; C) sin barra final | A | B choca con «salida solo POST»; C, con `APPEND_SLASH` un POST redirigido pierde el cuerpo | Ruta de la entrada reservada para la 015 |
| D10 Proxy de Vite | A) objeto con `changeOrigin: false`; B) `CSRF_TRUSTED_ORIGINS` en `development.py` | A | B añade un origen de confianza que oculta errores de configuración y difiere de producción | Una línea en `vite.config.ts`. Corrige la decisión de la T7 de la 006 («sin `changeOrigin`»), que la forma abreviada del proxy activaba sin que se viera |
| D11 Navegación | A) navegador propio con `pushState`/`replaceState` y `popstate`; B) recarga completa; C) react-router | A | B recarga el estilo y el mapa en cada cambio; C es una dependencia | Hay que notificar a mano, porque `pushState` no emite `popstate` |
| D12 Tiempo máximo | A) extraer `runWithTimeout`; B) tercera copia | A | B incumple la regla de la tercera repetición | Toca dos módulos de la 006; sus tests no cambian |
| D13 Estructura del frontend | A) lógica en `.ts` puro y `AppShell`/`TopBar`/`SessionProvider`/`RegisterPage` finos; B) lógica en componentes; C) jsdom | A | B queda sin vitest; C es una dependencia | Más ficheros pequeños |
| D14 Orden de los códigos de contraseña | A) required → invalid (va solo) → too_long → validadores; B) invalid junto a los demás | A | B pasa a los validadores texto no válido | Ya está en la spec (RF-2) |
| D15 Email con sustituto | A) `email_invalid` en `_create_account` y `change_user_email`; B) solo en el registro; C) código nuevo | A | Un 500 en `createsuperuser`, `create_user` y el cambio de email; C cambia la 004 | Cambia el resultado de esas vías con esa entrada (antes, un error del servidor). Ya está en la 004 (RF-4) |
| D16 Barra y zona | A) columna flex `h-dvh`, barra de 56 px y zona `flex-1 min-h-0`; B) barra fija y relleno superior | A | B: el mapa calcula mal su zona visible | Dos clases por página |
| D17 Estado de sesión en el cliente | A) sin email; B) con el email sin mostrarlo | A | Que un cambio futuro lo pinte | Si se necesita, otra consulta |
| D18 Tiempo máximo de registro y salida | A) mismo `runWithTimeout`, 10 s, error general y reintento; B) sin tiempo máximo; C) un helper distinto | A | B deja el envío colgado hasta que el navegador corte; C duplica | Un reintento tras un registro vencido puede topar con `email_taken` si el servidor lo completó: antes de dar el error, el cliente pregunta «quién soy» |
| D19 Marca de la barra | A) enlace a `/map`; B) solo texto | A | B: sin camino de vuelta al mapa desde `/register` salvo «Atrás» | Un enlace más en la barra, con navegación interna |
| D20 Campo de contraseña | A) no controlado, leído de un `ref` y borrado con `input.value = ""`; B) controlado con estado de React | A | B: React copia el valor al atributo `value` del DOM (`react-dom-client.development.js`, `updateInput` y `setDefaultValue`), también en `type="password"`, y cada tecla queda en el HTML | Hay que borrar el campo a mano y no se puede pintar su valor |
| D21 Contraseña tras un rechazo | A) se borra solo con un error de la contraseña; B) se borra siempre | A | B: obliga a reescribirla ante un `email_taken`, un límite superado o un fallo de red, donde no tiene la culpa | Spec RF-11 y su caso límite; `formStateAfter` decide por resultado |

### Desviaciones de la T8 respecto a la primera redacción del plan
- `AppShell.tsx` y `main.tsx` entran en la T8: sin ellos `/register` se pintaría como el mapa y `/register/` no se normalizaría.
- El envío usa `aria-disabled` en vez de `disabled`, con guarda por `ref` y campos en `readOnly` durante la operación; la spec (RF-10) dice «deshabilita» sin fijar el mecanismo.
- «Mostrar contraseña» mantiene su etiqueta y cambia solo `aria-pressed`, en vez de alternar con «Ocultar contraseña».
- El `replace("/map")` lo hace solo el efecto de `shouldLeaveRegister`, no el manejador del envío.
- «Creando la cuenta…» y los errores los anuncia la región de estado del formulario, no la global.
- Añadidos que el plan no tenía: resumen «Revisa los campos marcados.», pista «Al menos 10 caracteres.» con las constantes de longitud, token `--color-danger`, `RegistrationForm.tsx` como componente de solo marcado, `formStateForEmpty` (avisa de los campos vacíos sin enviar nada, con los códigos del servidor) y `settleRegistration`.
- El componente de solo marcado se llama `RegistrationForm` y no `RegisterForm`: `registerForm.ts` y `RegisterForm.tsx` solo se diferencian en las mayúsculas, TypeScript lo rechaza (TS1149) y en macOS y Windows serían el mismo fichero.
- Pruebas de mecanismo en una tarea de interfaz, por tocar la privacidad de la contraseña y el doble envío: ver `tasks.md`.

### Notas para el plan de la spec: resolución
| Nota | Resolución |
|---|---|
| CSRF explícito | D1. `apps/core/csrf.py`; fixture `csrf_client`; guarda del URLconf; mutaciones en T3, T5a (registro) y T5b (salida sin sesión) |
| `AuthenticationMiddleware` | D2. Tras `CsrfViewMiddleware`; la lista pública probada con la pila real (T1) |
| Tests existentes | Ver Blast radius |
| Comprobaciones en el contenedor | Ver Estrategia de tests, «Comprobaciones en el contenedor» |

## Blast radius
- **Cambian** (T1 a T9; los ficheros del cambio de RF-14 están en su propio blast radius):
  - `apps/core/api.py` y `tests/test_api.py` (T1);
  - `config/settings/base.py` (T1);
  - `config/tests/test_http_hardening.py` l.86-95 (T1);
  - `apps/assets/serializers.py` y `views.py`, solo el import (T1);
  - `apps/users/services.py`, `tests/test_services.py` l.15-26 y la lista de emails, `tests/test_leaks.py` l.22-24 (T2);
  - `apps/core/tests/test_api_import.py` l.9 (T3);
  - `backend/conftest.py`, solo el fixture nuevo (T3);
  - `config/urls.py` (T5a);
  - `backend/openapi.json` y `frontend/src/api/schema.gen.ts` (T5a y T5b);
  - `frontend/src/api/publicAssets.ts` y `src/map/loadStyle.ts` (T6);
  - `vite.config.ts` (T6);
  - `main.tsx`, `MapPage.tsx` l.78, `NotFoundPage.tsx` l.5 y `i18n/es.ts` (T7);
  - `route.ts`, `route.test.ts`, `main.tsx`, `AppShell.tsx` y `styles/index.css` (T8).
- **No cambian** (T1 a T9; con el cambio de RF-14, `apps/core/tests/test_middleware.py` sigue sin cambiar y `apps/assets/tests/test_public_list_api.py` cambia en C2):
  - `config/tests/test_api_settings.py`, `apps/core/tests/test_middleware.py`;
  - `apps/assets/tests/test_public_list_api.py`, también l.460-468, 513-520, 565-569, 661-699 y 900-918;
  - `test_production.py`, `test_migrations.py`;
  - `publicAssets.test.ts`, `loadStyle.test.ts`, `validate.test.ts`;
  - la CI.
- **Efectos laterales:**
  - el `createsuperuser` interactivo y `changepassword` aplican los validadores, mientras que el no interactivo de `test_superuser.py` no (riesgo aceptado en la spec);
  - `create_user`, `create_superuser` y `change_user_email` rechazan el email con sustituto suelto (antes, error del servidor).

## Riesgos
Los que la spec ya recoge en «Riesgos aceptados» (el usuario los aceptó) no se repiten aquí. Riesgos propios del plan:
| Riesgo | Mitigación |
|---|---|
| Los tests con el cliente por defecto no exigen CSRF | Fixture `csrf_client` en todos los tests de CSRF; guarda del URLconf |
| IPv4 mapeada en IPv6 agruparía todas las IPv4 en un /64 | `ip_bucket` la desenvuelve; test y mutación |
| Proxy de Vite con `changeOrigin` verdadero rechaza todo POST (decisión de la T7 de la 006 corregida) | D10 en T6; en T9 se comprueba que Django recibe `Host: localhost:5173` y que el registro funciona sin `CSRF_TRUSTED_ORIGINS` |
| Un registro vencido por tiempo puede haberse completado en el servidor | Antes de dar el error, el cliente pregunta «quién soy» (D18) |
| El aviso de fallo de «Salir» cambia el alto de la zona de contenido y el mapa debe reajustar su tamaño | Se comprueba en T9 a 375 y a 1280 px; si MapLibre no reajusta, la tarea de holgura lo corrige |
| T5 pasaba de 30 min | Partida con la tarea de holgura: T5a registro y guarda, y T5b «quién soy» y salida, cada una con su regeneración del contrato |
| Registrar en el navegador crea cuentas en la BD de desarrollo | Solo con autorización expresa en ese momento, con `@example.com`; el límite se prueba el último |
| Con una cuenta desactivada, «quién soy» responde `null` pero la fila y la cookie de sesión se mantienen: si la cuenta se reactiva, esa sesión vuelve a valer hasta que caduque | Riesgo aceptado por el usuario: la API no permite desactivar cuentas, y un cambio de contraseña sí invalida la sesión (hash de sesión) |

## Estrategia de tests
| RF | Cómo se verifica |
|---|---|
| RF-1 | pytest (T2): email normalizado, hash (`identify_hasher`), `is_staff` y `is_superuser` en falso. pytest (T5a): 201 con el cuerpo exacto; `sessionid` HttpOnly, Lax y Max-Age 1209600; la sesión nueva es de la cuenta creada; `is_staff: true` y campos desconocidos ignorados. pytest (T5b): «quién soy» después del registro devuelve el email. DevTools (T9) |
| RF-2 | pytest (T2): cada código y el orden completo (email antes que contraseña; required, too_long, too_short, common, numeric, similar); `email_taken` junto a los de contraseña; `Ana@Correo.ES` frente a `ana@correo.es`; 9, 10, 128 y 129 caracteres; `1234567890` → common y numeric; común en mayúsculas y con espacios; igual al email → similar; espacios conservados (`check_password`); vacíos y `null`; NUL en email y contraseña, y sustituto suelto en ambos; email con sustituto en el dominio → `email_invalid` en `register_user`, `create_user`, `create_superuser` y `change_user_email`, sin SQL sobre `users_user`; `password_invalid` va solo; carrera con `skip_validation` → `email_taken`. pytest (T5a): 400 `invalid_fields` con `list(params) == ["email", "password"]`; sesión intacta (métodos de `SessionStore` parcheados para lanzar; fila y clave sin cambios); sin valores. DevTools (T9): email repetido y contraseña débil |
| RF-3 | pytest (T4): `ip_bucket` (IPv4, mismo /64, otro /64, IPv4 mapeada, `%eth0`, vacía, inválida); con una vista de prueba y `timer` falso: 10 pasan y la 11.ª da 429; cuentan las inválidas, las 413, las 405 y las rechazadas por CSRF, no las 429; `X-Forwarded-For` ignorado; el límite va antes que CSRF y que el método; la ventana se libera. pytest (T5a): sobre el endpoint real, cada una de las 10 peticiones previas da su propio código y nunca 429 (sin token y token distinto → 403, `Content-Length` > 4096 y `Transfer-Encoding` → 413, JSON inválido e `invalid_fields` → 400, PUT → 405); la 11.ª, válida, da 429 con `Retry-After` igual a `retry_after` y `no-store`; al terminar cada caso no hay ninguna cuenta. vitest (T6): `waitMinutes` (0→1, 60→1, 61→2, 3600→60). DevTools (T9, el último) |
| RF-4 | pytest (T5a): con una sesión anónima con datos, de otra cuenta o de la misma, `sessionid` y `csrftoken` cambian, los datos desaparecen y la fila anterior no existe |
| RF-5 | pytest (T5b): 204; la fila desaparece; el identificador anterior ya no autentica en «quién soy»; la cookie se retira siempre (con sesión, caducada, mal formada y sin cookie); sin sesión no cambia nada; `csrftoken` intacta |
| RF-6 | pytest (T5b): anónimo → `{"user": null}` y `csrftoken`; con sesión → email; cuenta desactivada, sesión caducada (fila con `expire_date` un segundo en el pasado) y cookie mal formada → `null` sin error; HEAD sin cuerpo; `expire_date` no cambia tras «quién soy» (sin renovación) |
| RF-7 | pytest (T3): mixin con vistas de prueba (sin cabecera, vacía, sin cookie, distinta, cookie mal formada, Origin ajeno; 403 `csrf_failed`, `no-store`, sin motivo en el cuerpo ni en el log; `LimitedStream.read` parcheado para que lance; método no admitido → 405). pytest (T5a): registro con y sin sesión: sin cuenta ni fila nuevas y sesión intacta; guarda del URLconf. pytest (T5b): salida con y sin sesión, igual; la guarda cubre la salida sin tocarla. vitest (T6): un solo reintento tras «quién soy» |
| RF-8 | pytest (T3): 4096 bytes pasan y 4097 dan 413 (declarado y leído); `Transfer-Encoding` → 413; `text/plain` y multipart → 400; JSON inválido, BOM, `NaN`, lista, `"[" * 2048 + "]" * 2048` (400 porque la raíz no es un objeto); `RecursionError` simulado → 400; email numérico, contraseña lista u objeto, booleano → 400; cuerpo vacío → `{}`; objeto anidado en una clave desconocida (unos 600 niveles dentro de 4096 bytes) → se acepta. pytest (T5a): sobre el endpoint, también un email de 4 KB → `email_invalid` y `email_too_long` (el validador de email de Django rechaza más de 320 caracteres) sin 500 y ese objeto anidado → `invalid_fields` con `email_empty` y `password_required` |
| RF-9 | vitest (T6): `whoAmI` con 5 s (temporizador inyectado), 500, red, forma inválida y `Content-Type` ajeno → `anonymous`. vitest (T7): `topBarAction`, `isPlainLeftClick` y el marcado de `TopBar` (`react-dom/server`): sin acciones en `unknown`, la marca es un enlace a `/map`, el email nunca aparece. DevTools (T9): 375 y 1280 px sin desbordar; «quién soy» bloqueado → «Registrarse» y el mapa funciona; la marca lleva a `/map` |
| RF-10 | vitest (T8): `emptyFieldErrors`, `createSubmitGuard` (doble envío), `shouldLeaveRegister`, marcado del formulario (`aria-disabled` y `readOnly` en envío; contraseña sin `value=`). vitest (T6): 201 con forma inválida → «quién soy». DevTools (T9): envío con `aria-disabled`, `/map` sin entrada nueva en el historial (`history.length`), «Atrás» no vuelve al formulario, barra en «Salir», Intro envía |
| RF-11 | vitest (T8): `fieldMessages`, `firstFocusTarget`, `formStateAfter` (un test por caso: email conservado siempre; contraseña borrada solo con `fieldErrors` que traiga un error de `password`, también junto a errores del email; conservada con `fieldErrors` solo del email o de `other`, `throttled` y cada `failed`: `csrf`, `request`, `network`, `server`, `invalid`, `timeout` y `unexpected`; envío habilitado en todos, también con `failed("timeout")`). vitest (T6): reintento único y error general tras el segundo `csrf_failed`; registro vencido a los 10 s con temporizador inyectado → pregunta «quién soy»: con sesión `registered`, sin ella `failed("timeout")`. DevTools (T9): foco y anuncios con el teclado; registro que no responde (`fetch` simulado que no resuelve) → error general y reintento |
| RF-12 | vitest (T7): `logoutResult` (anuncio, foco y aviso en éxito, fallo y tiempo vencido). vitest (T6): reintento de la salida; salida vencida a los 10 s → `failed`. DevTools (T9): «Has salido», foco en «Registrarse»; fallo y tiempo vencido simulados: aviso visible con «Reintentar», foco en «Salir»; segunda pestaña |
| RF-13 | vitest (T8): `resolveRoute` (`/register`, `/register/`, `/register//`, `/REGISTER`) y `shouldLeaveRegister`. vitest (T7): `createNavigator` (`replace` sin entrada nueva, `navigate` a la misma ruta no hace nada, `popstate`). DevTools (T9): `/register` con sesión → `/map` con `replace`; `/register/` normalizada |
| RF-14 | pytest (C2) y navegador (C3): ver «Cambio: clave de sesión (RF-14)», estrategia de tests |

| Requisito no funcional | Verificación |
|---|---|
| Permisos y métodos | pytest (T5a): 405 con `Allow` y formato en PUT, PATCH, DELETE, OPTIONS y HEAD del registro. pytest (T5b): lo mismo en la salida, y en POST, PUT y DELETE de «quién soy» con y sin sesión y sin token, con `Allow: GET, HEAD`. Ninguna operación acepta identificadores |
| Orden de comprobaciones | pytest (T4, T5a): límite antes que método y CSRF; CSRF antes que el cuerpo; cuerpo antes que la validación; con el límite superado, cualquier método del registro da 429 |
| Sesión y cookies | pytest (T1): ajustes por entorno. pytest (T5a y T5b): atributos de las cookies, `csrftoken` legible (sin HttpOnly), Max-Age |
| Lista pública sin cambios | pytest (T1): `test_public_list_session.py`; con la cookie de nulos, C2 (ver «Cambio: clave de sesión (RF-14)») |
| Caché | pytest (T5a): `no-store` en 201, 400, 403, 405, 413 y 429. pytest (T5b): en 200, 204, 403 y 405, y `Vary: Cookie` en «quién soy» |
| Respuestas mínimas | pytest (T5a y T5b): claves exactas `{"user"}` y `{"email"}` con un usuario staff; ni `id` ni `last_login` |
| Desconfianza de la entrada | pytest (T2, T3, T5a): nunca 500 con NUL, sustitutos, anidamiento ni tipos. vitest (T6): esquemas estrictos |
| Errores | pytest (T1, T5a, T5b): códigos y estados. vitest (T8): un mensaje en castellano por código |
| Privacidad y logs | pytest (T2): `test_leaks.py` con `register_user`. pytest (T5a): petición con marca centinela, `caplog` a DEBUG con `force_debug_cursor` y la configuración real del logger comprobada antes; ni email ni contraseña en logs ni en errores; clave del contador sin el email |
| Contrato | pytest (T5a y T5b): `test_auth_contract.py`. CI: desfase de `openapi.json` y `api:check` |
| Mismo origen | pytest (T5a y T5b): sin `Access-Control-*`. DevTools (T9): solo `localhost:5173`; Django recibe `Host: localhost:5173` y el registro funciona sin `CSRF_TRUSTED_ORIGINS` |
| Dependencias | T9: `git diff` de `requirements*` y `package*.json` vacío |
| Accesibilidad, móvil e idioma | DevTools (T9): 375 y 1280 px, teclado, foco visible, 44 px, movimiento reducido, consola sin errores propios |

### Tests que se escriben primero y sus mutaciones (pruebas de mecanismo)
Cada mutación se hace sobre una copia del fichero, con el sha256 antes y después y restauración desde la copia, y se registra en `validation.md`, en la sección de su tarea.
- **T1**:
  - `SessionAuthentication` en `PublicAssetListView` → falla `test_public_list_session`;
  - en los valores por defecto → falla `test_api_settings`;
  - quitar `AuthenticationMiddleware` → falla `test_auth_settings`;
  - `csrf_failed` con estado 400 → falla `test_api`.
- **T2**:
  - calcular el hash antes de comprobar la longitud (trampa de `make_password` con 129 caracteres);
  - quitar la comprobación de sustitutos (email y contraseña, y en `change_user_email`);
  - reordenar los validadores;
  - `password_invalid` junto a los demás;
  - similitud con `user=None`.
- **T3**:
  - comprobar CSRF solo si `request.user.is_authenticated`;
  - `PermissionDenied` en vez de `ApiError`;
  - `CSRFCheck` que acepta siempre;
  - leer el cuerpo antes de CSRF;
  - CSRF antes de `super().initial()`;
  - quitar la comprobación de `Transfer-Encoding`, la de la longitud declarada o el `+ 1` de la lectura;
  - quitar la captura de `RecursionError` (con el error simulado: con datos reales no se produce en este Python);
  - aceptar números como texto.
- **T4**:
  - agrupar en /48 y en /128;
  - usar `X-Forwarded-For`;
  - heredar de `AnonRateThrottle`;
  - anotar también las rechazadas por el límite;
  - no desenvolver la IPv4 mapeada.
- **T5a**:
  - quitar `flush()` del registro;
  - `flush()` y `login()` antes de validar;
  - `ModelSerializer` con todos los campos;
  - quitar `no-store` del éxito;
  - pasar `is_staff` al servicio;
  - quitar el mixin de `RegisterView` (falla el registro sin token y la guarda);
  - `throttle_classes = []` en `RegisterView`;
  - leer el cuerpo en un `initial()` propio antes de `super().initial()` (el 413 dejaría de contar);
  - comprobar CSRF en una clase de autenticación, que corre antes del límite (el 403 dejaría de contar y ganaría al 429).
- **T5b**:
  - quitar `flush()` de la salida (la fila sigue y el identificador anterior aún autentica);
  - quitar `delete_cookie` de la salida: con cookie, `SessionMiddleware` la borra después de la vista y pisa su cabecera, así que solo lo detecta la salida sin cookie de sesión, cuyo test compara Path, Max-Age=0, SameSite y dominio con los ajustes de la cookie de sesión;
  - `django.contrib.auth.logout(request._request)` en vez de `flush()`: equivalente en esta vista, porque DRF ya ha puesto un `AnonymousUser` en la petición de Django y `logout()` no carga la sesión; se anota en `validation.md`;
  - leer la sesión antes de `flush()` (la clave caducada queda en `None` y la fila sobrevive);
  - quitar el mixin de `LogoutView` (falla la salida sin sesión y la guarda);
  - quitar el rechazo del método antes de autenticar en «quién soy» (con sesión y sin token daría 403);
  - `authentication_classes = []` en «quién soy» (con sesión respondería `null`).
  - Quitar el `Vary: Cookie` explícito es una mutación equivalente mientras la sesión se lea: se anota en `validation.md`.
- **T6**:
  - quitar el reintento;
  - reintentar dos veces;
  - guardar el token en vez de leerlo en cada envío;
  - `credentials: "omit"` en el cliente de sesión;
  - quitar el tiempo máximo de «quién soy»;
  - quitar el tiempo máximo del registro y el de la salida (dos mutaciones);
  - no preguntar «quién soy» tras un registro vencido.

### Comprobaciones en el contenedor
- **Verificado** (Django 5.2.18, DRF 3.18.3, drf-spectacular 0.30.0, Python 3.13.16): `login()`, validadores, JSON anidado dentro de 4 KiB (2048 listas anidadas se analizan sin `RecursionError`: dan 400 por la raíz, y un objeto anidado se acepta), throttle, prototipo de CSRF, middleware con la lista pública, lectura de `request.body` por DRF, y el proxy de Vite 8.3.5 contra un backend de prueba. Los tests de T2, T3, T5a y T5b lo fijan en la suite.
- **No verificado, y dónde queda cubierto:**
  - motor de sesión de BD y PostgreSQL: T5a y T5b, en la BD de test;
  - email con sustituto: T2, que lo rechaza sin ninguna consulta (`CaptureQueriesContext`);
  - cuerpo troceado bajo `runserver`: T9, con curl;
  - Vite contra Django, `document.cookie` e History API: T9, en el navegador.

## Afirmaciones no verificadas
- drf-spectacular 0.30.0:
  - `OpenApiParameter` de cabecera con `response=[...]` para `Set-Cookie` pasa `--fail-on-warn`;
  - `SessionAuthentication` genera `cookieAuth` sin avisos;
  - `DictField(child=ListField(...))` sin `read_only` queda opcional.
- Motor de sesión de BD:
  - `flush()` borra la fila de una sesión caducada a partir de la clave de la cookie;
  - `login()` tras `flush()` crea la fila dentro del `atomic`.
- `runserver` pasa `HTTP_TRANSFER_ENCODING` al entorno WSGI.
- `CsrfViewMiddleware.process_request`, ejecutado dos veces con una cookie mal formada, deja una sola cookie nueva.
- La BD de desarrollo tiene la tabla de sesiones: está en `INSTALLED_APPS` y la BD se migró entera, pero no se puede comprobar sin acceder a ella.
- `MapView` libera el mapa al desmontarse (`map.remove()` en la limpieza; se comprueba al volver con «Atrás» en T9) y MapLibre reajusta su tamaño cuando cambia el alto de su contenedor (aviso de salida).
- Con `changeOrigin: false`, `ALLOWED_HOSTS` acepta `localhost:5173` y el Origin coincide con el host.

## Cambio: clave de sesión (RF-14)
Cambio de requisitos posterior a la implementación: RF-14, la definición de «Cookie de sesión mal formada», los casos límite de RF-14 y los criterios «Cambio de RF-14» de la spec. Sus tareas, C1 a C3, se numeran aparte de T1 a T9.

### Resumen
- `apps/core/session_store.py` define `SessionStore`, que hereda de `django.contrib.sessions.backends.db.SessionStore` y redefine solo `_validate_session_key`. Una clave está bien formada si es texto de exactamente 32 caracteres de `a`-`z` y `0`-`9`. En `config/settings/base.py` se añade `SESSION_ENGINE = "apps.core.session_store"`.
- Con una clave mal formada, el setter de `_session_key` la deja en `None`, así que la sesión está vacía desde el principio:
  - ningún método consulta la BD con ese valor (`load`, `flush`, `delete` y `cycle_key`; `delete(None)` vuelve sin consulta);
  - `SessionMiddleware.process_response` retira la cookie porque viene en la petición y la sesión está vacía;
  - el registro y la entrada abren su sesión nueva como siempre.
- La lista pública sigue sin cookies. Con el cambio, `SessionMiddleware` también añade el borrado de la cookie a sus respuestas cuando la cookie está mal formada (antes solo con menos de 8 caracteres). Ese borrado lo quita `CleanMarkedResponseMiddleware`, porque la vista marca todas sus respuestas (`apps/assets/views.py:75-78`).
- Sin modelos, sin migraciones y sin dependencias nuevas. `backend/openapi.json` y el frontend no cambian. No cambia ningún endpoint ni ningún permiso.

### Archivos y responsabilidades
| Archivo | Crea/Modifica | Responsabilidad | RF |
|---|---|---|---|
| backend/apps/core/session_store.py | C | (C2) `SessionStore(db.SessionStore)` con solo `_validate_session_key`: `isinstance(key, str)` y `re.fullmatch` contra `[a-z0-9]{32}`, que devuelve un bool. Un comentario de una línea explica que es la forma de las claves que genera Django | RF-14 |
| backend/config/settings/base.py | M | (C2) `SESSION_ENGINE` junto a los ajustes de sesión (l.42-45). No hay `SESSION_ENGINE` en `test.py` ni en `development.py` | RF-14 |
| backend/apps/core/tests/test_session_store.py | C | (C2) La regla (sin BD), que la subclase solo redefine ese método y que las claves que genera Django cumplen la forma (con BD) | RF-14 |
| backend/config/tests/test_auth_settings.py | M | (C2) El motor es el módulo propio, y el cliente de pruebas usa la clase propia | RF-14 |
| backend/apps/core/tests/test_api_import.py | M | (C2) `MODULES` (l.9-15) gana `apps.core.session_store`: lo nombra un ajuste y se importa al construir `SessionMiddleware` | — |
| backend/apps/core/tests/helpers.py | C | (C1) `KEY_WITHOUT_ROW`. (C2) `OCTAL_NULL`, `raw_cookie_header`, `MALFORMED_SESSION_VALUES` y `session_queries_with`. Son los genéricos de sesión que usan los tests de core, users y assets; `untouchable_session_store` se queda en `apps/users/tests/helpers.py` | RF-14 |
| backend/apps/users/tests/test_session_api.py, test_logout_api.py, test_login_api.py | M | (C1) Importan `KEY_WITHOUT_ROW`; los ids pasan a nombrar la intención. (C2) Los tests de su operación con cookie mal formada; en la entrada se invierte el test del 500 | RF-5, RF-6, RF-7, RF-14 |
| backend/apps/users/tests/test_register_api.py | M | (C2) Los tests del registro con cookie mal formada | RF-1, RF-2, RF-7, RF-14 |
| backend/apps/assets/tests/test_public_list_session.py | M | (C2) `fetch_with_cookie` manda la cabecera en bruto, y la parametrización de la l.119 gana la cookie de nulos | RNF Lista pública, RF-14 |
| backend/apps/assets/tests/test_public_list_api.py | M | (C2) `MALFORMED_COOKIES` (l.677-681) gana `null-characters`, y `set_cookies` (l.684-686) manda la cabecera en bruto con `client.defaults["HTTP_COOKIE"]`, así que la reciben los dos tests que lo parametrizan (l.689-699 y l.724-736), también los envíos de error de `ERROR_SENDERS` | RNF Lista pública, RF-14 |
| docs/architecture.md | M | (C2) Estructura, l.92, l.96 y la lista de internos de la l.110 | — |
| specs/009-auth/validation.md | M | (C3) Sección del cambio: tests, mutaciones y navegador | RF-14 |
| specs/015-login/spec.md | M | (C3) Punto 7 de «Cambios en otras specs» (l.165) | — |
| MEMORY.md | M | (C3) Cierra el paso de la hoja de ruta y anota el aprendizaje de la cookie en bruto | — |

### Decisiones
| Decisión | Opciones | Elegida | Qué evita | Coste |
|---|---|---|---|---|
| DC1 Dónde se comprueba la forma de la clave | A) `SessionStore` propio que redefine solo `_validate_session_key`; B) middleware propio antes de `SessionMiddleware` que descarta la cookie mal formada; C) comprobación en cada vista que toca la sesión (registro, entrada, salida y «quién soy») | A | B: reescribe `request.COOKIES` antes de `SessionMiddleware` y añade un middleware cuyo orden hay que fijar con un test. Además, la cookie descartada ya no llegaría a `SessionMiddleware`, y para retirarla habría que duplicar su `delete_cookie`. C: repite el control en cuatro operaciones y no cubre `SessionMiddleware`, `AuthenticationMiddleware`, `SessionAuthentication`, `Client.session` ni ninguna vista futura; una vista que lo olvide vuelve a dar 500 | Depende de dos internos no documentados de Django: `_validate_session_key` y el setter de `_session_key`. Lo vigilan el test unitario, el de claves generadas, el de «solo redefine» y la nota en `docs/architecture.md`. Suma un ajuste (`SESSION_ENGINE`) |
| DC2 Cómo se escribe la regla | A) `isinstance(key, str)` y `re.fullmatch(r"[a-z0-9]{32}", key)`; B) longitud 32 con `isalnum()` e `islower()`; C) comparar con `VALID_KEY_CHARS` de Django | A | B acepta letras y dígitos Unicode (`ñ`, `٣`). Un `re.match` con `$` aceptaría un `\n` final. C ata la regla a otro interno no documentado, y el alfabeto ya lo fija la spec | Si Django cambiara el alfabeto de sus claves, ver Riesgos |
| DC3 Módulo | A) `apps/core/session_store.py`; B) `apps/users/sessions.py`; C) `apps/core/sessions.py` | A | B: el motor vale para todas las peticiones, también la lista pública, no solo para las vistas de `users`. C: al leer los imports se confunde con `django.contrib.sessions`. `core` ya agrupa las piezas HTTP transversales (`csrf.py`, `middleware.py`, `request_body.py`) | Un fichero más y su entrada en `test_api_import.py` |
| DC4 Cómo llega la cookie de nulos en los tests | A) cabecera `Cookie` en bruto (`HTTP_COOKIE`) con escape octal; B) el almacén de cookies del cliente (`client.cookies`) | A | B: `SimpleCookie` rechaza los caracteres de control con `CookieError` | `raw_cookie_header` en `apps/core/tests/helpers.py`. La barra del escape se construye con `chr(92)`, como hoy en `test_login_api.py:55-56` |
| DC5 Forma de los tests de cada operación | A) tests nuevos por operación, parametrizados con los valores mal formados; B) añadir casos a las parametrizaciones existentes (`COOKIE_STATES`, `EMPTY_SESSIONS`, `EVERY_STATE`, `WITHOUT_A_VALID_SESSION`) | A | B: esas parametrizaciones ponen la cookie con `prepare(client)` en el almacén del cliente, que no admite nulos (DC4). Además, sus aserciones no distinguen «no busca» en los valores de 31 o 33 caracteres, que hoy dan el mismo resultado visible | Cuatro bloques de tests parecidos que comparten los helpers |
| DC6 Dónde viven los helpers comunes | A) `apps/core/tests/helpers.py` para los genéricos de sesión (`KEY_WITHOUT_ROW`, `OCTAL_NULL`, `raw_cookie_header`, `MALFORMED_SESSION_VALUES` y `session_queries_with`); B) `apps/users/tests/helpers.py`; C) fixtures en `backend/conftest.py` | A | B: `test_session_store.py`, de core, usa `KEY_WITHOUT_ROW` en el id `mixed`, así que core importaría de los tests de users, y los tests de assets también. C: son constantes y funciones, no fixtures, y se mezclarían con los globales | Un fichero nuevo de helpers en core, que crea C1. `untouchable_session_store` se queda en `apps/users/tests/helpers.py` |

### Blast radius
- **Comportamiento que cambia**:
  - Toda petición con una cookie de sesión mal formada (vacía, de otra longitud, con mayúsculas, con caracteres de control o fuera de ASCII) se trata como sin sesión, sin consultar la BD.
  - Toda respuesta no marcada, incluidos los 404 y 405 del router, lleva `Set-Cookie: sessionid=""; Max-Age=0` y `Vary: Cookie` cuando llega una de esas cookies. Antes solo pasaba con menos de 8 caracteres.
  - `Client.session` y `force_login` con una cookie mal formada no consultan la BD.
- **Sin cambios, comprobado**:
  - `get_model_class` no hace falta: el modelo y la tabla son los mismos.
  - `Session.get_session_store_class()` sigue devolviendo el `SessionStore` de BD. Solo lo usa `get_decoded()` (`test_login_api.py:221` y `:347`, `test_register_api.py:94`), lo cual es inocuo.
  - `clearsessions` hereda `clear_expired`.
  - Las sesiones abiertas antes del cambio tienen claves generadas por Django, que están bien formadas.
- **Inventario de valores de cookie de sesión en los tests, por intención**:

| Fichero:línea | Valor | Intención | Con la regla nueva | Acción |
|---|---|---|---|---|
| `apps/users/tests/test_session_api.py:23-24` (uso 88-90; id `key-without-row` en 96 y 117) | `KEY_WITHOUT_ROW = "k3y5in4f1l4" * 3` (33) | Clave bien formada sin fila | Pasaría a estar mal formada y probaría otra cosa | C1: 32 caracteres `[a-z0-9]`, en `apps/core/tests/helpers.py` |
| `apps/users/tests/test_logout_api.py:31-32` (uso 159-161; id `closed-in-another-tab` en 171) | El mismo | El mismo | El mismo | C1 |
| `apps/users/tests/test_login_api.py:57-58` (uso 137-139; `COOKIE_STATES` en 294) | El mismo | El mismo | El mismo | C1 |
| `apps/users/tests/test_session_api.py:76-79` (comentario en 77; id `shorter-than-8` en 96 y 115) | `"abc1234"` | Mal formada a propósito | Sigue mal formada | Se mantiene. C1: id `too-short` y un comentario que no cite el umbral de Django |
| `apps/users/tests/test_logout_api.py:151-152` (id en 171) | `"abc1234"` | Mal formada a propósito | Sigue mal formada | Se mantiene. C1: id `too-short` |
| `apps/users/tests/test_login_api.py:132-134` (usos 293 y 367) | `"abc"` | Mal formada a propósito | Sigue mal formada | Se mantiene |
| `apps/users/tests/test_session_api.py:82-85` (valor en 83, asignado en 84) y `test_logout_api.py:155-156` | `"no-es-una-clave-de-sesion-" * 3` (78, con guiones) | Mal formada a propósito | Hoy pasa la validación de Django y se busca sin encontrar fila. Ahora no se busca, con el mismo resultado visible | Se mantiene |
| `apps/assets/tests/test_public_list_session.py:119` | `"short"` y `"!" * 40` | Mal formada a propósito | `"!" * 40` hoy pasa la validación y la cookie no se retira. Ahora `SessionMiddleware` añade el borrado y `CleanMarkedResponseMiddleware` lo quita | Se mantienen. C2: ids explícitos y se añade la de nulos |
| `apps/assets/tests/test_public_list_session.py:17-18` | `UNKNOWN_KEY = "a" * 32` | Clave bien formada sin fila | Sigue bien formada | Se mantiene |
| `apps/assets/tests/test_public_list_api.py:677-681` | `"short"` | Mal formada a propósito | Sigue mal formada | Se mantiene. C2: `MALFORMED_COOKIES` gana `null-characters`, con la cabecera en bruto |
| `apps/core/tests/test_middleware.py:15` | `"short"` | Mal formada a propósito | Sigue mal formada | Se mantiene |
| `apps/users/tests/test_login_api.py:55-56` y `:423-439` | Ocho nulos con escape octal | Mal formada a propósito | Deja de dar 500 | C2: se invierte el test, se replica en las otras tres operaciones y en las dos guardas de la lista pública, y `OCTAL_NULL` pasa a `apps/core/tests/helpers.py` |
| `test_session_api.py:31-34`, `test_logout_api.py:45-48` y `:187-189`, `test_login_api.py:101-114`, `test_register_api.py:68-82`, `test_public_list_session.py:49-58` | Claves de `force_login`, `log_in` y `SessionStore().create()` | Sesión válida | Las genera Django y están bien formadas | Se mantienen |

- **`patch.object` y `monkeypatch` sobre la clase base**: `apps/users/tests/helpers.py:64` (`untouchable_session_store`), `test_middleware.py:250`, `test_public_list_api.py:668` y `test_register_api.py:200` parchean `django.contrib.sessions.backends.db.SessionStore`. Siguen aplicándose por MRO, porque la subclase no redefine esos métodos; lo fija `test_the_store_only_redefines_the_key_validation`. Las tres primeras pasarían en vacío si el parche no llegara, así que cada una tiene su mutación de control (M2, M2b y M3a). La de `test_register_api.py:200` se valida sola: si el parche no llegara, el registro tendría éxito y fallaría `pytest.raises(SessionCreateFailed)`.

### Riesgos
| Riesgo | Mitigación |
|---|---|
| Una versión de Django cambia `_validate_session_key` o el setter de `_session_key`, y la regla deja de aplicarse sin aviso | Test unitario de la regla a través de `SessionStore(valor).session_key`, test de «solo redefine» y nota en la lista de internos de `docs/architecture.md:110`, con la condición de borrado de `SessionMiddleware.process_response`, para revisarlo al subir de 5.2.x. En Django 6.1, `SessionBase.__bool__` devuelve `not is_empty()`; hoy no hay ningún `if request.session:` |
| Django cambia el alfabeto o la longitud de sus claves: `create()` asigna una clave que el setter pone a `None`, `save()` vuelve a `create()` y se produce un `RecursionError` (500 en todo registro y toda entrada) | `test_keys_created_by_django_are_well_formed` (con `create()` y `cycle_key()`) falla al actualizar Django, antes de desplegar |
| Si la subclase redefiniera un método parcheado, esos tests pasarían en vacío | Test de «solo redefine» y mutaciones M2, M2b, M3a y M4 |
| La lista pública pasa a depender de `CleanMarkedResponseMiddleware` con cualquier cookie mal formada | Guardas con la cookie de nulos en `test_public_list_session.py` y `test_public_list_api.py`. `assert_same_as_anonymous` (`test_public_list_session.py:76-82`) y `assert_same_public_answer` (`test_public_list_api.py:630-637`) ya exigen que no haya `Set-Cookie` ni `Cookie` en `Vary`. M5 repite con el motor nuevo la mutación «No marcar las respuestas» de la 006 (`specs/006-public-map/validation.md:235`), que se ejecutó con el motor viejo |
| Efecto nuevo: las respuestas no marcadas retiran cualquier cookie mal formada y declaran `Vary: Cookie` | Es lo que pide RF-14. No cambia ningún endpoint ni ningún permiso |
| `SessionMiddleware` resuelve el motor al construirse, así que `override_settings` no cambiaría el de un cliente ya creado | No hay overrides de `SESSION_ENGINE`. El test de ajustes usa un cliente nuevo |
| Una cookie plantada desde un subdominio, con otro `Domain` o `Path`, no se borra | Riesgo ya aceptado («Inyección de cookies desde subdominios hermanos», spec 011) |

Privacidad: nadie pierde la sesión, no hay logs nuevos y no se puede enumerar nada, porque una cookie mal formada, una sin fila y una caducada responden igual. El tiempo de respuesta solo revela la regla de forma, que es pública en el código de Django.

### Estrategia de tests
| Aspecto de RF-14 | Cómo se verifica |
|---|---|
| Regla de forma | pytest sin BD (`test_session_store.py`). `test_a_well_formed_key_is_kept`, con ids `letters` (`"a" * 32`), `digits` (`"0" * 32`) y `mixed` (`KEY_WITHOUT_ROW`). `test_a_malformed_key_is_no_session`, con ids `none`, `empty`, `seven-characters`, `31-characters`, `33-characters`, `uppercase`, `n-with-tilde`, `arabic-indic-digit` (`٣`), `eight-nulls`, `thirty-two-nulls`, `control-character` (31 + `\x1f`), `trailing-newline` (32 + `\n`), `leading-space`, `trailing-space`, `hyphen` (32 con un `-`) y `long-with-hyphens`. Los caracteres invisibles se construyen con `chr()` |
| Solo cambia la validación | `test_the_store_only_redefines_the_key_validation`: los nombres no dunder de `vars(SessionStore)` son exactamente `{"_validate_session_key"}`, y la clase es subclase de la de BD |
| Sesiones abiertas antes del cambio y claves futuras | `test_keys_created_by_django_are_well_formed` (con BD): las claves de `create()` y de `cycle_key()` cumplen `[a-z0-9]{32}` |
| Motor configurado | `test_auth_settings.py`. `test_the_session_engine_is_the_project_store`: `settings.SESSION_ENGINE == "apps.core.session_store"` e `import_module(...).SessionStore` es la clase propia. `test_the_test_client_uses_the_project_store` (con BD): tras `force_login`, `type(client.session)` es la clase propia |
| Registro | `test_register_api.py`, parametrizados con `MALFORMED_SESSION_VALUES` (ids `null-characters`, `31-characters`, `33-characters`, `uppercase`, `non-ascii`). `test_a_malformed_session_cookie_is_ignored_when_registering`: 201, `sessionid` nueva que cumple la forma, una sola fila de sesión y de la cuenta creada, y ninguna consulta a `django_session` con ese valor. `test_a_rejected_registration_removes_a_malformed_session_cookie`: 400 `invalid_fields`, sin cuenta ni fila y con la cookie retirada (`Max-Age=0`). `test_without_a_token_a_malformed_session_cookie_is_removed`: 403 `csrf_failed`, sin efectos y con la cookie retirada. Contrapeso: `test_a_well_formed_key_without_row_is_looked_up`, en el que sí hay una consulta a `django_session` con `KEY_WITHOUT_ROW` |
| Entrada | `test_login_api.py`, con los mismos valores. `test_a_malformed_session_cookie_is_ignored_when_logging_in` sustituye a `test_a_session_cookie_with_null_characters_gives_a_server_error_on_success`; su id `null-characters` es la inversión: 200, sesión nueva y cookie sin el nulo. `test_a_failed_login_removes_a_malformed_session_cookie`: 400 `credentials_invalid` y la cookie retirada. `test_without_a_token_a_malformed_session_cookie_is_removed`. Y el contrapeso con `KEY_WITHOUT_ROW` |
| Salida | `test_logout_api.py`. `test_a_malformed_session_cookie_is_ignored_when_logging_out`: 204, cookie retirada, `stored_sessions()` y las cuentas sin cambios, y ninguna consulta con ese valor. `test_without_a_token_a_malformed_session_cookie_is_removed`. Y el contrapeso (`DELETE` con `KEY_WITHOUT_ROW`) |
| «Quién soy» | `test_session_api.py`. `test_a_malformed_session_cookie_is_ignored_when_asking`, con GET y HEAD: 200, `{"user": null}` en GET, cookie retirada, `csrftoken` presente, `no-store`, `Vary: Cookie` y ninguna consulta con ese valor. Y el contrapeso (`SELECT` con `KEY_WITHOUT_ROW`) |
| Lista pública | `test_public_list_session.py::test_a_malformed_or_unknown_cookie_changes_nothing`, con ids `short`, `exclamation-marks`, `null-characters` y `unknown-key`: la misma respuesta que la del anónimo, sin `Set-Cookie`, sin `Cookie` en `Vary` y sin consultas a `django_session`. `test_public_list_api.py`: `MALFORMED_COOKIES` gana `null-characters`, así que `test_malformed_cookies_do_not_make_the_success_response_set_cookies[null-characters]` (respuesta idéntica, sin cookies y con `Vary: Accept-Encoding`) y `test_error_responses_of_the_view_leave_without_cookies` con `null-characters` en 400, 405 y 429 (sin cookies) también la prueban. Están en verde desde el principio |
| Punta a punta | Navegador y petición real de salida (C3) |

Todas las peticiones con valores mal formados mandan la cabecera `Cookie` en bruto: `HTTP_COOKIE=raw_cookie_header(csrftoken=TOKEN, sessionid=valor)`. El helper escapa en octal todo carácter fuera de `[A-Za-z0-9]` y solo sirve para puntos de código menores que 256. El `٣` solo se prueba sin BD. Los tests de las cuatro operaciones usan `Client(enforce_csrf_checks=True, raise_request_exception=False)`, para que el error del servidor aparezca como un 500 y no como una excepción. `session_queries_with(captured, value)` devuelve las consultas de `CaptureQueriesContext` que nombran `django_session` y contienen el valor.

**Tests que se escriben primero (C2) y por qué fallan antes del código**
- Ids `null-characters` de los cuatro tests `..._is_ignored_when_...`: 500, porque PostgreSQL rechaza el nulo. En el registro, la entrada y la salida lo provoca el `DELETE` de `flush()`; en «quién soy», el `SELECT` de `load()`.
- Resto de ids de esos cuatro tests: hay una consulta a `django_session` con el valor.
- `..._removes_a_malformed_session_cookie` y `..._without_a_token_...`, todos los ids: la cookie no se retira, porque la sesión no está vacía.
- `test_session_store.py`: no se importa, porque el módulo no existe.
- Tests de ajustes: el motor es el de Django.
- Contrapesos y guardas de la lista pública: pasan antes y después del código.

**Mutación «quitar la comprobación de la forma»**
`_validate_session_key` pasa a devolver `super()._validate_session_key(key)`. Se elige así y no borrando el método para que el test de «solo redefine» siga pasando. La lista se escribe en `validation.md` antes de ejecutarla. Deben fallar 63:
- `test_session_store.py::test_a_malformed_key_is_no_session`, 13 ids: `31-characters`, `33-characters`, `uppercase`, `n-with-tilde`, `arabic-indic-digit`, `eight-nulls`, `thirty-two-nulls`, `control-character`, `trailing-newline`, `leading-space`, `trailing-space`, `hyphen` y `long-with-hyphens`.
- `test_register_api.py`: `test_a_malformed_session_cookie_is_ignored_when_registering`, `test_a_rejected_registration_removes_a_malformed_session_cookie` y `test_without_a_token_a_malformed_session_cookie_is_removed`, cada uno con sus 5 ids (15).
- `test_login_api.py`: `test_a_malformed_session_cookie_is_ignored_when_logging_in`, `test_a_failed_login_removes_a_malformed_session_cookie` y `test_without_a_token_a_malformed_session_cookie_is_removed`, cada uno con sus 5 ids (15).
- `test_logout_api.py`: `test_a_malformed_session_cookie_is_ignored_when_logging_out` y `test_without_a_token_a_malformed_session_cookie_is_removed`, cada uno con sus 5 ids (10).
- `test_session_api.py::test_a_malformed_session_cookie_is_ignored_when_asking`, con 5 ids en GET y en HEAD (10).

No deben fallar:
- `test_a_malformed_key_is_no_session[none]`, `[empty]` y `[seven-characters]`, que la regla de Django ya rechaza;
- los cuatro contrapesos;
- `test_keys_created_by_django_are_well_formed`;
- el test de «solo redefine»;
- los dos de ajustes;
- todo `test_public_list_session.py` y `test_public_list_api.py`;
- el resto de la suite.

**Mutaciones de control**
Cada una lleva su lista escrita en `validation.md` antes de ejecutarla.
- **M1**, quitar `SESSION_ENGINE` de `base.py`: fallan los dos tests de ajustes y los 50 casos de las cuatro operaciones de la lista anterior. No falla ninguno de `test_session_store.py`, que importa la clase directamente.
- **M2**, `PublicAssetListView.get` empieza leyendo `request._request.session.get("x")`. Fallan:
  - `test_public_list_api.py::test_the_session_is_never_read_and_the_answer_is_the_same`, con «sesión leída»: el parche de la l.668 llega al motor nuevo;
  - `test_public_list_session.py::test_a_valid_session_is_never_read_and_the_answer_is_the_same`, `test_an_expired_session_is_never_read_and_the_answer_is_the_same` y `test_a_malformed_or_unknown_cookie_changes_nothing[unknown-key]`.

  Los ids `short`, `exclamation-marks` y `null-characters` siguen pasando: con la clave en `None`, la sesión no se carga.
- **M2b**, `marked_view` (`test_middleware.py:18-19`) llama a `request.session.load()`: falla `test_marked_view_does_not_load_the_session` con «Sesión cargada», porque el parche de la l.250 llega al motor nuevo. Los demás tests del bloque B que usan la vista marcada fallan por acceder a la BD sin marca; se anota.
- **M3a**, se repite la m2 de la T5a (`flush()` al principio de `post`, `validation.md:261`): fallan los 3 casos de `test_a_rejected_registration_leaves_the_session_untouched` con «session.flush», porque `untouchable_session_store` (`apps/users/tests/helpers.py:64`) llega al motor nuevo.
- **M3b**, se repite la m3b de la T5b (leer la sesión antes de `flush()`, `validation.md:316`): falla `test_an_expired_session_row_is_deleted_too`.
- **M4**, añadir `def load(self): return super().load()` a la subclase: solo falla `test_the_store_only_redefines_the_key_validation`.
- **M5**, quitar `mark_response_cookieless` de `apps/assets/views.py:78` (`finalize_response` devuelve la respuesta sin marcar), con el motor nuevo. La de la 006 se ejecutó con el motor viejo, y las guardas de los nulos nunca se han visto fallar. La lista exacta se escribe en `validation.md` antes de ejecutarla, partiendo de los 13 fallos de la 006, y debe incluir los ids `null-characters` de las dos guardas: `test_public_list_session.py::test_a_malformed_or_unknown_cookie_changes_nothing[null-characters]`, `test_public_list_api.py::test_malformed_cookies_do_not_make_the_success_response_set_cookies[null-characters]` y los tres casos `null-characters` de `test_public_list_api.py::test_error_responses_of_the_view_leave_without_cookies` (400, 405 y 429).
- `test_register_api.py:200` no necesita mutación: se valida con `pytest.raises`.

### Tareas
- **C1. Clave sin fila bien formada y compartida.** RF-14 (preparación), RF-5, RF-6
  - Alcance: solo tests.
    - `KEY_WITHOUT_ROW = "0123456789abcdefghijklmnopqrstuv"` en `apps/core/tests/helpers.py`, que se crea, con el comentario «Bien formada (32 caracteres de a-z y 0-9) y sin fila en la BD». Lo importan `test_session_api.py`, `test_logout_api.py` y `test_login_api.py`, que pierden su definición (l.23-24, 31-32 y 57-58).
    - `test_the_key_without_row_is_well_formed_and_has_no_row` en `test_session_api.py`: `re.fullmatch` y ninguna fila.
    - Ids `shorter-than-8` → `too-short` (`test_session_api.py:96` y `:115`, `test_logout_api.py:171`). El comentario de `test_session_api.py:77` pasa a «Mal formada: más corta que una clave de sesión».
    - Ningún otro valor del inventario cambia.
  - Commit: `test(users): share a well-formed session key without row`
  - Hecho cuando:
    - toda la suite, ruff y la comprobación de migraciones están en verde;
    - `KEY_WITHOUT_ROW` se define solo en `apps/core/tests/helpers.py`;
    - el número de tests recogidos sube en uno (el de la precondición);
    - el diff solo toca `apps/core/tests/helpers.py` (nuevo) y los tres ficheros de test.

- **C2. Motor de sesión que ignora las claves mal formadas.** RF-14, RF-1, RF-2, RF-5, RF-6, RF-7, RNF Lista pública sin cambios
  - Alcance:
    - Primero los tests:
      - los helpers de C2 en `apps/core/tests/helpers.py`, con `OCTAL_NULL` traído de `test_login_api.py:55-56`;
      - los de las cuatro operaciones, con la inversión de `test_login_api.py:423-439`;
      - `test_session_store.py` y los dos de `test_auth_settings.py`;
      - la guarda de `test_public_list_session.py`: `fetch_with_cookie` (l.35-40) con `raw_cookie_header` y la cookie de nulos con ids en la l.119;
      - la guarda de `test_public_list_api.py`: `MALFORMED_COOKIES` (l.677-681) gana `null-characters` y `set_cookies` (l.684-686) manda la cabecera en bruto.
    - Después `apps/core/session_store.py`, `SESSION_ENGINE` en `base.py` y `MODULES` en `test_api_import.py`.
    - `docs/architecture.md`:
      - estructura: `session_store.py` junto a `middleware.py` (l.31);
      - l.92: con una cookie mal formada, también la de nulos, `SessionMiddleware` añade el borrado y la marca lo quita;
      - l.96: la sesión pasa por `apps.core.session_store` y una cookie mal formada equivale a no tener sesión;
      - l.110: `_validate_session_key`, el setter de `_session_key` y la condición de borrado de `SessionMiddleware.process_response` como internos que hay que revisar al actualizar Django, con la nota de `SessionBase.__bool__` en 6.1.
  - Commit: `fix(core): treat malformed session keys as no session`
  - Hecho cuando:
    - antes del código, los tests nuevos fallan por la razón esperada de la estrategia de tests (los ids `null-characters` de las cuatro operaciones, con 500) y las guardas de la lista pública ya pasan;
    - después, pasan toda la suite, ruff y `config/tests/test_migrations.py`;
    - `manage.py check` no da avisos;
    - regenerar `backend/openapi.json` no produce diferencias;
    - `git diff` de `frontend/`, `requirements*` y las migraciones está vacío.

- **C3. Mutaciones, comprobación de punta a punta y cierre.** RF-14
  - Alcance:
    - En `validation.md`, una sección «Cambio: clave de sesión (RF-14)» con C1 y C2 (tests que fallaron primero y recuentos).
    - La lista de la mutación «quitar la forma» y las de M1 a M5, escritas antes de ejecutar cada una. Se ejecutan sobre una copia, con el sha256 antes y después.
    - La nota de que `Client.session` y `force_login` con una cookie mal formada no consultan la BD.
    - Navegador, a 1280 y 375 px, a través del proxy de Vite:
      - con `sessionid="\000\000\000\000\000\000\000\000"` puesta con `document.cookie`, `/map` carga con «Entrar» y «Registrarse», sin errores en la consola, y la respuesta de «quién soy» retira la cookie;
      - con la cookie puesta otra vez, un POST real a `/api/v1/auth/logout/` desde la página, con `X-CSRFToken`, responde 204 con `Set-Cookie: sessionid=""; Max-Age=0`, y `document.cookie` queda sin `sessionid`.
    - Ninguna de esas peticiones consulta la BD de desarrollo. Si el stack no está levantado, se pregunta antes.
    - Punto 7 en `specs/015-login/spec.md:165`.
    - `MEMORY.md`: se quita el primer punto de «Próximos pasos», la hoja de ruta avanza y se anota que `SimpleCookie` rechaza los caracteres de control, así que los tests mandan la cookie en bruto.
  - Commit: `docs(spec-009): validate malformed session cookie change`
  - Hecho cuando:
    - en `validation.md`, cada mutación da exactamente la lista escrita, o la diferencia queda explicada;
    - el sha256 es idéntico antes y después de cada mutación;
    - la comprobación en el navegador queda registrada a 375 y 1280 px;
    - el riesgo «Cookie de sesión con nulos» de la 015 dice el texto del punto 7;
    - la validación termina con un veredicto sobre RF-14.

### Hallazgos de la revisión que no se aplican
- Añadir la cookie de nulos a `COOKIE_STATES`, `EMPTY_SESSIONS` y `EVERY_STATE`: esas parametrizaciones usan el almacén del cliente, que no admite nulos; se usan tests dedicados (DC5).
- Añadir la cookie de nulos a `test_middleware.py:15`: no es un test de la lista pública.
- Alinear el plan, las tareas y la validación de la 015: son el registro de lo que se implementó entonces. Solo cambia su spec (punto 7), y la corrección queda en esta validación.
- M4 con `return {}`: se usa `return super().load()`, que detecta lo mismo sin romper otros tests.

### Afirmaciones no verificadas
- En PostgreSQL con psycopg 3, el SQL que captura `CaptureQueriesContext` lleva los valores interpolados. Si no fuera así, los contrapesos fallarían en C2 y habría que cambiar `session_queries_with`.
- `parse_cookie` de Django deshace `\361` en `ñ`. Que deshace `\000` ya se comprobó en la 015 (`specs/015-login/validation.md:245`). Si `\361` no se deshiciera, el valor seguiría mal formado y el caso `ñ` seguiría cubierto por el test sin BD.
- Chrome acepta en `document.cookie` un valor entre comillas con barras (`"\000…"`) y lo envía tal cual. Si no fuera así, la petición de salida se hace con curl a través del proxy de Vite y se anota la limitación.
- Que `SimpleCookie` rechaza los caracteres de control solo se ha comprobado en el Python 3.12 del host. La cabecera en bruto no depende de ello.
- `client.defaults["HTTP_COOKIE"]` pisa la cabecera que el cliente de pruebas construye con su almacén de cookies, así que llega también a los envíos de `ERROR_SENDERS`. Se comprueba en C2 antes de añadir el id `null-characters`; si no fuera así, `set_cookies` cambia de forma y se anota.

## Skills que aplican
- sdd y django-drf.
- frontend-design y web-design-guidelines (barra superior y `/register`).
- Mientras no existan las skills react-ts y testing, se aplican los riesgos de MEMORY.md: jsdom no calcula layout, y los mocks de fetch respetan `AbortSignal`.
