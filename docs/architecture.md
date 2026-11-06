# Arquitectura

## Estructura
```
backend/
├── manage.py              # Resuelve DJANGO_ENV antes de cargar Django
├── docker-entrypoint.sh   # Espera a la BD (wait_for_db) y ejecuta la orden del contenedor
├── conftest.py            # Guarda de la BD de test y fixtures: bloqueo de la red y csrf_client (exige CSRF)
├── config/
│   ├── env.py             # Único lector de os.environ; valida sin mostrar valores
│   ├── log_redaction.py   # Formatter que tapa secretos en los logs de producción
│   ├── settings/
│   │   ├── base.py        # Común y seguro por defecto (DEBUG=False, UTC, es)
│   │   ├── development.py # DEBUG según DJANGO_DEBUG; BD desde el entorno
│   │   ├── test.py        # DEBUG siempre apagado; BD rentradar_test
│   │   └── production.py  # Rechaza la configuración insegura
│   ├── urls.py
│   ├── wsgi.py / asgi.py  # Mismo resolvedor que manage.py
│   └── tests/
└── apps/                  # Una carpeta por app: core y las de dominio
    ├── core/
    │   ├── db_wait.py     # Espera a la BD con reloj y pausa inyectados
    │   ├── text.py        # Detección de caracteres de control y de sustitutos Unicode sueltos, y su validador de Django
    │   ├── errors.py      # Error de dominio (solo campos y códigos) y traducción de errores de Django
    │   ├── db.py          # run_guarded: guardado protegido que traduce las restricciones de la BD a códigos
    │   ├── api.py         # ApiError, códigos de error de la API con su estado HTTP y manejador de excepciones de DRF (formato único)
    │   ├── serializers.py # ApiErrorSerializer: el componente ApiError de la descripción de la API
    │   ├── csrf.py        # enforce_csrf y CsrfEnforcedMixin: CSRF explícito para vistas anónimas
    │   ├── request_body.py # read_json_object (cuerpo JSON acotado en bytes) y read_text_fields
    │   ├── negotiation.py # Negociación de contenido que siempre elige JSON y no importa rest_framework.views
    │   ├── middleware.py  # mark_response_cookieless y el middleware que limpia las cookies de las respuestas marcadas
    │   ├── management/commands/wait_for_db.py
    │   └── migrations/    # 0001 declara la extensión PostGIS (necesaria en BD gestionadas)
    ├── users/             # Usuario identificado por email
    │   ├── models.py      # User y su gestor (normaliza el email y delega el alta en el servicio)
    │   ├── services.py    # Alta de usuarios y superusuarios, registro (register_user y reglas de contraseña), cambio de email
    │   ├── throttling.py  # ip_bucket (IPv6 por /64) y RegistrationThrottle: límite de registro por IP
    │   ├── serializers.py # Lista blanca de la sesión (solo el email) y esquemas de la documentación del registro
    │   ├── views.py       # RegisterView, CurrentSessionView («quién soy») y LogoutView
    │   └── urls.py        # auth/register/, auth/session/ y auth/logout/, montadas bajo api/v1/ en config/urls.py
    ├── categories/        # Lista cerrada de categorías
    │   ├── models.py      # Category y la normalización de su nombre
    │   ├── services.py    # save_category: valida, normaliza y guarda
    │   └── migrations/    # 0002 siembra las once categorías
    ├── assets/            # Bienes en alquiler y privacidad de su ubicación
    │   ├── location.py    # Función de aproximación (pura): centro de la celda de la cuadrícula
    │   ├── rules.py       # Reglas de los campos (puras): texto, precio, radio, estado, coordenadas
    │   ├── zone.py        # parse_zone (puro): valida los cuatro límites de la zona y devuelve Zone o ZoneError
    │   ├── selectors.py   # visible_assets_in_zone: bienes visibles de una zona, solo con campos públicos
    │   ├── models.py      # Asset: ubicación exacta y pública en campos separados, CHECK con nombre
    │   ├── services.py    # create_asset y update_asset: única vía de escritura de bienes
    │   ├── serializers.py # Forma JSON de la lista pública (diez campos) y esquemas de respuesta de la documentación
    │   ├── views.py       # PublicAssetListView y PublicListThrottle: la lista pública, sin sesión y con límite
    │   ├── urls.py        # Ruta public/assets/, montada bajo api/v1/ en config/urls.py
    │   ├── demo.py        # Datos puros de los 25 bienes de demostración (no importa el modelo)
    │   ├── management/commands/create_demo_assets.py  # Comando de demostración: solo en development y test, en una transacción
    │   └── migrations/    # 0001 depende de categories.0001, no de la semilla
    └── <app>/
        ├── models.py
        ├── services.py    # Escrituras y reglas de negocio
        ├── selectors.py   # Lecturas (querysets con select_related, annotate…)
        ├── serializers.py # Solo traducen entre JSON y Python
        ├── views.py       # Solo traducen entre HTTP y servicios/selectores
        ├── migrations/
        └── tests/
```

