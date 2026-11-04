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
| backend/apps/users/serializers.py | C | (T5) `SessionUserSerializer`, `SessionSerializer`, `RegistrationRequestSerializer` (solo documenta) y `RegistrationErrorSerializer` | RF-1, RF-6, RNF |
| backend/apps/users/views.py | C | (T5) `RegisterView`, `CurrentSessionView` y `LogoutView`; `public_field_errors(message_dict)` | RF-1…RF-8 |
| backend/apps/users/urls.py; backend/config/urls.py | C; M | (T5) `auth/register/`, `auth/session/` y `auth/logout/` bajo `api/v1/` | RF-1, RF-5, RF-6 |
| backend/apps/users/tests/test_register_api.py, test_session_api.py, test_logout_api.py, test_auth_contract.py | C | (T5) Contrato HTTP, sesión, cookies, cabeceras y OpenAPI | RF-1…RF-8 |
| backend/apps/core/tests/test_csrf_guard.py | C | (T5) Toda vista del URLconf que atiende métodos no seguros hereda el mixin | RF-7 |
| backend/openapi.json; frontend/src/api/schema.gen.ts | M | (T5) Contrato regenerado | RNF Contrato |
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
| frontend/src/register/registerForm.ts, registerForm.test.ts; pages/RegisterPage.tsx | C | (T8) Lógica del formulario y página | RF-10, RF-11, RF-13 |
| specs/009-auth/validation.md | C (T1), M | Evidencia de las mutaciones de cada tarea y validación final; incluye la nota de la desviación del proxy de Vite (T6, T9) | Todos |
| docs/architecture.md | M | (T9) Capa de autenticación, CSRF explícito, cuerpo acotado, límite /64, estructura del frontend | — |

## Modelo de datos y migraciones
- **No hay modelos ni migraciones nuevos.**
  - La sesión usa el motor de BD por defecto (`django.contrib.sessions`, ya instalado).
  - El usuario es el de la 004, sin cambios.
  - Las cuentas se crean por el servicio.
- `config/tests/test_migrations.py` (`makemigrations --check`, en la BD de test) sigue en verde en T1 y en T5.
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
  - Cookies: `Set-Cookie: csrftoken` siempre (`get_token`). `sessionid` no cambia, salvo el borrado que hace Django de una cookie mal formada o de un hash obsoleto.
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
  - vacía, `None` o inválida → el texto recibido, o `""`, sin lanzar.
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
  - `no-store` y `patch_vary_headers(("Cookie",))`.
- `LogoutView(CsrfEnforcedMixin, APIView)`: `authentication_classes = []`, `AllowAny`, `["post"]`; `request._request.session.flush()`; 204; `delete_cookie(SESSION_COOKIE_NAME, path=..., domain=..., samesite=...)`; `no-store`.
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
  - `formStateAfter(outcome)`: conserva el email, borra la contraseña, elige el mensaje general (también para `failed("timeout")`) y vuelve a habilitar el envío;
  - `shouldLeaveRegister(status)`: `authenticated` → sí;
  - `createSubmitGuard()`: un envío a la vez.

## Interfaz
- **AppShell**: `div.flex.h-dvh.flex-col` con la barra (`header`), el aviso de salida cuando existe y la zona de contenido (`div.relative.min-h-0.flex-1`). Cada página pone su `<main>`.
  - Al cambiar de página, el foco va a la zona (`tabIndex=-1`), para no perderlo en un elemento que desaparece.
  - Una región `role="status"` (polite), solo para lectores de pantalla, anuncia «Has salido», «Cuenta creada.» y «Creando la cuenta…».
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
  - `<main>` con `h1` «Crear una cuenta» y un formulario de ancho máximo `max-w-sm` con `noValidate`.
  - Email: `type="email"`, `autoComplete="email"`, `inputMode="email"`.
  - Contraseña: `autoComplete="new-password"`, con el botón «Mostrar contraseña» / «Ocultar contraseña» (`type="button"`, `aria-pressed`, `aria-controls`) de 44 px.
  - Envío «Crear cuenta» de 44 px; Intro en el último campo envía.
  - Se pinta sin esperar a «quién soy». Si el estado pasa a `authenticated`, `replace("/map")`.
  - Errores:
    - por campo, con `aria-invalid` y `aria-describedby`, uno o varios mensajes;
    - el general, en la región de estado del formulario (`role="status"`, `tabIndex=-1`).
  - Al enviar:
    - se anuncia «Creando la cuenta…» y el envío queda `disabled`;
    - un doble clic o un doble Intro no envían dos veces (guarda);
    - si se rechaza, falla o vence a los 10 s: el email se conserva, la contraseña se borra, el envío vuelve a habilitarse para reintentar y el foco va al primer campo con error o a la región.
  - Al registrarse: el estado pasa a `authenticated`, se anuncia «Cuenta creada.» y se hace `replace("/map")`, sin entrada nueva en el historial.
