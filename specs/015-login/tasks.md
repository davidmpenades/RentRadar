# Tareas 015 — Entrada
Spec: specs/015-login/spec.md · Plan: specs/015-login/plan.md
Máximo 10 tareas: hay 10, en orden lineal de dependencia (T1 → … → T10), con el corte del plan. La T1 lleva un commit por spec y la T10 cuatro; la T2 va precedida del commit que crea `validation.md`; la T8 lleva dos commits; la T5 puede llevar un commit más de documentación (Desviación 2 del plan).

Reglas comunes:
- Cada commit de código (T2 a T9) es atómico y deja en verde pytest, `ruff check` y `ruff format --check`, la comprobación de migraciones, el desfase de `openapi.json`, vitest, build, eslint de los ficheros tocados y `api:check`. Los tests se escriben primero y fallan por la razón que indica cada tarea; el fallo se anota en `validation.md`.
- El backend solo se prueba en el contenedor, contra la BD de test. No hay modelos, migraciones ni dependencias nuevas.
- **OK del desarrollador**, marcado en cada tarea con «OK necesario». Un OK al empezar la tarea cubre los `docker compose exec` de pytest y ruff con el stack ya levantado. Necesitan OK orden a orden, en ese momento: levantar, parar o reiniciar el stack; cada `docker compose run`, que siempre lleva `--no-deps -e DB_HOST=db-inexistente.invalid`; la regeneración del contrato (T5); y toda escritura en la BD de desarrollo (T10). Un implementer nunca levanta, para ni reinicia el stack.
- Pruebas de mecanismo en T2 a T6 y T8 (plan, «Pruebas de mecanismo»): cada mutación sobre una copia del fichero, con sha256 antes y después y restauración desde la copia, registrada en la sección de su tarea en `validation.md`. Si una mutación sobrevive, se explica o se añade el test que falta.
- Antes de cada commit, el diff completo y el grep de rutas personales sobre las líneas añadidas. La casilla de cada tarea se marca en su propio commit: `docs(spec-015): mark Tn done`.

## Tareas

- [ ] **T1. Cambios de texto en las specs 009, 016 y 015.** RF-7, RF-8 (texto), RNF Igualdad de tiempo
  - Ficheros:
    - `specs/009-auth/spec.md`: RF-9 (sin sesión, «Entrar» y «Registrarse»), RF-10 (enlace «¿Ya tienes cuenta? Entra») y RF-12 (foco tras salir a «Entrar»); se corrigen las frases obsoletas de las líneas 193 («sin entrada hasta la 015…»), 205 («sin entrada (spec 015) no se puede usar») y 221 (cita a las notas borradas de la 015).
    - `specs/016-visual-system/spec.md`: Definiciones («Botón»: «Entrar» de la barra es secundario y el envío «Entrar» es principal), RF-4 y RF-5 (región de estado de la entrada como la del registro, con «Entrando…»).
    - `specs/015-login/spec.md`: «Igualdad de tiempo» fija un hash con hashes al coste actual; «Riesgos aceptados» suma el hash con coste antiguo (`harden_runtime` con la contraseña errónea, rehash con la correcta también en una cuenta desactivada, hasher heredado distinto del preferido) y el límite por IP agotable desde otra web con POST rechazados por CSRF; aclaración de que `user_login_failed` solo se emite cuando se llama a la autenticación de Django (los rechazos por la forma no la emiten).
  - Tests: no aplica (solo texto). Pruebas de mecanismo: no aplica.
  - OK necesario: el diff de cada spec antes de su commit.
  - Commits, en este orden: `docs(spec-009): reflect login in the auth spec`, `docs(spec-016): add login buttons and status region`, `docs(spec-015): equalize hash cost and add accepted risks`.
  - Hecho cuando: los cinco cambios de «Cambios en otras specs» de la 015 y las Desviaciones 1, 3 y 4 y el riesgo nuevo del plan están en el texto; un grep de «hasta la 015», «spec 015) no se puede usar» y «notas de la 015» en `specs/009-auth/spec.md` no da resultados.

