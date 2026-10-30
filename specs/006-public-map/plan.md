# Plan 006 — Mapa público: ver los bienes
Spec: specs/006-public-map/spec.md (aprobada)

## Resumen
- Entrega:
  - la lectura pública versionada `GET|HEAD /api/v1/public/assets/`, con caché pública de 60 s, límite de 60 peticiones por minuto e IP, formato único en sus errores y respuesta idéntica para cualquier visitante;
  - el identificador público UUID v4, con su migración en tres ficheros;
  - el comando de demostración;
  - la descripción OpenAPI versionada en el repositorio;
  - la interfaz `frontend/` (Vite, React, TypeScript, Tailwind v4), con tipos generados, validación Zod, mapa MapLibre con círculos geodésicos, panel con la lista, estados de vacío y error, y la página «Página no encontrada».
- Nota: la spec se partió por profundidad. La interacción entre lista y mapa (agrupación, selección, filtro por círculo con «Ver todos», Escape y alturas del panel) pasa a la spec 007 y no entra en este plan.
- Fuera de este plan, como dice la spec:
  - handlers de Django y `no-store` fuera de la lista: 011;
  - redirección por barra final de la API: 011;
  - página de depuración sin coordenadas: 010.

## Archivos y responsabilidades
| Archivo | Crea/Modifica | Responsabilidad | RF |
|---|---|---|---|
| backend/requirements.in, requirements.txt | M | DRF y drf-spectacular con versión exacta y hashes (todas las ruedas: x86_64 y aarch64) | RNF Dependencias |
| backend/config/settings/base.py | M | `rest_framework` y `drf_spectacular` en INSTALLED_APPS; REST_FRAMEWORK; SPECTACULAR_SETTINGS; middleware de cookies el primero de MIDDLEWARE | RF-5, RNF |
| backend/config/settings/{development,test,production}.py | M | Constante `ENVIRONMENT` | RF-7 |
| backend/config/urls.py | M | `path("api/v1/", include("apps.assets.urls"))` (sin handlers) | RF-1 |
| backend/apps/core/api.py | C | Negociación fija a JSON; `ApiError` (código y parámetros); manejador de excepciones de DRF con formato único y `no-store`; tabla de códigos | RF-3, RF-5, RNF Errores |
| backend/apps/core/middleware.py | C | `mark_response_cookieless(response)` y `CleanMarkedResponseMiddleware`: solo una respuesta marcada expresamente sale sin `Set-Cookie` y sin `Cookie` en `Vary`; una sin marcar conserva sus cookies | RNF Respuesta idéntica |
| backend/apps/assets/models.py | M | `public_id = UUIDField(default=uuid.uuid4, editable=False, unique=True)` | RF-2 |
| backend/apps/assets/migrations/0002_…, 0003_…, 0004_… | C | Añadir nulo → rellenar con uuid4 por fila → no nulo y único | RF-2 |
| backend/apps/assets/zone.py | C | Validación pura de la zona | RF-3 |
| backend/apps/assets/selectors.py | C | Lectura pública en lista blanca: una consulta, LIMIT 201, sin recuento | RF-1, RF-2, RF-4 |
| backend/apps/assets/serializers.py | C | Serializer de salida (no ModelSerializer: no importa `Asset`) | RF-2 |
| backend/apps/assets/views.py | C | `PublicAssetListView` y `PublicListThrottle` (subclase de `AnonRateThrottle`) | RF-1…RF-5 |
| backend/apps/assets/urls.py | C | `public/assets/` | RF-1 |
| backend/apps/assets/demo.py | C | Datos de los 25 bienes de demostración (sin importar `Asset`) | RF-6 |
| backend/apps/assets/management/commands/create_demo_assets.py | C | Comando de demostración | RF-6, RF-7 |
| backend/conftest.py | M | Fixture autouse que vacía la caché `default` (contador del límite) | RF-5 |
| backend/openapi.json | C | Descripción OpenAPI generada y versionada | RNF Contrato |
| backend/apps/*/tests/*, config/tests/* | C/M | Tests por capa (ver Estrategia) | RF-1…RF-7 |
| .github/workflows/ci.yml | M | Paso de desfase de la descripción en backend; job `frontend-quality` (vitest, build, eslint, desfase de tipos) | RNF Contrato |
| docs/architecture.md | M | Capa de API, límite, selectores, comando y estructura del frontend | — |
| frontend/package.json, package-lock.json, .npmrc, .nvmrc, index.html, vite.config.ts, tsconfig*.json, eslint.config.js, .env.example | C | Esqueleto con 19 dependencias exactas; `save-exact`, `ignore-scripts` y `engine-strict`; Node `^22.13.0`; proxy `/api`; `VITE_MAP_STYLE_URL` | RF-8 |
| frontend/src/main.tsx, app/route.ts, app/NotFoundPage.tsx | C | `resolveRoute`: `/` y `/map/` → `replaceState` a `/map`; `/map` → mapa; otra dirección → «Página no encontrada» | RF-8, RF-14 |
| frontend/src/styles/index.css | C | `@import "tailwindcss"`, tokens `@theme`, fuente autoalojada | RNF Identidad |
| frontend/src/i18n/es.ts, format.ts | C | Catálogo de mensajes; precio y plurales en español | RF-11…RF-14 |
| frontend/src/api/schema.gen.ts | C | Tipos generados (openapi-typescript) | RNF Contrato |
| frontend/src/api/validate.ts, publicAssets.ts | C | Esquema Zod estricto; fetch del mismo origen con timeout y cancelación; clasificación de fallos | RF-9, RF-13 |
| frontend/src/map/requestBox.ts, scheduler.ts | C | Cuadro pedido (puro); espera y cancelación (temporizador inyectado) | RF-9, RF-12 |
| frontend/src/map/geodesy.ts, circles.ts | C | Haversine, polígono geodésico, círculos únicos por (ubicación, radio), visibilidad de un círculo | RF-10, RF-11 |
| frontend/src/map/style.ts, MapView.tsx | C | Validación de la URL y del JSON del estilo, URLs permitidas, MapLibre, controles, atribución, capas | RF-8, RF-10, RF-13 |
| frontend/src/panel/ResultsPanel.tsx, AssetCard.tsx, header.ts, frontend/src/state/viewState.ts | C | Panel, tarjetas no interactivas, cabecera, región de estado, estado del panel | RF-11, RF-12, RF-13 |
| frontend/src/assets/categories/*.svg | C | Las 11 imágenes de prototypes/006-mapa/datos/fotos, revisadas: sin referencias externas | RF-11 |

## Modelo de datos y migraciones
- `Asset.public_id`: `UUIDField(default=uuid.uuid4, editable=False, unique=True)`. Es v4 aleatorio y distinto de `id`. Queda fuera del admin y de los formularios.
  - `create_asset` y `update_asset` no lo aceptan como argumento (TypeError) y nunca lo incluyen en `update_fields`. `services.py` no cambia.
- `unique=True`, no `UniqueConstraint`: `test_the_constraints_are_the_nine_named_checks` exige que `Meta.constraints` tenga solo los nueve CHECK. El nombre automático de la restricción única se fija en un test con `diag.constraint_name`.
- Tres ficheros. Cada migración corre en su propia transacción, así que el UPDATE masivo no convive con el ALTER:
  1. `0002_asset_public_id`: `AddField(null=True, editable=False)`, sin default ni único.
  2. `0003_fill_asset_public_id`: `RunPython` con `apps.get_model`, `.using(schema_editor.connection.alias)` y un uuid4 por fila.
     - `reverse_code` explícito: pone el campo a nulo con un único `update()`. No es `noop` ni el `delete()` de las semillas, que borraría los bienes.
  3. `0004_alter_asset_public_id`: `AlterField(default=uuid.uuid4, editable=False, unique=True)`.
- `sqlmigrate` se revisa. Se aplica a la BD de desarrollo solo con OK expreso en ese momento.
- No hay más cambios de esquema: sin índice nuevo (D1).

## Contrato de API
### `GET|HEAD /api/v1/public/assets/?south=&west=&north=&east=`
- Los cuatro parámetros son obligatorios. Los desconocidos se ignoran (`format`, `category`, `q`…).
- Orden de proceso en DRF:
  1. negociación fija a JSON (sin 406);
  2. sin autenticación: el usuario es `AnonymousUser`;
  3. `AllowAny`;
  4. **límite**: anota la petición si la deja pasar;
  5. método: 405 para todo lo que no sea GET o HEAD, también OPTIONS;
  6. validación de la zona (400);
  7. selector.
- **200**: `Content-Type: application/json`, `Cache-Control: public, max-age=60` (solo aquí), `Vary: Accept-Encoding` explícito, sin `Set-Cookie` ni `Vary: Cookie`, y `Allow: GET, HEAD`. La vista marca esta respuesta como sin cookies.
- HEAD: mismas cabeceras que GET, sin cuerpo.

```json
{"results": [{"public_id": "3f0c…", "title": "Kayak doble", "category_slug": "kayak",
  "category_name": "Kayak", "price": "12.50", "currency": "EUR", "price_unit": "day",
  "privacy_radius": 1000, "latitude": 39.469912, "longitude": -0.376288}],
 "incomplete": false}
```
- Los campos son exactamente esos diez, en plano. `price` es una cadena con dos decimales.
- `incomplete` vale `true` si se leyeron 201 filas; se devuelven las 200 primeras. Nunca hay total.

### Errores de la lista pública
- Formato: `{"code": "<general>", "params"?: {"<parámetro>": "<código>"}, "retry_after"?: <entero ≥ 1>}`.
- Los produce solo el manejador de excepciones de DRF, que además pone `Cache-Control: no-store`.
- Nunca llevan `detail`, el valor recibido, coordenadas ni trazas.

| Estado | `code` | Cuándo |
|---|---|---|
| 400 | `invalid_parameters` + `params` | Falla algún límite. Un código por límite, el primero que falle en este orden: `required`, `repeated`, `too_long`, `not_a_number`, `out_of_range` |
| 400 | `zone_inverted` | Los cuatro límites son válidos y sur > norte u oeste > este (el área no se comprueba) |
| 400 | `zone_too_large` | Los cuatro son válidos, la zona no está invertida y el área es > 6 |
| 405 | `method_not_allowed` | POST, PUT, PATCH, DELETE, OPTIONS, TRACE; con `Allow: GET, HEAD` |
| 429 | `throttled` + `retry_after` | Límite superado, con cualquier método. `Retry-After` lleva el mismo entero |

- Otras `APIException` (hoy no se alcanzan): `not_found` (404), `forbidden` (401/403) y `bad_request` (resto de 4xx).
- Una excepción que no es de DRF sale con la respuesta de Django (riesgo aceptado hasta la 011).
- Un test compara el conjunto de códigos con esta tabla.

### Permisos por endpoint (constitución, punto 5)
| Ruta y método | Anónimo | Usuario con sesión (desde la 009) | Propietario del bien | Staff |
|---|---|---|---|---|
| GET/HEAD `/api/v1/public/assets/` | 200 con los bienes visibles | Lo mismo que el anónimo: la vista no autentica y el límite le cuenta igual | Lo mismo; nunca sus pausados ni la exacta | Lo mismo |
| Cualquier otro método, incluido OPTIONS | 405 (429 si el límite está superado) | ídem | ídem | ídem |
| Descripción OpenAPI | No se sirve por HTTP | ídem | ídem | ídem |

- No hay 404 ni 403 por objeto: no hay vista de detalle.
- Hoy no existen `AuthenticationMiddleware` ni clases de autenticación, así que los tests con `force_login` (propietario y staff) pasan por construcción. Quedan como guarda de regresión para la 009.
- Un test comprueba que la clase de la vista declara en sí misma `authentication_classes = []`, `permission_classes = [AllowAny]`, `throttle_classes` y `http_method_names = ["get", "head"]`.

### Ajustes globales de DRF
- Renderer: solo `JSONRenderer` (sin la interfaz navegable ni `Vary: Accept`).
- Parser: solo `JSONParser`.
- Negociación: `JSONOnlyNegotiation`, que ignora `Accept`. `URL_FORMAT_OVERRIDE = None`.
- `DEFAULT_VERSIONING_CLASS = None`: la versión va en la ruta `api/v1/`.
- `DEFAULT_AUTHENTICATION_CLASSES = []` y `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]` (denegar por defecto).
- `DEFAULT_THROTTLE_CLASSES = []` y `NUM_PROXIES = 0`.
- `EXCEPTION_HANDLER = apps.core.api.api_exception_handler`.
- `DEFAULT_SCHEMA_CLASS = drf_spectacular.openapi.AutoSchema`.
- `APPEND_SLASH` no cambia (011).

### Descripción legible por máquina
- No se sirve por HTTP en ningún entorno: no hay SpectacularAPIView, ni Swagger, ni Redoc.
- `extend_schema` declara los parámetros, la respuesta 200 y los errores 400, 405 y 429.
- Se genera a `backend/openapi.json` (versionado) con `docker compose exec -u "$(id -u)" backend python manage.py spectacular --format openapi-json --file openapi.json --validate --fail-on-warn --lang en`.
- SPECTACULAR_SETTINGS: `SCHEMA_PATH_PREFIX=r"/api/v[0-9]+"`, `SERVE_INCLUDE_SCHEMA=False`, `COMPONENT_SPLIT_REQUEST=True`, `VERSION="1.0.0"`.
- CI:
  - backend: se regenera en /tmp del contenedor y se compara con `diff`;
  - frontend: `npx openapi-typescript ../backend/openapi.json -o src/api/schema.gen.ts --check`.

## Lógica
**Backend**
- `parse_zone(params: Mapping[str, list[str]]) -> Zone | ZoneError` (puro, sin DRF). Recibe `request.GET.lists()`.
  - Por parámetro:
    - ausente → `required`;
    - más de un valor → `repeated`;
    - más de 32 caracteres → `too_long`;
    - no cumple `re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", v)` → `not_a_number`;
    - fuera de ±90 o ±180 → `out_of_range`.
  - Se aceptan `-0` y los ceros finales. Se rechazan `+`, `01`, `39.`, `.5`, exponente, coma, espacios, `_`, dígitos no ASCII, `NaN` e `Infinity`.
  - Después, inversión. Si no hay inversión, área con `decimal.localcontext(Context(prec=100, traps=[Inexact, InvalidOperation]))`: dos operandos de 32 caracteres no pasan de unos 66 dígitos, así que nunca redondea.
- `visible_assets_in_zone(*, zone, limit) -> (list[dict], bool)`:
  - `filter(status="active", owner__is_active=True)`, que es un JOIN sin `select_related("owner")`;
  - `annotate(longitude=ST_X(Cast(public_location, GeometryField())), latitude=ST_Y(…))` como el CHECK del modelo, y `Range` inclusivo en ambas;
  - `order_by("-created_at", "-id")`;
  - `.values()` con la lista blanca: `public_id`, `title`, `category__slug`, `category__name`, `price`, `currency`, `price_unit`, `privacy_radius`, `latitude`, `longitude`;
  - `list(qs[:limit + 1])`; devuelve `rows[:limit]` y `len(rows) > limit`.
- `PublicListThrottle(AnonRateThrottle)`, sin implementación propia:
  - `rate = "60/min"`: la tasa se fija en la clase porque `THROTTLE_RATES` se lee al importar y `override_settings` no la cambia;
  - `scope = "public_assets"`, para no compartir contador con otros throttles anónimos;
  - con `NUM_PROXIES = 0`, `get_ident` devuelve siempre `REMOTE_ADDR`;
  - ventana deslizante en la caché `default`; DRF solo anota las peticiones permitidas, así que las 429 no cuentan y las 400 y 405 sí;
  - la hora la da el atributo `timer`, sustituible en los tests;
  - no hace falta un alias de caché aparte: en la 011 la caché `default` pasa a ser compartida.
- Cookies de la respuesta pública (`apps/core/middleware.py`):
  - `mark_response_cookieless(response)` pone en la respuesta una marca expresa (`response.cookieless = True`). La vista pública la pone en su 200.
  - `CleanMarkedResponseMiddleware` va el primero de MIDDLEWARE, para ejecutarse el último en la respuesta, después de Session y CSRF. Si la respuesta lleva la marca, vacía `response.cookies` y quita `Cookie` de `Vary`. Si no la lleva, no hace nada.
  - No mira la ruta: ninguna vista futura bajo `/api/` (la autenticación de la 009) pierde sus cookies salvo que marque expresamente su respuesta.
  - La vista no puede quitar esas cookies por sí misma: Session y CSRF las añaden después de ella.
- `api_exception_handler(exc, context)`:
  - traduce `ApiError` (zona), `MethodNotAllowed` y `Throttled` al formato;
  - en `Throttled` pone `Retry-After` y `retry_after` con `exc.wait` (≥ 1 por construcción);
  - pone `no-store`;
  - devuelve `None` para lo que no es de DRF.
- Vista: `get` llama a `parse_zone`; si hay error lanza `ApiError`; si no, selector → serializer → `Response`, más `patch_cache_control(public=True, max_age=60)`, `patch_vary_headers(("Accept-Encoding",))` y `mark_response_cookieless`. Nada de esto toca la sesión.
- Comando `create_demo_assets`:
  - Comprueba `getattr(settings, "ENVIRONMENT", None) in {"development", "test"}` antes de cualquier acceso a la BD. Si falla: `CommandError("El comando de demostración solo se ejecuta en development o test.")`.
  - Dentro de un `transaction.atomic()`:
    - si `demo@example.com` existe, «El propietario de demostración ya existe; no se ha creado nada.»;
    - si no: `create_user(email, password=self.generate_password())`, 25 llamadas a `create_asset` (`now − i min`, `now` inyectable) y 24 a `update_asset(status="active")`.
  - Las ubicaciones públicas quedan a menos de 4 km de (39,4699, −0,3763).
  - Salida fija: «Creados 25 bienes de demostración (24 activos, 1 pausado).».
  - La contraseña viene de un generador inyectable (`secrets.token_urlsafe(32)`) y nunca se imprime.

**Frontend (funciones puras, sin importar maplibre-gl, vitest en entorno node)**
- `resolveRoute(pathname)` → `redirectToMap` (`/` y `/map/`) | `map` (`/map`) | `notFound` (cualquier otra). La redirección es un `history.replaceState` a `/map`, sin entrada en el historial.
- `requestBox(visible)`:
  - ampliación en latitud de 2000/6 371 008,8 rad (≈ 0,017986°); en longitud, ese valor / cos(latitud de la zona visible más alejada del ecuador);
  - índices enteros de paso 0,05°: `floor(sur·20)`, `floor(oeste·20)`, `ceil(norte·20)` y `ceil(este·20)`;
  - fuera de ±1700 (±85°) o ±3600 (±180°) → `outOfRange`; nunca recorta;
  - área en celdas `(N−S)·(E−O) ≤ 2200` (5,5 grados²), en aritmética entera; si no, `tooLarge`;
  - formato desde el entero (signo, parte entera y dos decimales), sin `toFixed`; orden fijo `south, west, north, east`.
- `createRequestScheduler({delayMs: 300, setTimer, clearTimer, run})`:
  - cada movimiento reinicia la espera;
  - al vencer, aborta la petición anterior y lanza la nueva con un número de secuencia;
  - descarta las respuestas viejas.
- `fetchPublicAssets(box, signal)`:
  - `fetch("/api/v1/public/assets/?…", {credentials: "omit", signal})` con un timeout de 10 s (AbortController);
  - comprueba el estado y `Content-Type`, captura el fallo de `JSON.parse` y valida con `validateResponse`;
  - nunca muestra el cuerpo del error.
- `validateResponse(json)`:
  - `z.strictObject` en la raíz y en cada bien; `public_id` UUID v4; `title` texto no vacío;
  - `price` `^\d{1,5}\.\d{2}$` (el máximo real de la spec 005 es 99999.99, `PRICE_MAXIMUM` en `rules.py` y CHECK `assets_asset_price_range`: cinco cifras enteras y dos decimales); `currency` el literal "EUR";
  - `price_unit` ∈ {hour, day, week, month}; `privacy_radius` ∈ {500, 1000, 2000};
  - latitud y longitud finitas en rango; `incomplete` booleano; como mucho 200 bienes; ids únicos.
  - Si un solo bien falla, la respuesta entera es inválida.
- `classifyFailure` → `network | timeout | server | throttled | invalid`.
- `circlePolygon(center, radius, 64)` (destino geodésico); `circleKey = lat|lon|radius`.
- `isCircleVisible(circle, bounds)`: haversine del centro al punto del rectángulo más cercano ≤ radio.
- `headerText(count, incomplete)`.
- `viewState(...)` → `loading | results | empty | zoomIn | error(kind) | styleError`. `atInitialView` compara el centro (±1e-6°) y el zoom (±0,01).
- `validateStyleUrl(url)`: `new URL`, `https:`, sin usuario ni contraseña.
- `isAllowedMapUrl(url, allowedOrigins)`: https y un origen permitido (el del estilo y el propio).
- `validateStyleJson(json)`: `version === 8`, `sources` es un objeto y `layers` un array.

## Interfaz
- Móvil primero (375 px).
  - Mapa a pantalla completa.
  - El panel ocupa abajo una sola altura de `40dvh` (mínimo 240 px). La cabecera (número de bienes) y el aviso de ubicación aproximada quedan fijos arriba; la lista se desplaza dentro.
- Desde 900 px: columna fija a la izquierda de 400 px, con todo el alto. El mapa sigue a pantalla completa debajo: la zona visible incluye la parte tapada.
- La atribución usa `AttributionControl({compact: false})` arriba a la derecha y el panel nunca la tapa. Dice «OpenFreeMap © OpenMapTiles Data from OpenStreetMap».
- El zoom usa `NavigationControl({showCompass: false})` debajo de ella. El CSS sube los botones a 44×44 px.
- Accesibilidad:
  - el canvas tiene la etiqueta «Mapa de bienes en alquiler» (locale `Map.Title`) y se mueve y acerca con el teclado por defecto;
  - `map.keyboard.disableRotation()`;
  - los círculos no son enfocables;
  - «Reintentar», «Volver a la zona inicial» e «Ir al mapa» miden 44 px como mínimo;
  - foco visible: contorno de 3 px tinta (#14181F) con 2 px de separación.
- Círculos: fuente GeoJSON con capas fill (azul #1647B8 al 12 %) y line (azul, 1,5 px), sin marcador ni punto central. Los círculos únicos van por `circleKey`.
- Tarjeta (`<li>`, no interactiva):
  - imagen decorativa (`alt=""`), elegida por `Map` slug → URL; si el slug no está, la de «other»;
  - título como texto en `<bdi>`, nunca HTML;
  - nombre de la categoría y «Zona de unos 500 m», «1 km» o «2 km»;
  - precio con `Intl.NumberFormat("es-ES")` a partir de céntimos enteros, sin decimales si son cero: «12,50 € / día», «30 € / semana».
- Región `role="status"` (polite): «Buscando bienes…» y luego el resultado, la lista incompleta, el vacío o el error; una vez por petición.
- Estados del panel:
  - carga;
  - resultados, con la cabecera «1 bien en esta zona», «N bienes en esta zona» o «Mostrando N bienes. Puede haber más: acerca el mapa para verlos todos»;
  - «No hay bienes en esta zona»;
  - «Acerca el mapa para ver los bienes»;
  - «Volver a la zona inicial», oculto en la vista inicial;
  - error de la petición con «Reintentar», sin círculos.
  - Si falla el estilo, el mensaje y «Reintentar» sustituyen al mapa. Un `GPUInitializationError` (sin WebGL2) se trata igual.
- Mensajes del catálogo:
  - red: «No hay conexión. Comprueba tu red y vuelve a intentarlo.»;
  - tiempo agotado: «El servidor tarda demasiado en responder.»;
  - servidor: «Ha habido un problema en el servidor.»;
  - límite: «Has hecho muchas búsquedas seguidas. Espera un momento y vuelve a intentarlo.»;
  - respuesta no válida: «No se han podido leer los bienes.»;
  - estilo: «No se ha podido cargar el mapa.».
- «Página no encontrada»: título y enlace «Ir al mapa» (`<a href="/map">`, 44 px).
- Identidad:
  - tokens `@theme`: accent #1647B8, sky #E8EEFF, ink #14181F, muted #424B5A, y lemon #F5D547 (definido, sin uso hasta la 007);
  - `font-family: "Bricolage Grotesque Variable"`, desde `@fontsource-variable`;
  - contraste calculado: azul sobre cielo 6,9:1 y gris sobre cielo 7,6:1.
- Movimiento reducido: `duration: 0` en los cambios de cámara y sin transiciones CSS.
- Privacidad: ni `pushState`, ni hash, ni almacenamiento del navegador. `/` y `/map/` hacen `history.replaceState(null, "", "/map")`.

## Decisiones
La partición de la spec ya está decidida: se hizo por profundidad y la interacción pasa a la 007.

| Decisión | Opciones | Elegida | Qué evita | Coste |
|---|---|---|---|---|
| D1 Filtro espacial | A) `ST_X`/`ST_Y` con Range, como el CHECK; B) A más un índice GiST de expresión; C) `bboverlaps` sobre geography | A | Aristas geodésicas de geography (fallan con altura cero y en bordes); una migración más | Sin índice: recorre los activos. Válido en el MVP |
| D2 Origen del UUID | A) `default=uuid.uuid4` en el modelo; B) lo genera el servicio | A | Romper `make_asset` y los `Asset(...)` directos | Eximir `public_id` en `test_no_field_is_nullable_or_has_a_default`, comprobando que su default es `uuid.uuid4` |
| D3 Migración del UUID | A) tres ficheros con RunPython; B) RunSQL `gen_random_uuid()` | A | El mismo UUID en todas las filas; «pending trigger events» | Tres ficheros |
| D4 Límite | A) subclase de `AnonRateThrottle` con `rate` y `NUM_PROXIES=0`; B) throttle propio en ventana fija; C) A con un alias de caché propio | A | Código propio; la tasa leída al importar; X-Forwarded-For | La ventana deslizante no es atómica entre hilos; contador por proceso |
| D5 Ruta | A) `/api/v1/public/assets/`; B) `/api/v1/assets/`; C) versionado de DRF | A | Que la escritura de la 010 comparta vista, límite y caché con lo público | Ruta específica de lo público |
| D6 Formato de error | A) `{code, params?, retry_after?}` plano; B) `{error: {…}}`; C) el de DRF | A | `detail` con mensajes y valores | Manejador y tabla propios |
| D7 Negociación | A) fija a JSON; B) la de DRF | A | 406 antes del límite y `Vary: Accept` | Una clase de diez líneas |
| D8 `no-store` en los errores | A) en el manejador de DRF; B) un middleware global; C) un decorador por vista | A | B queda para la 011; C se olvida en vistas nuevas | Cubre solo los errores de DRF, que son los que pide la spec |
| D9 Cookies en el 200 público | A) middleware que actúa solo sobre las respuestas marcadas expresamente por la vista; B) middleware por ruta `/api/`; C) subclases de Session y CSRF por ruta; D) postproceso en la vista | A | B quitaría las cookies de cualquier vista futura bajo `/api/` (la autenticación de la 009); D no funciona porque Session y CSRF actúan después de la vista; C duplica Django | Una marca más en la respuesta; un test comprueba que una respuesta sin marcar conserva sus cookies |
| D10 Métodos | A) `http_method_names = ["get", "head"]`; B) solo GET | A | OPTIONS con metadatos (200 por defecto en APIView) | Un método más en los tests |
| D11 Descripción OpenAPI | A) drf-spectacular en runtime, sin ruta; B) solo en dev; C) a mano | A | C se desfasa; B obliga a mover las anotaciones fuera de las vistas | 10 paquetes en la imagen |
| D12 Entorno del comando | A) constante `ENVIRONMENT`; B) `settings.SETTINGS_MODULE`; C) leer `DJANGO_ENV` | A | B vale None bajo `override_settings` (verificado); C la prohíbe `test_env_reader` | Una línea por settings |
| D13 Compresión | A) sin GZip en Django y `Vary: Accept-Encoding` explícito; B) GZipMiddleware | A | B omite Vary con cuerpos < 200 bytes; hoy no hay GZip (verificado) | La compresión llega con el proxy (011) |
| D14 Círculo | A) polígono geodésico de 64 pasos; B) capa `circle` con radio por zoom | A | B no es exacto y no se puede probar al 99–101 % | GeoJSON algo mayor |
| D15 Validación de la respuesta | A) Zod 4 con `strictObject`; B) guardas a mano | A | Muchas ramas a mano sin probar | Una dependencia |
| D16 Fallo del estilo | A) descargar el JSON con timeout, validar y pasar el objeto; B) deducirlo del evento `error` | A | B no tiene un evento específico de fallo del estilo | Un fetch y un validador mínimo |
| D17 URLs de terceros | A) `transformRequest` con `isAllowedMapUrl`; B) esperar a la CSP de la 011 | A | Peticiones a hosts que meta el estilo o el TileJSON | Hay que comprobar en el navegador cómo se rechaza |
| D18 Rutas | A) `resolveRoute` y `replaceState` sin router; B) react-router | A | Una dependencia | Ninguno |
| D19 Fuente | A) @fontsource-variable; B) woff2 a mano | A | Copia manual sin versión ni licencia trazada | Una dependencia |

### Dudas abiertas de la spec: resolución
| Duda | Resolución |
|---|---|
| Paso de la cuadrícula | 0,05°, con índices enteros |
| Margen del área en el cliente | 0,5 grados²: se pide si el área es ≤ 5,5 (≤ 2200 celdas) |
| Tiempo de espera | 300 ms tras `moveend`. La primera petición se lanza a mano tras `load`; redimensionar emite `moveend` |
| Tiempo máximo de espera | 10 s; luego se aborta y sale el error `timeout` |
| Panel por debajo de 900 px | `40dvh`, mínimo 240 px; cabecera y aviso fijos |
| Ancho de la columna | 400 px desde 900 px |
| Gramática ASCII | `-?(?:0\|[1-9][0-9]*)(?:\.[0-9]+)?` con `re.fullmatch`; longitud ≤ 32 comprobada antes |
| Formato, códigos y versión | Ver Contrato. Ruta `/api/v1/` |
| Publicación de la descripción | No se sirve por HTTP; fichero versionado `backend/openapi.json`, generado en desarrollo y comprobado en CI |
| Mismo origen en desarrollo | Proxy de Vite `/api` → `http://localhost:8000`; el navegador solo habla con `localhost:5173`; sin cabeceras CORS |
| Estilo que no usa https | `validateStyleUrl` en ejecución, antes de crear el mapa. Si falla: «No se ha podido cargar el mapa» y ninguna petición |
| Contador del límite | Caché `default` de Django (LocMemCache por proceso) en desarrollo. En la 011 se configura un `CACHES["default"]` compartido; `DatabaseCache` no añade dependencias |
| Dependencias | Tablas siguientes |

### Dependencias nuevas (aprobadas; todas verificadas)
Python (hashes de todas las ruedas, también manylinux x86_64 y aarch64 de rpds-py y PyYAML; `--require-hashes`; imagen python:3.13-slim-trixie):

| Paquete | Versión | Licencia | Para qué |
|---|---|---|---|
| djangorestframework | 3.18.3 | BSD-3-Clause | Capa de API |
| drf-spectacular | 0.30.0 | BSD-3-Clause | Descripción OpenAPI |
| inflection | 0.5.1 | MIT | Transitiva |
| jsonschema | 4.26.0 | MIT | Transitiva (`--validate`) |
| jsonschema-specifications | 2025.9.1 | MIT | Transitiva |
| referencing | 0.37.0 | MIT | Transitiva |
| rpds-py | 2026.9.1 | MIT | Transitiva; rueda cp313 para x86_64 y aarch64 |
| attrs | 26.1.0 | MIT | Transitiva |
| PyYAML | 6.0.3 | MIT | Transitiva |
| uritemplate | 4.2.0 | BSD-3-Clause OR Apache-2.0 | Transitiva |
| typing_extensions | — | PSF-2.0 | **Fuera del lock**: solo la piden referencing (Python < 3.13) y drf-spectacular (< 3.10); el lock se compila con 3.13 |

npm (19 dependencias, versiones exactas, sin `^`; `package-lock.json` en git; `npm ci --ignore-scripts`; `engines` y `.nvmrc` con Node `^22.13.0`; esta máquina usa Node v22.23.3 y npm 10.9.9; resolución probada: 288 paquetes, 0 vulnerabilidades, sin ERESOLVE):

| Paquete | Versión | Licencia | Para qué |
|---|---|---|---|
| react, react-dom | 19.3.1 | MIT | Interfaz |
| maplibre-gl | 6.14.0 | BSD-3-Clause | Mapa |
| zod | 4.6.7 | MIT | Validar respuestas (≥ 4.6.6 por el aviso de DoS) |
| @fontsource-variable/bricolage-grotesque | 5.3.0 | OFL-1.1 | Tipografía autoalojada |
| vite (dev) | 8.3.5 | MIT | Servidor y build |
| @vitejs/plugin-react (dev) | 6.1.2 | MIT | JSX |
| typescript (dev) | 5.9.3 | Apache-2.0 | Tipos (no la 7.x) |
| vitest (dev) | 5.0.5 | MIT | Tests de funciones puras (sin jsdom ni happy-dom) |
| tailwindcss, @tailwindcss/vite (dev) | 4.3.3 | MIT | Estilos |
| eslint (dev) | 10.13.0 | MIT | Lint |
| @eslint/js (dev) | 10.0.1 | MIT | Reglas base |
| typescript-eslint (dev) | 8.72.1 | MIT | Lint de TS (paquete paraguas) |
| eslint-plugin-react-hooks (dev) | 7.1.1 | MIT | `reactHooks.configs.flat.recommended` |
| globals (dev) | 17.13.0 | MIT | Globales del navegador |
| @types/react, @types/react-dom (dev) | 19.3.0 | MIT | Tipos de React 19 |
| openapi-typescript (dev) | 7.13.0 | MIT | Tipos desde OpenAPI |

- `@types/node` 22.20.5 no se añade: `vite.config.ts` no importa módulos de Node y `skipLibCheck` está activo. Si el build lo pidiera, se pide aprobación.
- No se añaden `eslint-plugin-react-refresh` ni `jiti`: `eslint.config.js` va en JS.
- Licencias de dependencias transitivas a tener presentes: lightningcss MPL-2.0 (solo build), caniuse-lite CC-BY-4.0 y argparse Python-2.0.
- Scripts de instalación: solo fsevents (opcional, darwin). Los binarios nativos llegan por `optionalDependencies`.

## Blast radius
- `apps/assets/tests/test_models.py`:
  - `EXPECTED_FIELDS` y `EXPECTED_COLUMNS` ganan `public_id` (`UUIDField`, `uuid`);
  - `test_no_field_is_nullable_or_has_a_default` pasa a eximir solo a `public_id`.
- `apps/assets/tests/test_architecture.py`:
  - `selectors.py` (ya en `ASSET_MODULES`) no puede escribir;
  - `views.py`, `serializers.py`, `demo.py` y el comando no pueden importar `Asset`;
  - el comando importa solo `create_asset` y `update_asset`.
- `config/tests/test_migrations.py`: `makemigrations --check` debe cuadrar con 0004.
- `config/tests/test_env_reader.py`: el comando no lee `os.environ`.
- `config/tests/test_env_template.py`: sin variables nuevas de backend. `VITE_MAP_STYLE_URL` vive en `frontend/.env.example`, que permite `!.env.example`.
- `config/tests/test_http_hardening.py`: sus respuestas no llevan la marca, así que el nuevo middleware no las altera.
- `config/tests/test_settings.py`: casos de `ENVIRONMENT`.
- `config/tests/test_production.py`: `manage.py check` con DRF instalado.
- `apps/assets/tests/test_create.py`, `test_update.py`: casos de `public_id`. `services.py` no se toca.
- `backend/conftest.py`: fixture autouse nueva.
- `Dockerfile`: sin cambios, pero la imagen se reconstruye.
- `ci.yml`: paso de desfase y job de frontend.
- `.gitignore` ya ignora `node_modules/` y `dist/`.

## Riesgos
| Riesgo | Mitigación |
|---|---|
| Hasta la 011, una ruta inexistente bajo `/api/`, la dirección sin barra (301 cacheable) o un error interno reciben la respuesta de Django, sin formato ni `no-store` | Aceptado en la spec. Ninguna lleva datos de bienes |
| Hasta la 010, con DEBUG activo, la página técnica puede mostrar las coordenadas de los bienes de demostración | Aceptado en la spec; son ficticias |
| La ventana de `SimpleRateThrottle` (lectura y escritura) no es atómica entre hilos de runserver: puede dejar pasar alguna petición de más | Aceptado en desarrollo; caché compartida en la 011 |
| Contador por proceso; en Docker todo el host comparte IP | Riesgo aceptado en la spec |
| Una vista que marque su respuesta como sin cookies pierde las suyas | La marca es expresa y solo la pone la lista pública. Un test comprueba que una respuesta sin marcar conserva sus cookies, y otro que la vista no toca la sesión |
| Un límite con más de 15 cifras significativas se compara como el doble más cercano (como el CHECK) | Los bordes de la spec se prueban contra la BD real |
| Sin índice espacial, la consulta recorre los activos | Volumen de MVP; D1-B si hace falta |
| La migración choca con escrituras entre 0002 y 0004 | Solo hay datos de desarrollo; se aplica con el servidor parado |
| Sin WebGL2, `new Map()` lanza un error síncrono | Se captura y se trata como fallo del mapa (RF-13) |
| Tareas que pueden pasar de 30 min (T5, T7, T9, T10) | Se avisa al llegar a ellas. Corte posible sin pasar de 10 tareas: Zod de la T7 a la T8 |

## Estrategia de tests
| RF | Cómo se verifica |
|---|---|
| RF-1 | pytest. Selector: dentro y fuera, los cuatro bordes, altura cero (39,4), pausados (también de un propietario), cuentas inactivas, base vacía. API: anónimo, propietario y staff (`force_login`) reciben el mismo cuerpo |
| RF-2 | pytest. Conjunto exacto de claves del bien y de la raíz. `public_id`: versión 4, ≠ `id`, único (nombre de la restricción), `editable=False`, sin cambios al editar, pausar, reactivar y mover en pausa (UPDATE capturado sin `public_id`), TypeError al pasarlo a los servicios. Relleno con las apps históricas y el test del alias |
| RF-3 | pytest de `parse_zone`: `abc`, vacío, `NaN`, `Infinity`, `-inf`, `1e1`, `39,4`, `" 39.4"`, `"39.4\n"`, dígitos no ASCII (escapes), `+39`, `039`, `39.`, `.5`, `1_0`, repetido, 33 frente a 32 caracteres, 90,000001, −180,5, sur y este a la vez, invertida (y en el antimeridiano), invertida con área > 6, área 6 aceptada y 6,0001 rechazada. API: formato, `no-store`, sin valores ni coordenadas; parámetros desconocidos ignorados |
| RF-4 | pytest: 201 → 200 e `incomplete=true`; 200 → `false`; orden con empate de `created_at` por `id` descendente; `CaptureQueriesContext` con una consulta, `LIMIT 201`, sin `COUNT(` y sin `exact_location` |
| RF-5 | pytest con la caché vaciada y `timer` falso: 60 POST → 405 y la siguiente → 429; 60 inválidas → 400 y luego 429; con el límite superado, POST y OPTIONS → 429; las 429 no alargan la espera; `X-Forwarded-For` distintos cuentan para una IP; otra `REMOTE_ADDR` aparte; con `force_login` también cuenta; `Retry-After` entero ≥ 1 igual a `retry_after`; `no-store` |
| RF-6 | pytest: 25 bienes, 24 activos y 1 pausado; las 11 categorías; los tres radios; un par con la misma ubicación pública y el mismo radio; haversine < 4 km desde el centro; altas por el servicio (25 y 24 llamadas); la segunda ejecución no crea nada y lo dice; un fallo a mitad no deja nada |
| RF-7 | pytest **sin** `django_db`: con `ENVIRONMENT` en `production` o ausente, CommandError con el mensaje fijo y ningún acceso a la BD. `test_settings` comprueba `ENVIRONMENT` de cada módulo |
| RF-8 | Chrome DevTools a 375 y 1280 px (validation.md): `/` y `/map/` → `/map` sin entrada en el historial, mapa a pantalla completa en la vista inicial, mapa base, panel, aviso y atribución visibles. vitest de `resolveRoute` |
| RF-9 | vitest: ampliación con la latitud más alejada (59–61), redondeo, rechazo fuera de ±85, ±180 y en el antimeridiano, margen (6,3 y 6 justos no piden), formato estable; planificador con temporizadores falsos (solo la última pide, la vieja no se pinta) y timeout. DevTools: una sola petición tras parar, aciertos de caché dentro del mismo cuadro |
| RF-10 | vitest: haversine del centro a cada vértice entre el 99 % y el 101 % (tres radios, varias latitudes); la misma clave da un solo círculo y radios distintos, dos. DevTools: círculos sin marcador, sin agrupar a zoom bajo |
| RF-11 | vitest: `headerText` (1, N, incompleta), `isCircleVisible` (círculo de 2 km que asoma por el borde), orden de la respuesta. DevTools: lista del panel |
| RF-12 | vitest: `viewState` (vacío, «acerca», sin botón en la vista inicial). DevTools: vacío y su salida |
| RF-13 | vitest: `validateResponse` (1500, `null`, campo de más, otra moneda, precio mal formado, 201 bienes, ids repetidos), `Content-Type` incorrecto, JSON roto, `classifyFailure`, `validateStyleUrl` y `validateStyleJson`. DevTools: sin conexión, respuesta 500 y 429 simuladas, estilo bloqueado y con URL http |
| RF-14 | vitest de `resolveRoute` (`/otra` → `notFound`). DevTools: «Página no encontrada» con «Ir al mapa» y teclado |

| Requisito no funcional y criterio de finalización | Verificación |
|---|---|
| Permisos | pytest: GET y HEAD admitidos; OPTIONS y métodos de escritura → 405 con formato y `no-store`; atributos declarados en la vista; `force_login` |
| Privacidad | pytest con el SQL capturado y el conjunto de claves. DevTools: la URL no cambia, almacenamiento vacío, `history.length` estable |
| Caché | pytest: el 200 lleva `public` y `max-age=60` (por directivas); 400, 405 y 429 llevan `no-store` |
| Respuesta idéntica | pytest: misma petición con sesión de `force_login`, `Authorization`, `Origin`, `Accept: application/xml`, `?format=xml` y `X-Forwarded-For`. Mismo cuerpo, mismo `Cache-Control`, `Vary == Accept-Encoding`, sin `Set-Cookie` ni `Access-Control-*`, `SessionStore.load` nunca llamado. Se repite con `csrftoken=x` y `sessionid=short`: sin `Set-Cookie` ni `Vary: Cookie`. Test del middleware: la respuesta marcada sale limpia y una respuesta sin marcar conserva sus cookies |
| Errores de la lista | pytest: formato único en 400, 405 y 429; conjunto de códigos igual a la tabla; sin valores, coordenadas ni trazas |
| Logs | pytest: `caplog` a DEBUG con `force_debug_cursor` en una petición con coordenadas centinela (no aparecen) y en el comando (ni coordenadas de `coordinate_forms` ni la contraseña centinela en stdout, stderr o logs) |
| Contrato | CI: `spectacular --validate --fail-on-warn` más `diff`; `openapi-typescript --check` |
| Terceros, mismo origen, accesibilidad, configuración, idioma | DevTools: red solo a `localhost:5173` y `tiles.openfreemap.org` por https; woff2 del propio origen; teclado en mapa, zoom, «Reintentar», «Volver…» e «Ir al mapa»; 44 px; contraste; movimiento reducido emulado; región de estado; consola sin errores. eslint con `no-restricted-syntax` contra `dangerouslySetInnerHTML`, `innerHTML` y `setHTML`. Prueba con `VITE_MAP_STYLE_URL=http://…` |
| De punta a punta | Con OK para `migrate` y el comando en desarrollo: en la vista inicial, 24 tarjetas sin el pausado y sus círculos (validation.md) |
| pytest, ruff, vitest, build y eslint en verde | En cada tarea y en CI |

### Pruebas de mecanismo (solo en tareas de privacidad o seguridad)
Se mutan los ficheros nuevos con su sha256 antes y después. Lo ajeno se muta con un plugin de pytest temporal. Las migraciones, con `--create-db`.
- T2 `public_id`:
  - `uuid1`;
  - `editable=True`;
  - `update_asset` lo regenera;
  - quitar `unique`.
- T3 zona:
  - quitar `fullmatch` o el `[0-9]` ASCII;
  - longitud 33;
  - área con float;
  - `>` por `>=`;
  - área en una zona invertida;
  - aceptar duplicados.
- T4 selector:
  - añadir `exact_location`, `id` u `owner` a `values`;
  - quitar `.values`;
  - `select_related("owner")`;
  - quitar el filtro de `status` o el de `owner__is_active`;
  - `[:200]`;
  - `.count()`;
  - quitar `-id`;
  - Range a mayor estricto.
- T5 endpoint, límite, cookies y OPTIONS:
  - campo de más en el serializer;
  - `SessionAuthentication`;
  - quitar el `Vary` explícito;
  - añadir `Vary: Cookie`;
  - añadir `Access-Control-Allow-Origin`;
  - quitar el middleware de cookies o la marca de la vista;
  - hacer que el middleware actúe por ruta `/api/` en vez de por marca;
  - poner la caché pública también en los errores;
  - el manejador incluye `detail`;
  - `NUM_PROXIES=None`;
  - `rate = "61/min"`;
  - comprobar el límite dentro de `get`;
  - quitar `Retry-After`;
  - añadir "options" a `http_method_names`.
- T6 comando:
  - quitar la comprobación de entorno;
  - consultar la BD antes de comprobarlo;
  - quitar `atomic`;
  - imprimir la contraseña.
- vitest:
  - T7: Zod que acepte 1500, `null`, un campo de más o otra moneda;
  - T9: `validateStyleUrl` e `isAllowedMapUrl` que acepten `http:` u otro host;
  - T10: título con `dangerouslySetInnerHTML` (renderizado con `react-dom/server`).

## Afirmaciones no verificadas
- DRF 3.18.3, leído del código por reviewer-docs y no confirmado en Context7 (los tests lo fijan):
  - `check_throttles` corre en `initial()`, antes de elegir el manejador (405);
  - `THROTTLE_RATES` se lee al importar;
  - con `authentication_classes = []`, `request.user` es `AnonymousUser` y la sesión no se lee;
  - `SimpleRateThrottle.cache` es la caché `default`;
  - `throttle_failure` no anota;
  - `Throttled.wait` se redondea hacia arriba.
  - Verificado en Context7: con `NUM_PROXIES=0` se usa siempre `REMOTE_ADDR`.
- Que `wait()` dé siempre ≥ 1 con el límite superado (lectura propia: queda una petición disponible y el resto de la ventana es > 0).
- DRF: `as_view` es `csrf_exempt`; `default_response_headers` pone `Allow`; el patrón de negociación propia.
- drf-spectacular: `extend_schema` con `OpenApiParameter` en un `APIView` sin serializer de entrada pasa `--fail-on-warn`; salida determinista con `--lang en`.
- ORM y PostgreSQL:
  - el ORM convierte a float los límites Decimal frente a `FloatField`;
  - cada migración corre en su propia transacción;
  - el nombre de la restricción única (lo fija un test).
- Que `pip-compile --generate-hashes` incluya los hashes aarch64 de rpds-py y PyYAML (se revisa en el diff del lock).
- Que `runserver` quite el cuerpo de HEAD (el cliente de test lo quita siempre; «sin cuerpo» se comprueba con curl en la validación).
- Que el servidor de desarrollo de Vite sirva index.html en cualquier ruta.
- MapLibre:
  - la forma de `setWorkerUrl` con Vite 8 (`?worker&url` o `?url`);
  - cómo se rechaza una URL en `transformRequest`;
  - que la etiqueta del canvas salga de `Map.Title`.
- El estilo positron usa URLs absolutas https en `tiles.openfreemap.org`.
- `z.number()` rechaza `Infinity`.
- Los SVG del prototipo no tienen referencias externas.
- Los contrastes, calculados a mano.
- Verificado en el código (Django 5.2.17 del .venv local; el contenedor usa 5.2.18):
  - no hay GZipMiddleware;
  - `UserSettingsHolder.SETTINGS_MODULE = None`;
  - CsrfViewMiddleware pone una cookie y `Vary: Cookie` con un token mal formado;
  - SessionMiddleware borra una `sessionid` de menos de 8 caracteres y añade `Vary: Cookie`;
  - `config/urls.py` está vacío;
  - DRF no está instalado.

## Skills que aplican
- sdd y django-drf.
- frontend-design y web-design-guidelines.
- Las skills react-ts y testing aún no existen. Mientras tanto se aplican los riesgos de MEMORY.md: jsdom no calcula layout y los mocks de fetch respetan AbortSignal.