- **Mensajes del catálogo (`es.ts`)**:
  - `email_taken`: «Ya existe una cuenta con este email.» (fijado por la spec);
  - `throttled`: el texto fijado por la spec;
  - `email_empty` «Escribe tu email.», `email_invalid` «Escribe un email válido.», `email_control_char` «El email tiene caracteres no permitidos.», `email_too_long` «El email es demasiado largo.»;
  - `password_required` «Escribe una contraseña.», `password_invalid` «La contraseña tiene caracteres no permitidos.», `password_too_long` «La contraseña no puede tener más de 128 caracteres.», `password_too_short` «La contraseña debe tener al menos 10 caracteres.», `password_too_common` «Esa contraseña es demasiado común.», `password_entirely_numeric` «La contraseña no puede tener solo números.», `password_too_similar` «La contraseña se parece demasiado al email.»;
  - generales: tiempo vencido, «La petición ha tardado demasiado. Inténtalo de nuevo.»; CSRF tras el reintento, «No se ha podido enviar el formulario. Recarga la página e inténtalo de nuevo.»; red, servidor e inesperado, como la 006.
- **Movimiento reducido**: sin transiciones. Contraste AA con los tokens de la 006.

## Decisiones
| Decisión | Opciones | Elegida | Qué evita | Coste |
|---|---|---|---|---|
| D1 CSRF anónimo | A) mixin en `initial()` con `CSRFCheck` sobre el `HttpRequest` con `POST` vacío; B) `csrf_protect`; C) clase de autenticación que llama a `enforce_csrf`; D) `CSRFCheck` con el `Request` de DRF | A | B: 403 en HTML sin `no-store` y antes del límite. C: corre antes del límite y da `forbidden`. D: 415 antes de decidir, y lee el cuerpo con formularios | Toca `request._request.POST`; la guarda del URLconf obliga a heredar el mixin |
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

### Notas para el plan de la spec: resolución
| Nota | Resolución |
|---|---|
| CSRF explícito | D1. `apps/core/csrf.py`; fixture `csrf_client`; guarda del URLconf; mutaciones en T3 y T5, con registro y salida sin sesión |
| `AuthenticationMiddleware` | D2. Tras `CsrfViewMiddleware`; la lista pública probada con la pila real (T1) |
| Tests existentes | Ver Blast radius |
| Comprobaciones en el contenedor | Ver Estrategia de tests, «Comprobaciones en el contenedor» |

## Blast radius
- **Cambian:**
  - `apps/core/api.py` y `tests/test_api.py` (T1);
  - `config/settings/base.py` (T1);
  - `config/tests/test_http_hardening.py` l.86-95 (T1);
  - `apps/assets/serializers.py` y `views.py`, solo el import (T1);
  - `apps/users/services.py`, `tests/test_services.py` l.15-26 y la lista de emails, `tests/test_leaks.py` l.22-24 (T2);
  - `apps/core/tests/test_api_import.py` l.9 (T3);
  - `backend/conftest.py`, solo el fixture nuevo (T3);
  - `config/urls.py` (T5);
  - `backend/openapi.json` y `frontend/src/api/schema.gen.ts` (T5);
  - `frontend/src/api/publicAssets.ts` y `src/map/loadStyle.ts` (T6);
  - `vite.config.ts` (T6);
  - `main.tsx`, `MapPage.tsx` l.78, `NotFoundPage.tsx` l.5 y `i18n/es.ts` (T7);
  - `route.ts` y `route.test.ts` (T8).
- **No cambian:**
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
| T5 puede pasar de 30 min | Se parte con la tarea de holgura: T5a registro y T5b «quién soy», salida y guarda, cada una con su regeneración del contrato |
| Registrar en el navegador crea cuentas en la BD de desarrollo | Solo con autorización expresa en ese momento, con `@example.com`; el límite se prueba el último |