## Selección de entorno
`DJANGO_ENV` (`development`, `test` o `production`) decide el módulo de settings. `manage.py`, `wsgi.py` y `asgi.py` llaman a `configure_settings_module()`, que siempre sobrescribe `DJANGO_SETTINGS_MODULE`. Un valor distinto de los tres impide arrancar. pytest usa siempre `config.settings.test` (`--ds` en `pyproject.toml`).

## Capas
Las vistas y los serializers no contienen reglas de negocio ni hacen consultas propias: las escrituras van en `services.py` y las lecturas en `selectors.py`. Los tests de cada app viven en `apps/<app>/tests/`; los de configuración, en `config/tests/`.

## Errores de dominio
Los servicios no devuelven los errores de Django tal cual: los traducen a `DomainValidationError`, una subclase de `ValidationError` que solo contiene campos y códigos estables en inglés (`email_taken`, `name_too_long`…), nunca el valor recibido ni sus parámetros. Cada servicio expone sus códigos como constantes, y un test compara el conjunto con la tabla del plan.
- `translate_validation_error` convierte cada par (campo, código de Django) en un par (campo, código de dominio); lo que no está en el mapa pasa a `validation_failed`. El campo de destino puede ser otro: la violación de una restricción de unicidad con `Lower` llega en `__all__` y se coloca en su campo.
- `run_guarded(write, constraint_codes)` (en `core/db.py`) ejecuta el bloque entero dentro de un `atomic`, captura el `IntegrityError` fuera de él, lee el nombre de la restricción (`diag.constraint_name`, sin leer el mensaje, que lleva el valor) y devuelve `(resultado, códigos)`. El servicio lanza el error de dominio fuera de cualquier `except`, de modo que no queda encadenado al error original. Lo usan users, categories y assets.
- Antes de salir del bloque ejecuta `SET CONSTRAINTS ALL IMMEDIATE` y después `ALL DEFERRED`: una clave foránea violada salta dentro del `try` y se traduce, en lugar de saltar en el `COMMIT` de una transacción exterior, y las restricciones quedan diferidas sea cual sea el modo con el que se entró. Si el bloque falla, el savepoint restaura el modo de entrada.
- Un `DomainValidationError` lanzado dentro de `write` deshace el `atomic` y sale tal cual; un `DatabaseError` que no es de integridad se propaga.
- Una restricción desconocida o sin nombre (un `NOT NULL`) da `constraint_violated`.

## Ubicación de los bienes
- Cada bien guarda dos ubicaciones en campos `geography` separados. La exacta es privada. La pública es la única que se muestra o se usa para buscar, y se deriva de la exacta y del radio de privacidad (500, 1000 o 2000 m).
- `approximate_location` proyecta la coordenada a EPSG:3035, localiza la celda cuadrada de lado igual al radio (los bordes inferior e izquierdo pertenecen a la celda) y devuelve su centro en latitud y longitud, a 6 decimales. No consulta la BD ni la red, y crea las referencias espaciales en cada llamada porque GDAL no es seguro entre hilos. Cambiar la proyección o el origen movería todas las celdas ya publicadas.
- `create_asset` y `update_asset` son las únicas funciones que escriben bienes, y solo `services.py` obtiene `Asset` y `approximate_location` (lo vigila un test por AST). No admiten una ubicación pública ni un propietario nuevo: fallan con un `TypeError`. La hora entra como parámetro. Fuera de `apps/assets`, el servicio solo se usa importando por nombre esas dos funciones y nadie llega a la app por `get_app_config("assets")`; otro test por AST lo vigila.
- `update_asset` bloquea la fila con `select_for_update` como primera lectura del bien, compara con el estado guardado y escribe solo las columnas que cambian. Con el bien activo no deja cambiar la ubicación exacta ni el radio.
- Las FK de `owner` y `category` son `PROTECT` y sin `related_name`: borrar un usuario o una categoría con bienes se rechaza, también al revertir la semilla de categorías.
- Ni los errores, ni `str()` ni `repr()` ni los logs contienen coordenadas. `test_leaks.py` lo comprueba con coordenadas centinela en 22 formas.

