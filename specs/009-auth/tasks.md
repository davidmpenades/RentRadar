# Tareas 009 — Registro, sesión y salida
Spec: specs/009-auth/spec.md · Plan: specs/009-auth/plan.md
Máximo 10 tareas: hay 10 (T1 a T9), porque la T5 se partió con la tarea de holgura en T5a (registro, URL, guarda del URLconf y contrato) y T5b («quién soy», salida y contrato). Las del cambio de la clave de sesión, C1 a C3, se numeran aparte.
Cada tarea deja en verde pytest, ruff, la comprobación de migraciones, el desfase de `openapi.json`, vitest, build, eslint de los ficheros tocados y `api:check`. El backend solo se prueba en el contenedor y nunca contra la BD de desarrollo. No hay migraciones.

- [x] **T1. Ajustes de autenticación y base de errores de la API.** RF-2 (validadores), RF-4 y RF-6 (sesión de 14 días), RNF Lista pública sin cambios, Errores
  - `AuthenticationMiddleware` tras `CsrfViewMiddleware`; `AUTH_PASSWORD_VALIDATORS`; `SESSION_COOKIE_AGE`, `SESSION_SAVE_EVERY_REQUEST` y `SESSION_EXPIRE_AT_BROWSER_CLOSE`.
  - En `core/api.py`, los códigos `invalid_fields`, `invalid_request`, `payload_too_large` y `csrf_failed`, con estado por código y `params` con listas.
  - `ApiErrorSerializer` pasa a `core/serializers.py`.
  - Se crea `validation.md`.
  - Toca tests existentes: `apps/core/tests/test_api.py` (conjunto de códigos) y `config/tests/test_http_hardening.py` (política de cookies por entorno).
  - Commit: `feat(core): session auth settings and auth error codes`
  - Hecho cuando: `test_auth_settings.py`, `test_public_list_session.py` y los tests nuevos de `test_api.py` fallan primero y luego pasan; `openapi.json` no cambia al regenerarlo; la suite entera está en verde.
  - Pruebas de mecanismo: `SessionAuthentication` en la vista pública y en los valores por defecto; quitar el middleware; `csrf_failed` con estado 400.
  - Evidencia: `specs/009-auth/validation.md`, sección T1.

- [x] **T2. Servicio de registro con las reglas de contraseña y el sustituto suelto en el email.** RF-1, RF-2
  - `contains_lone_surrogate` en `core/text.py`; `register_user` y `_registration_password_errors`; `_create_account` y `change_user_email` rechazan el email con sustituto suelto con `email_invalid` antes de `full_clean` y de cualquier consulta (regla de la 004, RF-4: vale para `create_user`, `create_superuser`, el registro y el cambio de email); cuatro códigos nuevos.
  - Toca tests existentes: `apps/users/tests/test_services.py` (`PLAN_ERROR_CODES` y los casos del sustituto) y `test_leaks.py` (`register_user`).
  - Commit: `feat(users): registration service with password rules`
  - Hecho cuando: `test_registration_service.py` cubre todos los códigos y su orden, 9, 10, 128 y 129 caracteres (con la trampa de `make_password`), `1234567890`, la contraseña igual al email, los espacios conservados, NUL y sustituto suelto sin error y sin SQL sobre `users_user`, `password_invalid` solo y la carrera con `email_taken`; el email con sustituto suelto en el dominio da `email_invalid` en `register_user`, `create_user`, `create_superuser` y `change_user_email`; el resto del comportamiento de `create_user` no cambia.
  - Pruebas de mecanismo: hash antes de comprobar la longitud; quitar la comprobación de sustitutos (en el alta y en el cambio de email); reordenar los validadores; `password_invalid` no exclusivo; similitud sin usuario.
  - Evidencia: `validation.md`, sección T2.