## Estrategia de tests
| RF | Cómo se verifica |
|---|---|
| RF-1 | pytest (T2): email normalizado, hash (`identify_hasher`), `is_staff` y `is_superuser` en falso. pytest (T5): 201 con el cuerpo exacto; `sessionid` HttpOnly, Lax y Max-Age 1209600; «quién soy» después devuelve el email; `is_staff: true` y campos desconocidos ignorados. DevTools (T9) |
| RF-2 | pytest (T2): cada código y el orden completo (email antes que contraseña; required, too_long, too_short, common, numeric, similar); `email_taken` junto a los de contraseña; `Ana@Correo.ES` frente a `ana@correo.es`; 9, 10, 128 y 129 caracteres; `1234567890` → common y numeric; común en mayúsculas y con espacios; igual al email → similar; espacios conservados (`check_password`); vacíos y `null`; NUL en email y contraseña, y sustituto suelto en ambos; email con sustituto en el dominio → `email_invalid` en `register_user`, `create_user`, `create_superuser` y `change_user_email`, sin SQL sobre `users_user`; `password_invalid` va solo; carrera con `skip_validation` → `email_taken`. pytest (T5): 400 `invalid_fields` con `list(params) == ["email", "password"]`; sesión intacta (métodos de `SessionStore` parcheados para lanzar; fila y clave sin cambios); sin valores. DevTools (T9): email repetido y contraseña débil |
| RF-3 | pytest (T4): `ip_bucket` (IPv4, mismo /64, otro /64, IPv4 mapeada, `%eth0`, vacía, inválida); con una vista de prueba y `timer` falso: 10 pasan y la 11.ª da 429; cuentan las inválidas, las 405 y las rechazadas por CSRF, no las 429; `X-Forwarded-For` ignorado; el límite va antes que CSRF y que el método; la ventana se libera. pytest (T5): sobre el endpoint real, `Retry-After` igual a `retry_after` y `no-store`. vitest (T6): `waitMinutes` (0→1, 60→1, 61→2, 3600→60). DevTools (T9, el último) |
| RF-4 | pytest (T5): con una sesión anónima con datos, de otra cuenta o de la misma, `sessionid` y `csrftoken` cambian, los datos desaparecen y la fila anterior no existe |
| RF-5 | pytest (T5): 204; la fila desaparece; el identificador anterior ya no autentica en «quién soy»; la cookie se retira siempre (con sesión, caducada, mal formada y sin cookie); sin sesión no cambia nada; `csrftoken` intacta |
| RF-6 | pytest (T5): anónimo → `{"user": null}` y `csrftoken`; con sesión → email; cuenta desactivada, sesión caducada (fila con `expire_date` un segundo en el pasado) y cookie mal formada → `null` sin error; HEAD sin cuerpo; `expire_date` no cambia tras «quién soy» (sin renovación) |
| RF-7 | pytest (T3): mixin con vistas de prueba (sin cabecera, vacía, sin cookie, distinta, cookie mal formada, Origin ajeno; 403 `csrf_failed`, `no-store`, sin motivo en el cuerpo ni en el log; `LimitedStream.read` parcheado para que lance; método no admitido → 405). pytest (T5): registro y salida con y sin sesión: sin cuenta ni fila nuevas y sesión intacta; guarda del URLconf. vitest (T6): un solo reintento tras «quién soy» |
| RF-8 | pytest (T3): 4096 bytes pasan y 4097 dan 413 (declarado y leído); `Transfer-Encoding` → 413; `text/plain` y multipart → 400; JSON inválido, BOM, `NaN`, lista, `"[" * 2048 + "]" * 2048` (400 porque la raíz no es un objeto); `RecursionError` simulado → 400; email numérico, contraseña lista u objeto, booleano → 400; cuerpo vacío → `{}`; objeto anidado en una clave desconocida (unos 600 niveles dentro de 4096 bytes) → se acepta. pytest (T5): sobre el endpoint, también un email de 4 KB → `email_too_long` sin 500 y ese objeto anidado → `invalid_fields` con `email_empty` y `password_required` |
| RF-9 | vitest (T6): `whoAmI` con 5 s (temporizador inyectado), 500, red, forma inválida y `Content-Type` ajeno → `anonymous`. vitest (T7): `topBarAction`, `isPlainLeftClick` y el marcado de `TopBar` (`react-dom/server`): sin acciones en `unknown`, la marca es un enlace a `/map`, el email nunca aparece. DevTools (T9): 375 y 1280 px sin desbordar; «quién soy» bloqueado → «Registrarse» y el mapa funciona; la marca lleva a `/map` |
| RF-10 | vitest (T8): `emptyFieldErrors`, `createSubmitGuard` (doble envío), `shouldLeaveRegister`. vitest (T6): 201 con forma inválida → «quién soy». DevTools (T9): envío deshabilitado, `/map` sin entrada nueva en el historial (`history.length`), «Atrás» no vuelve al formulario, barra en «Salir», Intro envía |
| RF-11 | vitest (T8): `fieldMessages`, `firstFocusTarget`, `formStateAfter` (email conservado, contraseña vacía, envío habilitado, también con `failed("timeout")`). vitest (T6): reintento único y error general tras el segundo `csrf_failed`; registro vencido a los 10 s con temporizador inyectado → pregunta «quién soy»: con sesión `registered`, sin ella `failed("timeout")`. DevTools (T9): foco y anuncios con el teclado; registro que no responde (`fetch` simulado que no resuelve) → error general y reintento |
| RF-12 | vitest (T7): `logoutResult` (anuncio, foco y aviso en éxito, fallo y tiempo vencido). vitest (T6): reintento de la salida; salida vencida a los 10 s → `failed`. DevTools (T9): «Has salido», foco en «Registrarse»; fallo y tiempo vencido simulados: aviso visible con «Reintentar», foco en «Salir»; segunda pestaña |
| RF-13 | vitest (T8): `resolveRoute` (`/register`, `/register/`, `/register//`, `/REGISTER`) y `shouldLeaveRegister`. vitest (T7): `createNavigator` (`replace` sin entrada nueva, `navigate` a la misma ruta no hace nada, `popstate`). DevTools (T9): `/register` con sesión → `/map` con `replace`; `/register/` normalizada |