- [ ] **T2. Almacén `login` y límite por IP.** RF-3, RNF Almacén
  - Ficheros:
    - `backend/config/settings/base.py`: `CACHES` con `default` (LocMemCache sin opciones, como el implícito de hoy) y `login` (`LOCATION = "login-attempts"`, `MAX_ENTRIES` 20 000, `CULL_FREQUENCY` 10).
    - Crea `backend/config/tests/test_cache_settings.py`.
    - `backend/conftest.py`: `clear_default_cache` pasa a `clear_caches` y vacía todos los alias de `settings.CACHES`.
    - `backend/apps/users/throttling.py`: `wait_seconds`, `LOGIN_CACHE_ALIAS`, `LoginIpThrottle` (`rate` y `scope` en la clase, `cache` como `property`, `wait()` propio) y `client_bucket`.
    - `backend/apps/users/tests/helpers.py`: `Clock` (tercer uso); `test_throttling.py` y `test_register_api.py` pasan a importarlo, sin cambiar sus casos.
    - `backend/apps/users/tests/throttle_views.py` y `throttle_urls.py`: `LoginIpLimitedView` y su ruta, sobre `PostOnlyView`.
    - Crea `backend/apps/users/tests/test_login_throttling.py`.
    - `specs/015-login/validation.md`: sección de la T2.
  - Antes del commit de la T2, un commit aparte crea `specs/015-login/validation.md` solo con la sección «Comprobaciones en el contenedor (2026-11-18)»: versiones (Django 5.2.18, DRF 3.18.3, drf-spectacular 0.30.0); el fallo de la orden con `inspect.getsource` (`ImproperlyConfigured`) y la orden con `ast` del plan; el resultado punto por punto con las líneas del código fuente (recuento de hashes en los cuatro casos y `harden_runtime`, rehash, `get_ident` con `NUM_PROXIES=0`, `dispatch` y el 405, `SimpleRateThrottle.wait`, `LocMemCache._cull`, `salted_hmac`, `_validate_session_key`, `is_empty`, `login()` y `user_login_failed`); y lo que esa lectura no cubre, con la tarea cuyo test lo fija.
  - Tests (primero; fallan porque no existen el alias `login`, `wait_seconds`, `LoginIpThrottle` ni la vista de prueba):
    - `test_cache_settings.py`: alias exactos, `LOCATION` distinta, capacidad 20 000, `CULL_FREQUENCY` 10, `default` con su capacidad de 300 y aislamiento real (una clave escrita en `login` no existe en `default`).
    - `wait_seconds` con 20 anotaciones, con 23 (cuenta desde `history[19]`) y con decimales (redondeo hacia arriba, mínimo 1).
    - Sobre la vista de prueba con `Clock`: 20 pasan y la 21.ª da 429 con `retry_after == 60`; la espera baja con el reloj; ventana deslizante (10, a los 30 s otras 10, 429; a los 60 s pasan 10); los 429 no cuentan ni alargan la espera; cuentan 400, 403, 405 (también HEAD y OPTIONS) y 413; el límite va antes que el CSRF, el método y el cuerpo; `X-Forwarded-For` se ignora; dos IPv6 del mismo /64 comparten límite y otro /64 no; IP vacía o inválida al cubo fijo; con 23 marcas sembradas en `caches["login"]`, el `retry_after` sale de `history[19]`; un `override_settings` de `CACHES` cambia el almacén que usa el límite (la `property`).
    - `test_production.py` y `test_settings.py` siguen en verde con `CACHES` declarado.
  - Pruebas de mecanismo: espera desde `history[-1]`; ventana fija (sin podar); anotar también los rechazos; `cache` del alias `default`; `MAX_ENTRIES` 300 o la misma `LOCATION` que `default`; quitar el `wait()` propio; tomar la IP de `X-Forwarded-For` (o `NUM_PROXIES = None` con `override_settings`).
  - OK necesario: al empezar la tarea, para los `exec` de pytest y ruff; orden a orden, levantar el stack si está parado.
  - Commits, en este orden: `docs(spec-015): record container checks` (solo `validation.md` con la sección de las comprobaciones en el contenedor) y `feat(users): add login ip limit with its own cache`.
  - Hecho cuando: el primer commit solo contiene `validation.md` con esa sección; los tests nuevos fallan primero por la razón indicada y luego pasan; `openapi.json` no cambia; la suite entera, ruff y la comprobación de migraciones en verde; `validation.md` tiene la sección de la T2 con sus mutaciones.