- [x] **T3. CSRF explícito y lectura acotada del cuerpo.** RF-7, RF-8
  - `apps/core/csrf.py` (`enforce_csrf` y `CsrfEnforcedMixin`); `apps/core/request_body.py` (`read_json_object` y `read_text_fields`); fixture `csrf_client` en `backend/conftest.py`; vistas de prueba en `apps/core/tests`.
  - Toca tests existentes: `apps/core/tests/test_api_import.py` (`MODULES`).
  - Commit: `feat(core): explicit csrf check and bounded json body`
  - Hecho cuando: con `csrf_client`, cada variante sin token válido da 403 `csrf_failed` con `no-store`, sin el motivo y sin leer el cuerpo; un método no admitido da 405; 4096 bytes pasan y 4097 dan 413 (declarado y leído); `Transfer-Encoding` da 413; tipos, listas, JSON inválido, listas anidadas y `RecursionError` simulado dan 400; un cuerpo vacío da `{}`; un objeto anidado en una clave desconocida se acepta (no es un 400).
  - Pruebas de mecanismo: CSRF solo con usuario autenticado; `PermissionDenied`; `CSRFCheck` que acepta siempre; leer el cuerpo antes; CSRF antes de `super().initial()`; quitar `Transfer-Encoding`, la longitud declarada o el `+ 1`; quitar la captura de `RecursionError`; números como texto.
  - Evidencia: `validation.md`, sección T3.

- [x] **T4. Límite de registro por IP con IPv6 por /64.** RF-3
  - `apps/users/throttling.py` (`ip_bucket` y `RegistrationThrottle`).
  - Commit: `feat(users): registration rate limit by ip prefix`
  - Hecho cuando:
    - `ip_bucket` resuelve IPv4, el mismo y otro /64, la IPv4 mapeada, `%eth0`, la vacía y la inválida;
    - con una vista de prueba con el mixin y `timer` falso, 10 pasan y la 11.ª da 429 con `retry_after`;
    - cuentan las inválidas, las 405 y las rechazadas por CSRF, y no las 429;
    - el límite va antes que CSRF y el método;
    - `X-Forwarded-For` se ignora y la ventana se libera.
  - Pruebas de mecanismo: /48 y /128; `X-Forwarded-For`; `AnonRateThrottle`; anotar las del propio límite; no desenvolver la IPv4 mapeada.
  - Evidencia: `validation.md`, sección T4.

- [x] **T5a. Vista de registro, URL, guarda del URLconf y contrato.** RF-1, RF-2, RF-3, RF-4, RF-7, RF-8
  - `apps/users/serializers.py`; `RegisterView` y `public_field_errors` en `apps/users/views.py`; `auth/register/` en `apps/users/urls.py`; `config/urls.py`; guarda del URLconf en `apps/core/tests/test_csrf_guard.py`, desde la primera vista que escribe.
  - Se regeneran `backend/openapi.json` y `frontend/src/api/schema.gen.ts`. Cambio de contrato aprobado por el usuario.
  - Commit: `feat(users): register endpoint`
  - Hecho cuando:
    - los tests de `test_register_api.py`, `test_csrf_guard.py` y los del registro en `test_auth_contract.py` fallan primero y luego pasan: sesión nueva al registrarse (identificador y token CSRF que cambian), registro rechazado sin tocar la sesión, `no-store`, respuestas mínimas, 405 por método, sin `Access-Control-*`, logs sin email ni contraseña, y un objeto anidado en una clave desconocida que sigue a la validación (`email_empty` y `password_required`);
    - sobre el endpoint real, con cada tipo de petición rechazada (sin token, token distinto, `Content-Length` > 4096, `Transfer-Encoding`, JSON inválido, `invalid_fields` y PUT), cada una de las 10 previas da su propio código y nunca 429, la 11.ª, válida, da 429 con `Retry-After` igual a `retry_after` y `no-store`, y al terminar cada caso no hay ninguna cuenta;
    - `spectacular --validate --fail-on-warn`, `npm run api:check` y `npm run build` en verde.
  - Pruebas de mecanismo: quitar `flush()` del registro; `flush()` y `login()` antes de validar; `ModelSerializer`; quitar `no-store`; pasar `is_staff`; quitar el mixin de `RegisterView` (falla el registro sin token y la guarda); `throttle_classes = []`; leer el cuerpo antes de `super().initial()`; CSRF en una clase de autenticación.
  - Evidencia: `validation.md`, sección T5a.