## API pública
La lista pública (`GET|HEAD /api/v1/public/assets/`) no autentica al visitante ni toca la sesión: `authentication_classes` está vacío y la respuesta no depende de cookies ni de cabeceras. El límite de peticiones (`PublicListThrottle`) se aplica antes de comprobar el método y de validar la zona, y cuenta por `REMOTE_ADDR` (`NUM_PROXIES = 0`). Todas las respuestas de la vista, errores incluidos, llevan la marca de `mark_response_cookieless` y salen sin cookies. Los errores salen con `Cache-Control: no-store`, y solo el 200 es cacheable. El módulo de negociación no importa `rest_framework.views`: DRF resuelve esa clase al importar la vista. Aunque exista el middleware de autenticación, la vista sigue sin leer la sesión: un test cuenta sus consultas y exige que ninguna toque `django_session`, también con una cookie de sesión válida, caducada o mal formada.

## Autenticación y sesión
Registro, «quién soy» y salida (`/api/v1/auth/register/`, `/session/` y `/logout/`, en `apps/users`). La autenticación es la sesión de Django con CSRF, en el mismo origen que la página; JWT y la aplicación móvil quedan fuera por ahora.
- **Sesión**: motor de BD de `django.contrib.sessions`. La cookie es `HttpOnly` y `SameSite=Lax` (y `Secure` en producción), y caduca a los 14 días fijos: `SESSION_SAVE_EVERY_REQUEST` está apagado y la actividad no la renueva. Una sesión es válida si existe, no ha caducado y su cuenta está activa.
- **Middleware y autenticación por vista**: `AuthenticationMiddleware` va justo después de `CsrfViewMiddleware`, pero `DEFAULT_AUTHENTICATION_CLASSES` sigue vacío: cada vista declara la suya. Solo «quién soy» usa `SessionAuthentication`; el registro, la salida y la lista pública no leen la sesión al autenticar.
- **CSRF de doble envío**: la cookie `csrftoken` es legible por la página y la petición debe repetirla en la cabecera `X-CSRFToken`. El token no está ligado a la sesión; lo que se garantiza es que cambia al abrir una sesión. «Quién soy» lo deja en la cookie con `get_token`.
- **CSRF explícito en vistas anónimas** (`core/csrf.py`): DRF marca sus vistas como exentas y su autenticación por sesión solo comprueba el token a quien ya está autenticado, así que el registro y la salida, que son anónimos, heredan `CsrfEnforcedMixin`. Este ejecuta `CSRFCheck` sobre el `HttpRequest` de Django con `POST` vacío, en `initial()` y para los métodos no seguros que la vista admite, y lanza `csrf_failed` (403, distinto de `forbidden`) sin el motivo. Un test recorre el URLconf y exige el mixin a toda vista con un método no seguro: si se monta el admin o una `ViewSet`, esa guarda falla y hay que decidir.
- **Cuerpo acotado** (`core/request_body.py`): `read_json_object` lee como mucho 4096 bytes (más uno, para detectar el exceso), rechaza `Transfer-Encoding` y una longitud declarada mayor con `payload_too_large` (413), y todo lo que no sea un objeto JSON con `invalid_request` (400). `read_text_fields` exige texto o nulo en cada campo. Estas vistas no usan `request.data` ni `request.body`.
- **Límite de registro** (`users/throttling.py`): `RegistrationThrottle` (un `SimpleRateThrottle`) permite 10 peticiones por hora y por IP, la de la conexión (`NUM_PROXIES = 0`). `ip_bucket` agrupa las direcciones IPv6 por su prefijo /64, desenvuelve las IPv4 mapeadas y manda las vacías o no válidas a un cubo fijo. Solo anota las peticiones que deja pasar: las que rechaza él mismo no cuentan, y DRF no devuelve `retry_after` si el historial pasara de 10. Los contadores viven en la caché por defecto, en memoria y por proceso, hasta la spec de despliegue.
- **Orden de comprobaciones del registro**: límite → método → CSRF → tamaño y forma del cuerpo → validación → creación. La salida va método → CSRF. Con el límite superado, cualquier método del registro recibe el error de límite.
- **Registro**: `register_user` (servicio) valida el email y la contraseña con las reglas de la 004 más los validadores de contraseña de Django, en el orden fijo de `AUTH_PASSWORD_VALIDATORS` y con un máximo de 128 caracteres que se comprueba sin calcular el hash. Una contraseña con un nulo o un sustituto suelto da `password_invalid`, sola. La vista abre la sesión dentro de una transacción: crea la cuenta, `flush()` de la sesión anterior y `login()`, de modo que cambian el identificador y el token CSRF aunque fuera la misma cuenta. Un registro rechazado no toca la sesión.
- **Salida y «quién soy»**: la salida hace `flush()` (borra la fila aunque esté caducada) y retira siempre la cookie de sesión; sin sesión responde bien y no cambia nada. «Quién soy» responde `{"user": null}` sin error cuando no hay sesión válida, para que una visita anónima no deje errores en la consola, y rechaza con 405 un método no admitido antes de autenticar.
- **Respuestas**: las de éxito llevan solo el email de la propia cuenta o `null`, y todas, errores incluidos, `Cache-Control: no-store`; la de «quién soy» declara además `Vary: Cookie`. Los errores usan el formato único (`code`, `params`, `retry_after`) con los códigos `invalid_fields`, `invalid_request`, `payload_too_large` y `csrf_failed`, y nunca incluyen el valor recibido.