- [ ] **T3. Clave del par y límite de fallos por IP y email.** RF-4, RNF Privacidad y logs
  - Ficheros: `backend/apps/users/throttling.py` (`LOGIN_PAIR_KEY_SALT`, `login_pair_key`, `LoginFailureLimit` con `wait` y `record_failure`, sin `reset`); `test_login_throttling.py`; `validation.md`.
  - Tests (primero; fallan porque no existen `login_pair_key` ni `LoginFailureLimit`):
    - La clave no contiene el email ni una marca; `"  Ana@Correo.ES "` y `"ana@correo.es"` dan la misma clave; `None`, ausente y `""` la comparten; `chr(0xD800)` y `"\x00"` dan clave sin error y distinta de otra; `override_settings(SECRET_KEY=…)` la cambia; otro cubo, otra clave; con un email que empieza por U+00A8 (escrito en el test con escape), la clave es igual a un HMAC calculado en el test sobre una sola normalización y distinta de la de dos normalizaciones; `client_bucket` ignora `X-Forwarded-For`; las claves `login_pair:` y `throttle_login_ip_` no se solapan.
    - `LoginFailureLimit` con `Clock`: ventana deslizante de 15 minutos; con 5 fallos `wait` devuelve la espera; con 7 anotaciones cuenta desde `history[4]`; `wait` no anota; `record_failure` guarda con `timeout` igual a la ventana y en `caches["login"]`.
  - Pruebas de mecanismo: clave sin secreto (`hashlib.sha256`); email en claro en la clave; `encode("utf-8")` estricto; normalizar dos veces; clave sin cubo; ventana fija; espera desde la anotación más antigua; `client_bucket` desde `X-Forwarded-For`.
  - OK necesario: al empezar la tarea, para los `exec` de pytest y ruff; orden a orden, levantar el stack si está parado.
  - Commit: `feat(users): add login failure limit per ip and email`
  - Hecho cuando: los tests fallan primero y luego pasan; un script (que busca el punto de código 0xA8 sin escribir el carácter) comprueba que los ficheros de test tocados no contienen U+00A8 literal, que va como escape; suite, ruff y migraciones en verde; mutaciones registradas en `validation.md`.

- [ ] **T4. Comprobación de credenciales.** RF-1, RF-2, RNF Igualdad de tiempo, Señal de salida, Privacidad y logs
  - Ficheros:
    - Crea `backend/apps/users/login.py`: `CREDENTIALS_INVALID`, `is_queryable_email`, `is_checkable_password` y `check_credentials` (con `@sensitive_variables("email", "password")`; el email crudo va a `authenticate`).
    - Crea `backend/apps/users/tests/test_login_credentials.py`.
    - `backend/apps/users/tests/helpers.py`: `untouchable_session_store`, `stored_sessions` y `cross_origin_headers` (tercer uso), movidos desde `test_register_api.py` y `test_logout_api.py`, que pasan a importarlos sin cambiar sus casos.
    - `backend/apps/users/tests/test_logout_api.py`: la salida no emite `user_logged_out`.
    - `validation.md`.
  - Tests (primero; fallan porque no existe `apps.users.login`, salvo el de la señal de salida, que es de caracterización y pasa al escribirlo: su valor lo da la mutación con `logout()`):
    - Prefiltro: email `None`, `""`, solo espacios, con `"\x00"` y con `chr(0xD800)`; contraseña `None`, `""`, de 129 puntos de código y con sustituto → `None` sin consultas (`CaptureQueriesContext`), sin hash y sin `user_login_failed`.
    - Recuento de hashes parcheando `encode` del hasher de test (MD5), tras comprobar con `identify_hasher` el algoritmo de cada cuenta: exactamente 1 con email desconocido consultable, contraseña errónea, cuenta desactivada (con la contraseña correcta y con una errónea) y contraseña inutilizable; 0 con email no consultable, contraseña no comprobable y 129 puntos de código; 1 con 128 puntos de código errónea; un email sin arroba se consulta.
    - Aciertos: `"  Ana@Correo.ES "` y `"ana@correo.es"` devuelven la cuenta; una contraseña correcta con `"\x00"` también.
    - Rehash: una sola prueba con `override_settings(PASSWORD_HASHERS=[PBKDF2 de pocas iteraciones definido en el test, MD5])` y una cuenta guardada con MD5.
    - La entrada de `normalize_email` en la clave del par y la de `get_by_natural_key` son el mismo valor crudo (espías), también con U+00A8.
    - `user_login_failed` solo cuando se llama a `authenticate`, con la contraseña tapada; ningún contenido del email o la contraseña da un error del servidor.
    - `check_credentials` declara sus variables sensibles y el informe de error de Django con `DEBUG` no muestra la marca.
    - Si un test muestra que Django se comporta distinto de lo que supone el plan (por ejemplo, que `MD5PasswordHasher.verify` no llama a `encode`), se para y se avisa.
  - Pruebas de mecanismo: quitar el tope de 128; pasar `""` a `authenticate`; consultar la cuenta antes y no llamar a `authenticate` sin ella; pasar el email ya normalizado; quitar el rechazo del sustituto; `django.contrib.auth.logout()` en `LogoutView`; quitar `@sensitive_variables`.
  - OK necesario: al empezar la tarea, para los `exec` de pytest y ruff; orden a orden, levantar el stack si está parado.
  - Commit: `feat(users): add login credential check`
  - Hecho cuando: los tests fallan primero y luego pasan (el de la señal de salida, anotado como caracterización con su mutación); un script (que busca el punto de código 0xA8 sin escribir el carácter) comprueba que los ficheros de test tocados no contienen U+00A8 literal, que va como escape; los tests de registro y salida pasan sin cambios en sus casos; suite, ruff y migraciones en verde.