| Requisito no funcional | Verificación |
|---|---|
| Permisos y métodos | pytest (T5): 405 con `Allow` y formato en PUT, PATCH, DELETE, OPTIONS y HEAD del registro y de la salida, y en POST de «quién soy»; ninguna operación acepta identificadores |
| Orden de comprobaciones | pytest (T4, T5): límite antes que método y CSRF; CSRF antes que el cuerpo; cuerpo antes que la validación; con el límite superado, cualquier método del registro da 429 |
| Sesión y cookies | pytest (T1): ajustes por entorno. pytest (T5): atributos de las cookies, `csrftoken` legible (sin HttpOnly), Max-Age |
| Lista pública sin cambios | pytest (T1): `test_public_list_session.py` |
| Caché | pytest (T5): `no-store` en 201, 200, 204, 400, 403, 405, 413 y 429; `Vary: Cookie` en «quién soy» |
| Respuestas mínimas | pytest (T5): claves exactas `{"user"}` y `{"email"}` con un usuario staff; ni `id` ni `last_login` |
| Desconfianza de la entrada | pytest (T2, T3, T5): nunca 500 con NUL, sustitutos, anidamiento ni tipos. vitest (T6): esquemas estrictos |
| Errores | pytest (T1, T5): códigos y estados. vitest (T8): un mensaje en castellano por código |
| Privacidad y logs | pytest (T2): `test_leaks.py` con `register_user`. pytest (T5): petición con marca centinela, `caplog` a DEBUG con `force_debug_cursor` y la configuración real del logger comprobada antes; ni email ni contraseña en logs ni en errores; clave del contador sin el email |
| Contrato | pytest (T5): `test_auth_contract.py`. CI: desfase de `openapi.json` y `api:check` |
| Mismo origen | pytest (T5): sin `Access-Control-*`. DevTools (T9): solo `localhost:5173`; Django recibe `Host: localhost:5173` y el registro funciona sin `CSRF_TRUSTED_ORIGINS` |
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
- **T5**:
  - quitar `flush()` del registro;
  - `flush()` y `login()` antes de validar;
  - quitar `flush()` y `delete_cookie` de la salida;
  - quitar el mixin de `LogoutView` (falla la salida sin sesión y la guarda);
  - `ModelSerializer` con todos los campos;
  - quitar `no-store` del éxito;
  - pasar `is_staff` al servicio.
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
- **Verificado** (Django 5.2.18, DRF 3.18.3, drf-spectacular 0.30.0, Python 3.13.16): `login()`, validadores, JSON anidado dentro de 4 KiB (2048 listas anidadas se analizan sin `RecursionError`: dan 400 por la raíz, y un objeto anidado se acepta), throttle, prototipo de CSRF, middleware con la lista pública, lectura de `request.body` por DRF, y el proxy de Vite 8.3.5 contra un backend de prueba. Los tests de T2, T3 y T5 lo fijan en la suite.
- **No verificado, y dónde queda cubierto:**
  - motor de sesión de BD y PostgreSQL: T5, en la BD de test;
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

## Skills que aplican
- sdd y django-drf.
- frontend-design y web-design-guidelines (barra superior y `/register`).
- Mientras no existan las skills react-ts y testing, se aplican los riesgos de MEMORY.md: jsdom no calcula layout, y los mocks de fetch respetan `AbortSignal`.