## Logs
`django.db.backends` está fijado en INFO en los tres entornos (en producción, con el handler que redacta secretos): con DEBUG, Django registra cada consulta con sus valores, entre ellos el email y el hash.

## Arranque y aislamiento de tests
El `ENTRYPOINT` del contenedor ejecuta `wait_for_db`, que reintenta la conexión hasta 60 s y, si no llega, falla con un mensaje fijo sin credenciales. Durante los tests, un fixture autouse de `backend/conftest.py` bloquea los sockets de internet (libpq y los sockets AF_UNIX siguen funcionando; el loopback TCP, 127.0.0.1 y ::1, también queda bloqueado) y una guarda aborta la sesión si la BD de test no contiene `test` o coincide con `DB_NAME`.

## Frontend
Vive en `frontend/` (React, TypeScript, Vite y Tailwind v4) y corre en el host, no en Docker. Las versiones están fijadas con `save-exact` y `package-lock.json` está en git; se instala con `npm ci --ignore-scripts`.

```
frontend/
├── index.html
├── vite.config.ts      # Proxy de /api (objeto con changeOrigin: false), puerto 5173 y configuración de vitest (entorno node)
├── eslint.config.js    # Incluye no-restricted-syntax contra dangerouslySetInnerHTML, innerHTML y setHTML
├── .env.example        # VITE_MAP_STYLE_URL: estilo del mapa base (https)
└── src/
    ├── main.tsx        # Monta la aplicación (StrictMode, SessionProvider y AppShell) y normaliza las direcciones con replaceState
    ├── styles/         # index.css: Tailwind, tokens de @theme (también --color-danger), foco global y tipografía autoalojada
    ├── i18n/           # es.ts: catálogo de mensajes en castellano · format.ts: precios, radios y minutos de espera
    ├── assets/categories/  # Ilustraciones SVG de las categorías
    ├── api/            # Clientes HTTP y validación de lo que llega
    │   ├── schema.gen.ts    # Tipos generados desde backend/openapi.json (no se edita a mano)
    │   ├── validate.ts      # Esquema Zod estricto de la lista pública y validateResponse
    │   ├── publicAssets.ts  # Cliente de la lista pública (sin cookies) y clasificación de sus fallos
    │   ├── session.ts       # Cliente de sesión (cookies del mismo origen): «quién soy» (5 s), registro y salida (10 s), con un reintento ante csrf_failed y esquemas Zod
    │   ├── timeout.ts       # runWithTimeout: el tiempo máximo común de todos los clientes
    │   └── http.ts          # hasJsonContentType
    ├── app/            # Cáscara de la aplicación
    │   ├── AppShell.tsx     # Columna con la barra, la zona de contenido y la región de estado global; el foco va a la zona al cambiar de página
    │   ├── TopBar.tsx       # Barra de 56 px: la marca (enlace a /map) y «Registrarse» o «Salir»
    │   ├── LogoutNotice.tsx # Aviso de fallo de «Salir», con «Reintentar»
    │   ├── NotFoundPage.tsx # «Página no encontrada», con desplazamiento propio
    │   ├── navigation.ts    # createNavigator: History API (pushState, replaceState y popstate) sin librería de rutas
    │   └── route.ts         # resolveRoute: de la dirección a la ruta (/map, /register, redirecciones y no encontrada)
    ├── session/        # Estado de la sesión
    │   ├── sessionState.ts      # Lógica pura: estado (desconocido, sin sesión, con sesión), acción de la barra y resultado de la salida
    │   └── SessionProvider.tsx  # Contexto: «quién soy» al montar, salida y registro
    ├── register/       # Página de registro
    │   ├── registerForm.ts      # Lógica pura: errores por campo, foco, estado tras el resultado y guarda del doble envío
    │   └── RegistrationForm.tsx # Solo marcado (probado con react-dom/server); la contraseña no tiene valor en el DOM
    ├── pages/          # MapPage.tsx (mapa y panel) y RegisterPage.tsx (estado, sesión, guarda y foco del formulario)
    ├── map/            # Mapa MapLibre
    │   ├── MapView.tsx      # Crea y libera el mapa, la capa de círculos y los controles
    │   ├── style.ts         # Validación del estilo y de las URL permitidas, atribución fija
    │   ├── loadStyle.ts     # Descarga del estilo con tiempo máximo
    │   ├── loadAssets.ts    # Petición de los bienes de la vista
    │   ├── requestBox.ts    # Caja de petición a partir de los límites visibles
    │   ├── scheduler.ts     # Retardo y cancelación de las peticiones al mover el mapa
    │   ├── viewport.ts      # Vista inicial y su comprobación con tolerancia
    │   ├── circles.ts       # Círculos únicos y su colección GeoJSON
    │   └── geodesy.ts       # Distancias y puntos sobre la esfera
    ├── panel/          # Panel de resultados: ResultsPanel.tsx, AssetCard.tsx, header.ts (textos de cabecera y estado) y categoryImage.ts
    └── state/          # viewState.ts: estado de la petición y de la vista (cargando, resultados, vacío, acercar el mapa y errores)
```