- [ ] **T5. Endpoint de entrada (sin límites).** RF-1, RF-2, RF-5, RF-6, RNF Permisos, Respuestas mínimas, Contrato
  - Ficheros:
    - `backend/apps/users/serializers.py`: `LoginRequestSerializer` (`component_name="Login"`) y `LoginErrorSerializer`.
    - `backend/apps/users/views.py`: `LoginView` (`CsrfEnforcedMixin`, sin autenticación, `AllowAny`, solo POST, `@sensitive_variables` en `post`), `LOGIN_MAX_BYTES = 4096`, `LOGIN_COOKIES` y `_open_session` (`flush()` y `login()` en `transaction.atomic()`).
    - `backend/apps/users/urls.py`: `auth/login/` con `name="auth-login"`.
    - Crea `backend/apps/users/tests/test_login_api.py`; modifica `test_auth_contract.py` y `backend/apps/core/tests/test_csrf_guard.py`.
    - Regenera `backend/openapi.json` y `frontend/src/api/schema.gen.ts` (orden de «Descripción OpenAPI» del plan y `npm run api:gen`), en el mismo commit que la vista.
    - `validation.md`.
  - Tests (primero; fallan con 404 en `/api/v1/auth/login/` y por la operación `login` ausente del contrato):
    - RF-1: 200 con cuerpo exacto `{"user": {"email": "ana@correo.es"}}`; `sessionid` HttpOnly, Lax, Max-Age 1209600 y Path `/`; «quién soy» devuelve el email después; con cuenta de staff, solo el email.
    - RF-2: respuesta idéntica en estado, cuerpo y cabeceras (sin `Date`; cookies por nombre y atributos), parametrizada por causa (desconocido, no consultable en todas sus formas, sin arroba, unos 4000 caracteres, contraseña errónea, vacía, de 129 y con sustituto, cuenta desactivada con su contraseña correcta, contraseña inutilizable) y por estado de cookie (sin sesión, sesión válida, `sessionid` de menos de 8 caracteres, clave de 8 o más desconocida); ninguna da 500.
    - RF-5: con sesión anónima con datos, de otra cuenta, de la misma y de staff, cambian `sessionid` y `csrftoken`, los datos desaparecen y la fila anterior no existe; con cookie caducada o mal formada y credenciales correctas, entra; tras un fallo, `untouchable_session_store`, `stored_sessions()` igual y sin `Set-Cookie` de sesión; sustituir la sesión de otra cuenta no emite `user_logged_out`; cookie `sessionid` con nulos por escape octal (Desviación 2).
    - RF-6: sin token, vacío, sin cookie, distinto u `Origin` ajeno → 403 `csrf_failed` sin llamar a `check_credentials` (parcheado para fallar) y con la sesión intacta; PUT y DELETE sin token → 405; `LimitedStream.read` parcheado → `csrf_failed`; cuerpos mal formados, de 4097 bytes, declarado grande y troceado; email numérico, contraseña lista u objeto → `invalid_request`; `is_staff: true` y `next` se ignoran; 405 con `Allow: POST` en GET, PUT, PATCH, DELETE, OPTIONS y HEAD; `no-store` en 200, las dos 400, 403, 405 y 413; sin `Access-Control-*`; la guarda del URLconf llega a `LoginView`.
    - Contrato: operación `login`, `LoginRequest`, `LoginError`, `Set-Cookie` en el 200 y `cookieAuth` solo en «quién soy».
    - Si la cookie con nulos da 500, el test fija ese comportamiento y la tarea sigue (Desviación 2, opción A).
  - Pruebas de mecanismo: otro código o estado para la cuenta desactivada; quitar `flush()`; leer `request.session` en el fallo; quitar `CsrfEnforcedMixin`; quitar `no-store` del 200; `ModelSerializer` con todos los campos.
  - OK necesario: al empezar la tarea, para los `exec` de pytest y ruff; orden a orden, levantar el stack si está parado y la regeneración del contrato (el `docker compose run` de `spectacular`), en el momento de lanzarla. El cambio de contrato está aprobado en la spec.
  - Commits: `feat(users): add login endpoint`; si la cookie con nulos da 500, además `docs(spec-015): accept malformed session cookie risk` (riesgo aceptado que también afecta a la 009, para la 011).
  - Hecho cuando: los tests fallan primero y luego pasan; `spectacular --validate --fail-on-warn`, el diff de `openapi.json` regenerado, `npm run api:check` y `npm run build` en verde; suite, ruff y migraciones en verde.