- [x] **T5b. Vistas de «quién soy» y salida, y contrato.** RF-1 («quién soy» tras el registro), RF-5, RF-6, RF-7
  - `CurrentSessionView` y `LogoutView` en `apps/users/views.py`; `auth/session/` y `auth/logout/` en `apps/users/urls.py`. La guarda del URLconf de la T5a cubre `LogoutView` sin tocarla.
  - «Quién soy» rechaza con 405 un método no admitido antes de autenticar: con sesión, `SessionAuthentication` exigiría CSRF y daría 403.
  - Se regeneran `backend/openapi.json` y `frontend/src/api/schema.gen.ts`.
  - Commit: `feat(users): session and logout endpoints`
  - Hecho cuando:
    - los tests de `test_session_api.py`, `test_logout_api.py` y el resto de `test_auth_contract.py` fallan primero y luego pasan: «quién soy» en todos sus casos y tras el registro, sin renovación y con `Vary: Cookie`; POST, PUT y DELETE a «quién soy» con y sin sesión y sin token dan 405 con `Allow: GET, HEAD`; salida con y sin sesión y cookie retirada siempre, también con una sesión caducada, cuya fila desaparece; sin cookie de sesión en la petición, el borrado de la vista lleva Path, Max-Age=0, SameSite y dominio de los ajustes; «quién soy» borra la cookie con una sesión caducada, mal formada o sin fila, y no la toca con una sesión válida o de una cuenta desactivada; `no-store` en todo; respuestas mínimas; la guarda de la T5a pasa con `LogoutView` sin cambios en ella;
    - `spectacular --validate --fail-on-warn`, `npm run api:check` y `npm run build` en verde.
  - Pruebas de mecanismo: quitar `flush()` de la salida; quitar `delete_cookie` (lo detecta la salida sin cookie); `django.contrib.auth.logout()` en vez de `flush()` (equivalente en esta vista, se anota); leer la sesión antes de `flush()`; quitar el mixin de `LogoutView`; quitar el rechazo del método antes de autenticar en «quién soy»; `authentication_classes = []` en «quién soy». `Vary: Cookie` se anota como equivalente.
  - Evidencia: `validation.md`, sección T5b.

- [x] **T6. Cliente de sesión, tiempo máximo común y proxy de Vite.** RF-3 (minutos), RF-6, RF-7, RF-9, RF-10, RF-11, RF-12
  - `src/api/timeout.ts` (extraído); `publicAssets.ts` y `loadStyle.ts` lo usan; `src/api/session.ts`, con «quién soy» a 5 s y registro y salida a 10 s, todos con el mismo helper; `waitMinutes` y `throttledMessage` en `i18n/format.ts`; `vite.config.ts` con el proxy como objeto y `changeOrigin: false`.
  - El proxy corrige la decisión de la T7 de la 006 («sin `changeOrigin`»), que la forma abreviada activaba. Se anota en `validation.md` como desviación de la T7 de la 006 corregida.
  - Toca tests existentes: ninguno; `publicAssets.test.ts` y `loadStyle.test.ts` siguen sin cambios y en verde.
  - Commit: `feat(frontend): session api client with csrf retry`
  - Hecho cuando: vitest cubre la lectura del token en cada envío, un solo reintento tras «quién soy», el error general tras el segundo `csrf_failed`, los 5 s de «quién soy» y los 10 s de registro y salida con temporizador inyectado, el registro vencido que pregunta «quién soy» (con sesión es un éxito, sin ella `failed("timeout")`), la salida vencida que da `failed`, las formas inválidas (también el 201 con forma inválida) y los minutos redondeados; `credentials` es `same-origin` en el cliente de sesión y `omit` en el público.
  - Pruebas de mecanismo: quitar el reintento; reintentar dos veces; guardar el token; `credentials: "omit"`; quitar el tiempo máximo de «quién soy»; quitar el del registro; quitar el de la salida; no preguntar «quién soy» tras un registro vencido.
  - Evidencia: `validation.md`, sección T6, con la nota de la desviación del proxy.