- **Contrato de la API**: `backend/openapi.json` es la descripción versionada de la API (no se sirve por HTTP). Se genera con `docker compose run --rm -T --no-deps --entrypoint "" -u "$(id -u)" backend python manage.py spectacular --format openapi-json --file openapi.json --validate --fail-on-warn --lang en`. De ella salen los tipos con `npm run api:gen`, y `validateResponse` valida en ejecución cada respuesta con Zod y devuelve el tipo generado. Un test compara las claves del esquema con las del `openapi.json`. Si el esquema dejase de caber en el tipo generado, el build no compilaría. El cliente de sesión valida igual cada respuesta, con esquemas `z.strictObject` propios comprobados en compilación frente a los tipos generados.
- **Mismo origen**: en desarrollo el navegador solo habla con `localhost:5173`; Vite reenvía `/api` a `http://localhost:8000` con `changeOrigin: false`, escrito como objeto porque la forma abreviada lo activaría. Así Django recibe `Host: localhost:5173`, el `Origin` de los POST coincide con él y no hace falta `CSRF_TRUSTED_ORIGINS`. La API no emite cabeceras CORS: las `Access-Control-Allow-Origin` que se ven en desarrollo las añade el servidor de Vite para los orígenes `localhost`.
- **Lógica pura y componentes finos**: las reglas (sesión, formulario, navegación, tiempos máximos, peticiones) viven en funciones de `.ts` con sus dependencias inyectadas (`fetch`, temporizadores, historial), que vitest prueba en `node`. Los componentes solo pintan y conectan; los de solo marcado se prueban con `react-dom/server`. jsdom no calcula layout, así que el desbordamiento, el responsive y el foco real se verifican en el navegador.
- **Navegación propia**: `createNavigator` usa la History API, sin librería de rutas. `pushState` no emite `popstate`, así que notifica a mano; las redirecciones usan `replaceState` y no añaden entradas al historial.
- **Barra y zona de contenido**: columna `h-dvh` con la barra de 56 px (`shrink-0`) y la zona (`min-h-0 flex-1`), de modo que las páginas ocupan la zona con `h-full` y la página nunca hace scroll. La zona recibe el foco por código al cambiar de página y no dibuja contorno (`outline-none!`: la regla global `:focus-visible` no va en una capa de Tailwind y solo le gana una utilidad importante).
- **Contraseña fuera del DOM**: el campo es no controlado y se lee de un `ref` al enviar, porque React copia el valor de un campo controlado al atributo `value`, también en `type="password"`.
- **Tiempos máximos y errores de red**: todos los clientes pasan por `runWithTimeout`. Con el backend parado, el proxy de Vite responde 502 `text/plain` sin cuerpo, así que el registro da el error de servidor y «quién soy» da sin sesión; el error de red solo aparece si cae el propio Vite o falla la conexión del navegador.
- **Comandos** (desde `frontend/`): `npm run dev`, `npx vitest run`, `npm run build`, `npx eslint .`, `npm run api:gen` y `npm run api:check`.
- **Puertas de CI**: el backend regenera la descripción en `/tmp` y la compara con `backend/openapi.json` con `diff`; el job `frontend-quality` ejecuta vitest, build, eslint, `api:check` (los tipos generados corresponden al `openapi.json`) y `npm audit --omit=dev`.