- [ ] **T6. Límites conectados al endpoint, orden y fugas.** RF-3, RF-4, RF-5, RF-6, RNF Orden de comprobaciones, Privacidad y logs
  - Ficheros: `backend/apps/users/views.py` (`throttle_classes = [LoginIpThrottle]`; en `post`, tras leer el cuerpo, `LoginFailureLimit.wait` → `Throttled`, y `record_failure` tras un fallo de credenciales); `test_login_api.py`; `validation.md`.
  - Tests (primero; fallan sobre la vista de la T5 porque no hay ningún límite):
    - RF-3: 20 entradas correctas y la 21.ª con credenciales correctas → 429 sin sesión y sin llamar a `check_credentials`; un rechazo del par cuenta en RF-3; con el límite superado, cualquier método da 429; `X-Forwarded-For` distinto en cada petición no lo evita.
    - RF-4: 5 fallos y la contraseña correcta → 429 sin sesión y sin llamar a `check_credentials`; con 7 fallos sembrados para el par, `retry_after` de `history[4]`; a los 15 minutos del primer fallo, entra; 4 fallos, acierto y fallo → el 6.º intento da 429; 4 fallos, acierto y acierto → 200; un rechazo del par no anota un fallo; cuentan los fallos de emails no consultables; el mismo email desde otro /64 entra; dos IPv6 del mismo /64 comparten; `X-Forwarded-For` distinto no evita el límite.
    - RF-5 y RF-6: un rechazo por cualquiera de los dos límites no toca la sesión; `no-store` en los dos 429; ningún rechazo de RF-6 anota un fallo; con el par bloqueado, un cuerpo mal formado da su error y no 429.
    - Fugas: email y contraseña centinela con una marca, `caplog` a DEBUG con `force_debug_cursor`; la marca no aparece en el log, en ninguna respuesta (200, 400 y los dos 429) ni en las claves y valores de `caches["login"]`; un receptor temporal de `user_login_failed` recibe la contraseña tapada; `LoginView.post` declara sus variables sensibles y el informe de error con `DEBUG` no muestra la marca.
  - Pruebas de mecanismo: anotar el acierto como fallo; reiniciar al acertar; anotar el rechazo del par; comprobar el par tras las credenciales; llamar a `check_credentials` antes del cuerpo y del par; comprobar el par en `initial()` antes de `super().initial()`; anotar fallos en los rechazos de RF-6; `throttle_classes = []`; quitar `no-store` de los 429; la IP desde `X-Forwarded-For`.
  - OK necesario: al empezar la tarea, para los `exec` de pytest y ruff; orden a orden, levantar el stack si está parado.
  - Commit: `feat(users): rate limit the login endpoint`
  - Hecho cuando: los tests fallan primero sobre la vista de la T5 y luego pasan; `openapi.json` no cambia; suite, ruff y migraciones en verde; `validation.md` reúne las mutaciones de T2 a T6.