- [x] **T7. Navegación interna, barra superior, estado de sesión y zona de contenido.** RF-9, RF-12
  - `src/app/navigation.ts`, `src/session/sessionState.ts` y `SessionProvider.tsx`, `src/app/AppShell.tsx`, `TopBar.tsx` y `LogoutNotice.tsx`; `main.tsx`; `MapPage` (`h-full`) y `NotFoundPage` (`min-h-full`); textos en `es.ts`.
  - La marca de la barra es un enlace a `/map`. El fallo de «Salir», o su tiempo vencido, muestra un aviso visible bajo la barra con «Reintentar».
  - Commit: `feat(frontend): top bar with session state and page navigation`
  - Hecho cuando: vitest de `createNavigator`, `isPlainLeftClick`, `topBarAction` y `logoutResult` (éxito, fallo y tiempo vencido), y el marcado de `TopBar` con la marca como enlace a `/map`, sin email y sin acciones en `unknown`, y el de `LogoutNotice` con su botón «Reintentar»; build y eslint en verde; en el navegador a 375 px, la barra y el mapa caben sin scroll de página.
  - Pruebas de mecanismo: no aplica (interfaz).
  - Evidencia: comprobación en T9.

- [x] **T8. Página de registro.** RF-10, RF-11, RF-13
  - `route.ts` (`register` y `redirectToRegister`); `src/register/registerForm.ts`; `src/pages/RegisterPage.tsx`; mensajes de los códigos y del tiempo vencido en `es.ts`.
  - Con un fallo o un tiempo vencido, el error es general, el envío vuelve a habilitarse para reintentar y el email y la contraseña se conservan; la contraseña solo se borra si el resultado trae un error de la contraseña.
  - También `main.tsx`, `app/AppShell.tsx`, `styles/index.css` (token `--color-danger`) y `register/RegistrationForm.tsx` (solo marcado).
  - Toca tests existentes: `frontend/src/app/route.test.ts`, al que se añaden casos.
  - Commits: `feat(frontend): registration form logic` (`registerForm.ts`, su test y `es.ts`) y `feat(frontend): registration page and route` (ruta, `main.tsx`, `AppShell.tsx`, `RegistrationForm.tsx`, `RegisterPage.tsx`, `index.css` y el registro de la tarea en `validation.md`).
  - Hecho cuando: vitest de `resolveRoute` (`/register`, `/register/`, `/register//`, `/REGISTER`), `emptyFieldErrors`, `fieldMessages` (un texto por código), `firstFocusTarget`, `formStateAfter` (un test por caso: contraseña borrada solo con un error de `password` y conservada en el resto, también con `failed("timeout")`; mensaje general y envío habilitado), `createSubmitGuard` y `shouldLeaveRegister`; marcado del formulario con etiquetas, `autoComplete`, «Mostrar contraseña» y la contraseña sin `value=`; build y eslint en verde.
  - Pruebas de mecanismo (privacidad de la contraseña y doble envío): quitar la comprobación de `tryStart` (falla el test de la guarda) y volver a hacer controlado el campo de contraseña (falla el test de marcado sin `value=`).
  - Evidencia: `validation.md`, sección T8 (tests y mutaciones); la comprobación en el navegador, en T9.

- [x] **T9. Validación en el navegador, arquitectura y cierre.** RF-1…RF-13
  - Chrome DevTools a 1280 y 375 px, con la consola sin errores propios (los 4xx esperados se anotan) y un recorrido solo con teclado:
    - registrarse, ver «Salir», recargar y seguir con sesión, salir;
    - la marca de la barra lleva a `/map`;
    - email repetido y contraseña débil;
    - «quién soy» bloqueado;
    - registro que no responde (`fetch` simulado que no resuelve): a los 10 s, error general y reintento;
    - «Salir» que falla o no responde: aviso visible con «Reintentar» y foco en «Salir»;
    - `/register` con sesión y `/register/`;
    - «Atrás» tras registrarse;
    - el mapa vuelve a su vista inicial;
    - límite superado, el último.
  - Se comprueba que el registro funciona a través del proxy de Vite sin `CSRF_TRUSTED_ORIGINS` y que Django recibe `Host: localhost:5173`. Se anota en `validation.md` como desviación de la T7 de la 006 corregida.
  - Cada registro de una cuenta de prueba en la BD de desarrollo necesita una autorización expresa en ese momento y usa `@example.com`. El contador se reinicia con `docker compose restart backend`.
  - curl contra `runserver`: cuerpo troceado → 413; cabeceras y cookies de las tres operaciones.
  - Se actualiza `docs/architecture.md` y se propone pasar la spec a «implementada».
  - Commit: `docs(spec-009): browser validation and architecture`
  - Hecho cuando: `validation.md` recorre RF-1 a RF-13 y los no funcionales con su test o su comprobación, reúne las mutaciones de T1 a T6 y termina con un veredicto; el `git diff` de `requirements*` y `package*.json` está vacío.