- [ ] **T7. Entrada en el cliente de sesión.** RF-8
  - Ficheros: `frontend/src/api/session.ts` (`LOGIN_URL`, `LoginOutcome`, `login()`, `interpretLogin`, `isCredentialsInvalid`; extracción de `postWithin` y `retryOnceOnCsrf`, tercer uso, que pasan a usar el registro y la salida) y `session.test.ts`.
  - Tests (primero; fallan porque `login` no existe):
    - 200 válido → `loggedIn`; 200 con forma inválida o cuerpo cortado → «quién soy» (con sesión `loggedIn`, sin ella `failed`); red, cuerpo cortado y 5xx → «quién soy»; vencimiento a los 10 s con temporizador inyectado → «quién soy»; 400 exacto → `credentialsInvalid`; 400 con otra forma o código → `failed("invalid")`; 429 con `retry_after` válido → `throttled`, fuera de rango → `failed("invalid")`; un `csrf_failed` → un solo reintento tras «quién soy»; dos → `failed("csrf")`.
    - Tras `login`, la salida envía el token nuevo de la cookie.
    - Los tests del registro y de la salida pasan sin cambios tras la extracción.
  - Pruebas de mecanismo: no aplica (plan).
  - OK necesario: ninguno (frontend en el host).
  - Commit: `feat(frontend): add login to the session client`
  - Hecho cuando: los tests nuevos fallan primero y luego pasan; vitest, build, eslint de los ficheros tocados y `api:check` en verde.

- [ ] **T8. Página `/login` y enlaces cruzados.** RF-8, RF-9
  - Ficheros:
    - `frontend/src/session/sessionState.ts` y su test: `authenticatedResult(how)` (sustituye a `registrationResult`), `shouldLeaveAuthForm` (movida desde `registerForm.ts`) y `settleUnexpected` (tercer uso; sustituye a `settleLogout` y `settleRegistration`).
    - `SessionProvider.tsx`: `markRegistered` pasa a `markAuthenticated(how)`.
    - `frontend/src/app/route.ts` y su test (`login` y `redirectToLogin`); `main.tsx` (`redirectToLogin: "/login"`); `AppShell.tsx` (`Page` pinta `LoginPage`; `leaveToMap` común).
    - Crea `frontend/src/login/loginForm.ts` y su test, `frontend/src/login/LoginForm.tsx` y `LoginForm.test.ts`, y `frontend/src/pages/LoginPage.tsx`.
    - `frontend/src/register/registerForm.ts` y su test (exporta `generalMessage`), `RegistrationForm.tsx` y su test (enlace «¿Ya tienes cuenta? Entra», `Messages` exportado) y `RegisterPage.tsx` (`markAuthenticated("registered")` y `shouldLeaveAuthForm`).
    - `frontend/src/i18n/es.ts`: textos de `login`, `session.loggedIn` y `register.toLogin`.
    - `validation.md`.
  - Tests (primero; fallan porque no existen la ruta, `loginForm.ts`, `LoginForm.tsx` ni `authenticatedResult`):
    - `resolveRoute`: `/login`, `/login/`, `/login//` y `/LOGIN`; `shouldLeaveAuthForm`; `authenticatedResult` con «Cuenta creada.» y «Has entrado.»; `settleUnexpected` sin registrar las credenciales.
    - `formStateAfterLogin` por resultado: contraseña borrada solo con `credentialsInvalid`; email conservado siempre; los dos campos conservados con límite y con fallo; foco a la región de estado; envío habilitado de nuevo.
    - Marcado de `LoginForm` con `react-dom/server`: etiquetas, `autocomplete` email y `current-password`, contraseña sin `value=`, `aria-disabled` y `readOnly` durante el envío, «Mostrar contraseña» con `aria-pressed` y `aria-controls`, enlace a `/register` de 44 px.
    - `RegistrationForm` con el enlace a `/login` de 44 px.
  - Pruebas de mecanismo: contraseña controlada en `LoginForm` (falla el test de «sin `value=`»).
  - OK necesario: ninguno (frontend en el host).
  - Commits, en este orden:
    1. `feat(frontend): add login form logic`: `sessionState.ts` (`authenticatedResult`, `shouldLeaveAuthForm`, `settleUnexpected`), `SessionProvider.tsx` (`markAuthenticated`), `RegisterPage.tsx` y `registerForm.ts` (`export` de `generalMessage`) pasan a las funciones comunes, y en este mismo commit se borran `registrationResult`, `settleLogout`, `settleRegistration` y `shouldLeaveRegister`; además `loginForm.ts`, `es.ts` y sus tests.
    2. `feat(frontend): add the login page`: `route.ts` y `main.tsx` (`login` y `redirectToLogin`), `AppShell.tsx`, `LoginForm.tsx`, `LoginPage.tsx` y el enlace «¿Ya tienes cuenta? Entra» en `RegistrationForm.tsx`, con sus tests.
  - Hecho cuando: los tests fallan primero y luego pasan; tras cada commit, vitest, build y eslint de los ficheros tocados en verde; tras el primero, los del registro y la salida siguen en verde con las funciones comunes y no queda ningún uso de las cuatro sustituidas; ningún commit deja duplicados ni una ruta `/login` que pinte el mapa; la mutación, en `validation.md`.