## Cambio: clave de sesión
Cambio posterior a la implementación (RF-14), con su plan en «Cambio: clave de sesión (RF-14)» de `plan.md`. Sus tareas se numeran aparte de T1 a T9. Cada una deja en verde lo mismo que las anteriores; sin migraciones, y `openapi.json` y el frontend no cambian. Los números de línea citados son los de 37cadc9.

- [x] **C1. Clave sin fila bien formada y compartida.** RF-14 (preparación), RF-5, RF-6
  - Solo tests, con todo en verde, antes de cualquier rojo.
  - `KEY_WITHOUT_ROW = "0123456789abcdefghijklmnopqrstuv"` en `apps/core/tests/helpers.py`, que se crea, con el comentario «Bien formada (32 caracteres de a-z y 0-9) y sin fila en la BD». Lo importan `test_session_api.py`, `test_logout_api.py` y `test_login_api.py`, que pierden su definición (l.23-24, 31-32 y 57-58).
  - `test_the_key_without_row_is_well_formed_and_has_no_row` en `test_session_api.py`: `re.fullmatch` y ninguna fila.
  - Ids `shorter-than-8` → `too-short` (`test_session_api.py:96` y `:115`, `test_logout_api.py:171`). El comentario de `test_session_api.py:77` pasa a «Mal formada: más corta que una clave de sesión».
  - Ningún otro valor de cookie cambia (clasificación por intención en el blast radius del cambio, en `plan.md`).
  - Commit: `test(users): share a well-formed session key without row`
  - Hecho cuando: toda la suite, ruff y la comprobación de migraciones están en verde; `KEY_WITHOUT_ROW` se define solo en `apps/core/tests/helpers.py`; el número de tests recogidos sube en uno (el de la precondición); el diff solo toca `apps/core/tests/helpers.py` (nuevo) y los tres ficheros de test.

- [ ] **C2. Motor de sesión que ignora las claves mal formadas.** RF-14, RF-1, RF-2, RF-5, RF-6, RF-7, RNF Lista pública sin cambios
  - Primero los tests:
    - en `apps/core/tests/helpers.py`, `OCTAL_NULL` (traído de `test_login_api.py:55-56`), `raw_cookie_header`, `MALFORMED_SESSION_VALUES` y `session_queries_with`;
    - los de las cuatro operaciones (`test_register_api.py`, `test_login_api.py`, `test_logout_api.py` y `test_session_api.py`), con la inversión de `test_a_session_cookie_with_null_characters_gives_a_server_error_on_success` (`test_login_api.py:423-439`) y un contrapeso con `KEY_WITHOUT_ROW` por operación;
    - `apps/core/tests/test_session_store.py` y los dos de `config/tests/test_auth_settings.py`;
    - la guarda de `test_public_list_session.py`: `fetch_with_cookie` (l.35-40) con `raw_cookie_header` y la cookie de nulos con ids en la l.119;
    - la guarda de `test_public_list_api.py`: `MALFORMED_COOKIES` (l.677-681) gana `null-characters` y `set_cookies` (l.684-686) manda la cabecera en bruto con `client.defaults["HTTP_COOKIE"]`, comprobado antes de añadir el id.
  - Después `apps/core/session_store.py`, `SESSION_ENGINE = "apps.core.session_store"` en `config/settings/base.py` y `MODULES` en `apps/core/tests/test_api_import.py`.
  - `docs/architecture.md`: estructura (`session_store.py` junto a `middleware.py`, l.31), l.92, l.96 y la lista de internos de la l.110 (`_validate_session_key`, el setter de `_session_key` y la condición de borrado de `SessionMiddleware.process_response`, con la nota de `SessionBase.__bool__` en 6.1).
  - Commit: `fix(core): treat malformed session keys as no session`
  - Hecho cuando:
    - antes del código, los tests nuevos fallan por la razón esperada de la estrategia de tests de `plan.md`:
      - Ids `null-characters` de los cuatro tests `..._is_ignored_when_...`: 500, porque PostgreSQL rechaza el nulo. En el registro, la entrada y la salida lo provoca el `DELETE` de `flush()`; en «quién soy», el `SELECT` de `load()`.
      - Resto de ids de esos cuatro tests: hay una consulta a `django_session` con el valor.
      - `..._removes_a_malformed_session_cookie` y `..._without_a_token_...`, todos los ids: la cookie no se retira, porque la sesión no está vacía.
      - `test_session_store.py`: al recogerlo falla el import de `apps.core.session_store` (`ModuleNotFoundError`). Es un error de colección y pytest interrumpe toda la ejecución, así que el rojo se registra en dos ejecuciones: la suite sin ese fichero (`--ignore`), con los fallos de esta lista y su motivo, y ese fichero solo, con el `ModuleNotFoundError` esperado.
      - Tests de ajustes: fallan porque el motor es el de Django. Comparan por nombre, sin importar `apps.core.session_store` de forma directa: `settings.SESSION_ENGINE == "apps.core.session_store"`, `import_module(settings.SESSION_ENGINE).SessionStore.__module__ == "apps.core.session_store"` y, tras `force_login`, `type(client.session).__module__ == "apps.core.session_store"`.
      - Contrapesos y guardas de la lista pública: pasan antes y después del código.
    - después, pasan toda la suite, ruff y `config/tests/test_migrations.py`; `manage.py check` no da avisos; regenerar `backend/openapi.json` no produce diferencias; el `git diff` de `frontend/`, `requirements*` y las migraciones está vacío.