- [ ] **T9. Barra superior con «Entrar» y foco tras salir.** RF-7
  - Ficheros: `sessionState.ts` y su test (`TopBarAction` con `"anonymous"`; `logoutResult` con `focus: "login"`); `SessionProvider.tsx` (`FocusRequest.target: "login" | "logout"`); `AppShell.tsx` (`loginRef` y foco a «Entrar»); `frontend/src/app/TopBar.tsx` y `TopBar.test.ts`; `es.ts` (`topBar.login`).
  - Tests (primero; fallan porque `topBarAction` aún devuelve la acción de registro y el foco va a «Registrarse»):
    - `topBarAction`: `"none"` en `unknown`, `"anonymous"` sin sesión y `"logout"` con sesión; `logoutResult` con `focus: "login"` tras salir y en «Salir» si falla.
    - Marcado de `TopBar`: «Entrar» antes de «Registrarse», sus `href`, `btn-secondary` y `btn-primary`, 44 px, sin email; ninguna acción en `unknown`; solo «Salir» con sesión.
  - Pruebas de mecanismo: no aplica (interfaz; plan).
  - OK necesario: ninguno (frontend en el host).
  - Commit: `feat(frontend): show login next to register in the top bar`
  - Hecho cuando: los tests fallan primero y luego pasan; vitest, build y eslint de los ficheros tocados en verde.

- [ ] **T10. Validación en el navegador, arquitectura y cierre.** RF-1…RF-9 y RNF
  - `/sdd-validate` con los revisores en paralelo.
  - Chrome DevTools a 1280 y 375 px (la barra sin sesión, en un navegador real a 375 px), con la consola sin errores propios, un recorrido solo con teclado y a través del proxy de Vite:
    - registrarse con una cuenta `@example.com`, salir, entrar y pulsar «Salir» a continuación (una sola petición de salida, sin `csrf_failed` ni reintento);
    - entrar otra vez, recargar y seguir con sesión; «Atrás» no vuelve al formulario;
    - doble clic y doble Intro en «Entrar»: un solo envío;
    - `/login` con sesión → `/map` sin entrada de historial; `/login/` normalizada; `/login?next=https://otro.sitio` → `/map`; formulario pintado con «quién soy» bloqueado;
    - credenciales incorrectas y, la última, el límite de fallos del par;
    - accesibilidad: controles de 44 px, contraste AA de los textos nuevos, autocompletado, pegar en los campos, foco visible y los anuncios («Entrando…», «Has entrado.» y cada error una vez); foco en «Entrar» tras salir.
  - `docs/architecture.md`: la entrada, sus dos límites, el almacén `login`, `login.py`, la nota de la señal de salida y el árbol del frontend.
  - `MEMORY.md`: la 015 pasa a completada y «Spec activa: ninguna».
  - OK necesario: al empezar la tarea, para los `exec` de pytest y ruff; orden a orden: levantar el stack si está parado; el registro de la cuenta de prueba y cada entrada, que escriben en la BD de desarrollo (cuenta y `last_login`); y, si hay que repetir el límite, el reinicio del backend.
  - Commits, en este orden: `docs(spec-015): validation`, `docs(architecture): describe login`, `docs(memory): close spec 015`; el paso de la spec a «implementada», con la aprobación del desarrollador, en `docs(spec-015): mark spec implemented`, como en la 017 y la 018.
  - Hecho cuando: `validation.md` recorre RF-1 a RF-9 y los no funcionales con su test o su comprobación, reúne las mutaciones de T2 a T6 y T8 y termina con un veredicto; el `git diff` de `requirements*` y `package*.json` respecto de `dev` está vacío.