- [ ] **C3. Mutaciones, comprobación de punta a punta y cierre.** RF-14
  - `validation.md`, sección «Cambio: clave de sesión (RF-14)»: C1 y C2 (tests que fallaron primero y recuentos), y la nota de que `Client.session` y `force_login` con una cookie mal formada no consultan la BD.
  - Mutaciones, cada una con su lista exacta escrita en `validation.md` antes de ejecutarla, sobre una copia y con el sha256 antes y después: «quitar la comprobación de la forma» (los 63 fallos de la estrategia de tests de `plan.md`) y M1, M2, M2b, M3a, M3b, M4 y M5. La de M5 incluye los ids `null-characters` de las dos guardas de la lista pública.
  - Navegador, a 1280 y 375 px, a través del proxy de Vite:
    - con `sessionid="\000\000\000\000\000\000\000\000"` puesta con `document.cookie`, `/map` carga con «Entrar» y «Registrarse», sin errores en la consola, y la respuesta de «quién soy» retira la cookie;
    - con la cookie puesta otra vez, un POST real a `/api/v1/auth/logout/` desde la página, con `X-CSRFToken`, responde 204 con `Set-Cookie: sessionid=""; Max-Age=0`, y `document.cookie` queda sin `sessionid`.
  - Ninguna respuesta trae una `sessionid` nueva: la primera de «quién soy» y la de la salida la retiran (`Max-Age=0`), y la de la lista pública no lleva cookies. Que no se crean ni borran filas de `django_session` lo prueban los tests de C2 en la BD de test. Si el stack no está levantado, se pregunta antes.
  - Punto 7 de «Cambios en otras specs» en `specs/015-login/spec.md:165`.
  - `MEMORY.md`: se quita el primer punto de «Próximos pasos», avanza la hoja de ruta y se anota que `SimpleCookie` rechaza los caracteres de control, así que los tests mandan la cookie en bruto.
  - Commit: `docs(spec-009): validate malformed session cookie change`
  - Hecho cuando: cada mutación da exactamente la lista escrita, o la diferencia queda explicada; el sha256 es idéntico antes y después de cada mutación; la comprobación en el navegador queda registrada a 375 y 1280 px; el riesgo «Cookie de sesión con nulos» de la 015 dice el texto del punto 7; la validación termina con un veredicto sobre RF-14 y se propone devolver la spec a «implementada».
