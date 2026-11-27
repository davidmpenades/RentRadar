# Plan 008 — Búsqueda y filtros por categoría en el mapa
Spec: specs/008-search-filters/spec.md (aprobada)
Estado del plan: aprobado (24-11-2026). Decididas: método de comparación (D1), ñ, alfabeto, contrato, índice y caracteres de formato. En su momento, con OK expreso: crear y aplicar la migración 0005 (T2), `migrate` en la BD de desarrollo (T10) y cada orden de Docker, una a una.

## Resumen
- Backend:
  - la lista pública `GET|HEAD /api/v1/public/assets/` acepta dos parámetros opcionales, `category` (identificador de categoría) y `q` (texto);
  - los valida en una función pura dentro de `get`, después del límite de peticiones;
  - los aplica en la misma consulta del selector, que conserva estado activo, cuenta activa, zona, orden, `LIMIT 201` y lista blanca;
  - el texto se compara con una columna generada por la BD, `title_folded`, que guarda el título plegado (sin mayúsculas ni tildes de un alfabeto fijo, con la ñ distinta de la n). Nunca se compara con la descripción, la categoría, el propietario ni la ubicación.
- Medición: `EXPLAIN (ANALYZE, BUFFERS)` de la consulta en la BD de test con 50 000 bienes sintéticos, antes de cambiarla (T1) y después (T6), registrada en validation.md. No bloquea la entrega; si recomienda un índice, es un cambio aparte.
- Frontend:
  - barra de filtros encima del mapa, con el buscador, «Quitar filtros» y una fila de 12 chips de categoría que se desplaza en horizontal;
  - estado de los filtros en funciones puras, petición con los filtros y cancelación con el planificador existente;
  - vacío y error con filtros en el panel;
  - `h1` oculto en la pantalla del mapa y la cabecera del panel como `h2`.
- Contrato: `backend/openapi.json` y `frontend/src/api/schema.gen.ts` se regeneran. La respuesta no cambia.

## Decisiones registradas
- Método de comparación (D1): opción (d), columna generada con `translate()`. Condición comprobada: en el catálogo de la base `postgres` del contenedor, `translate(text, text, text)` tiene `provolatile = 'i'` (IMMUTABLE). `normalize(text, text)` también es `i`, aunque no se usa.
- La tabla pliega también A-Z a a-z y no usa `lower()`, para no depender de `LC_CTYPE`. Python usa la misma tabla.
- La ñ es una letra distinta de la n: «ano» no encuentra «año». La Ñ se pliega a ñ.
- Se acepta que solo se plieguen letras latinas de Europa occidental (riesgo anotado).
- Contrato aprobado: `category`, `q` y los códigos nuevos dentro de `params`.
- El índice espacial, si la medición lo pide, va en un cambio aparte, fuera de las 10 tareas.
- Los caracteres de formato (Cf) en el texto no se rechazan. Orden de proceso del texto: NFC → recorte → vacío → longitud ≤ 64 en puntos de código sobre el NFC → caracteres de control → plegado. El plegado nunca se usa para medir.

## Archivos y responsabilidades
| Archivo | Crea/Modifica | Responsabilidad | RF |
|---|---|---|---|
| backend/conftest.py | M | Opción `--run-measurement`: sin ella, los tests marcados como medición se saltan | RNF Rendimiento |
| backend/apps/assets/tests/test_list_query_plan.py | C | Filas sintéticas, sondeo del entorno de la BD de test y `EXPLAIN (ANALYZE, BUFFERS)`; imprime la tabla que se copia a validation.md | RNF Rendimiento |
| backend/apps/assets/folding.py | C | Puro: `FOLD_SOURCE`, `FOLD_TARGET` y `fold_for_search(text)`, la misma tabla para la columna y para el texto buscado | RF-2 |
| backend/apps/assets/models.py | M | `title_folded = GeneratedField(translate(title, FOLD_SOURCE, FOLD_TARGET), TextField, db_persist=True)` | RF-2 |
| backend/apps/assets/migrations/0005_asset_title_folded.py | C | `AddField` de la columna generada (almacenada); sin RunPython ni índice | RF-2 |
| backend/apps/assets/filters.py | C | Puro: `Filters`, `parse_filters(params)` y `parse_public_query(params)`, que une zona y filtros; códigos por parámetro | RF-3, RF-4 |
| backend/apps/assets/selectors.py | M | `visible_assets_in_zone(*, zone, limit, filters=NO_FILTERS)`: `category__slug` y `title_folded__contains` en el mismo queryset | RF-1, RF-2, RF-4, RF-5, RF-6 |
| backend/apps/assets/views.py | M | Llama a `parse_public_query`; dos `OpenApiParameter` con `required=False` | RF-1 a RF-6 |
| backend/apps/assets/tests/test_folding.py | C | Tabla de Python y columna de la BD coinciden | RF-2 |
| backend/apps/assets/tests/test_filters.py | C | Validación y unión con la zona; módulo puro | RF-3, RF-4 |
| backend/apps/assets/tests/test_selectors.py | M | Casos con filtros; los tests de fugas existentes se parametrizan con filtros | RF-1, RF-2, RF-4 a RF-6 |
| backend/apps/assets/tests/test_public_list_api.py | M | Casos con filtros; cambian `test_unknown_parameters_are_ignored` (381-389) y el test de OpenAPI (891-895); se amplía `assert_error_format` | RF-1 a RF-6 |
| backend/apps/assets/tests/test_models.py | M | `EXPECTED_FIELDS`, `EXPECTED_COLUMNS` y la regla de nulos y valores por defecto con `title_folded` | RF-2 |
| backend/openapi.json | M | Regenerado con `category` y `q` opcionales | RNF Contrato |
| docs/architecture.md | M | `filters.py`, `folding.py`, columna plegada y carpeta `search/` del frontend | — |
| frontend/src/api/schema.gen.ts | M | Regenerado (`npm run api:gen`) | RNF Contrato |
| frontend/src/search/categories.ts | C | `CATEGORY_CHIPS`: 12 identificadores en orden de presentación («Otros» al final) | RF-7 |
| frontend/src/search/filters.ts | C | Puro: `FilterState`, `toggleCategory`, `setText`, `clearFilters`, `appliedFilters`, `hasActiveFilters` y `filtersQuery` | RF-8 a RF-10, RF-12 |
| frontend/src/search/FilterBar.tsx | C | Formulario `role="search"`, campo de búsqueda, borrar texto, «Quitar filtros» y grupo de chips `aria-pressed` | RF-7 a RF-10 |
| frontend/src/search/*.test.ts | C | vitest de lo anterior (react-dom/server para el marcado) | RF-7 a RF-10 |
| frontend/src/api/publicAssets.ts | M | `fetchAssets(box, signal, filters = NO_FILTERS)`: añade `filtersQuery` tras `boxToQuery` | RF-8, RF-9, RF-12 |
| frontend/src/map/loadAssets.ts | M | Pasa los filtros vigentes al fetcher | RF-8, RF-9, RF-12 |
| frontend/src/state/viewState.ts | M | Entrada `filtersActive`; `empty` y `results` llevan `filtered` | RF-11, RF-12 |
| frontend/src/panel/header.ts | M | Textos con filtros (número, incompleta y vacío) | RF-11 |
| frontend/src/panel/ResultsPanel.tsx | M | Cabecera como `h2`; «Quitar filtros» en el vacío con filtros | RF-11 a RF-13 |
| frontend/src/pages/MapPage.tsx | M | Estado y ref de filtros, `h1` oculto, `FilterBar`, disposición en columna, la barra no se pinta con el estilo fallido | RF-7 a RF-13 |
| frontend/src/i18n/es.ts | M | Nombres de las 12 categorías, «Buscar por título», «Borrar texto», «Quitar filtros», textos con filtros y `h1` | RF-7 a RF-13 |
| frontend/src/styles/buttons.css | M | `.chip` y `.chip[aria-pressed="true"]` (azul, marca de verificación, 44 px, sin limón) | RF-7, RF-10 |
| specs/008-search-filters/validation.md | C | Medición antes y después, pruebas de mecanismo, verificación en navegador | Criterios |

## Modelo de datos y migraciones
- `Asset.title_folded = models.GeneratedField(expression=Func(F("title"), Value(FOLD_SOURCE), Value(FOLD_TARGET), function="translate"), output_field=models.TextField(), db_persist=True)`.
  - Django exige `db_persist` explícito (True o False) en el constructor: `generated.py:27-28`. PostgreSQL solo admite columnas almacenadas: `supports_stored_generated_columns = True` y `supports_virtual_generated_columns = False` (`postgresql/features.py:67-68`), y el check de Django rechaza `db_persist=False` con la pista «Set db_persist=True» (`generated.py:151-176`).
  - Rutas del contenedor del backend, `/usr/local/lib/python3.13/site-packages/django/db/...`.
  - La documentación de Django 5.2.18 (`docs/ref/models/fields.txt`, vía Context7) dice que PostgreSQL exige que las funciones de la expresión sean IMMUTABLE y que la expresión sea determinista y solo referencie campos de la misma tabla. `translate` cumple lo primero (catálogo, `provolatile = 'i'`).
- `0005_asset_title_folded`:
  - `AddField`, que emite `ALTER TABLE assets_asset ADD COLUMN title_folded text GENERATED ALWAYS AS (translate("title", '…', '…')) STORED`;
  - PostgreSQL rellena las filas existentes al reescribir la tabla: no hay RunPython ni código de relleno;
  - la reversión es `RemoveField`.
- La BD recalcula la columna en cada INSERT y en cada UPDATE de `title`. Ni `create_asset` ni `_apply_update` cambian, y `make_asset` y `bulk_create` de los tests siguen valiendo.
- `GeneratedField.db_returning = True` (`generated.py:13`): el INSERT gana `RETURNING … "title_folded"`. Los tests que comparan el SQL del INSERT se revisan en T2.
- El título se guarda en NFC al escribirse: `clean_title` (`rules.py:39-47`) llama a `_clean_text`, que hace `unicodedata.normalize("NFC", raw.strip())` (`rules.py:131`), y los servicios lo usan al crear (`services.py:208`) y al editar (`services.py:322`). La BD no lo impone: un título que entre por `bulk_create` o una fixture sin pasar por el servicio puede no estar en NFC, y entonces `translate` no pliega sus letras descompuestas.
- Sin índice nuevo en la 008. Si la medición lo recomienda, va en un cambio aparte, con su migración y OK.
- `title_folded` nunca entra en `PUBLIC_FIELDS` (selectors.py:9-20) ni en el serializer (serializers.py:4-15).
- Generación de la migración (pendiente de OK): `docker compose run --rm --no-deps -e DB_HOST=db-inexistente.invalid -u "$(id -u)" --entrypoint "" backend python manage.py makemigrations assets`.
- Revisión del SQL (pendiente de OK): `docker compose exec backend pytest -q --reuse-db config/tests/test_migrations.py` y después `docker compose exec -e DJANGO_ENV=test backend python manage.py sqlmigrate assets 0005`.
- Aplicación en la BD de desarrollo: solo con OK expreso en ese momento, antes de la comprobación de punta a punta.

### Tabla de plegado (`folding.py`)
- `FOLD_SOURCE` y `FOLD_TARGET` tienen igual longitud (82 parejas): `str.translate` y `translate()` de PostgreSQL borrarían caracteres si el destino fuera más corto.
  - A-Z → a-z (26);
  - ÀÁÂÃÄÅ y àáâãäå → a (12);
  - Ç y ç → c (2);
  - ÈÉÊË y èéêë → e (8);
  - ÌÍÎÏ y ìíîï → i (8);
  - ÒÓÔÕÖ y òóôõö → o (10);
  - ÙÚÛÜ y ùúûü → u (8);
  - Ý, Ÿ, ý y ÿ → y (4);
  - Ñ → ñ (1); la ñ no está en la tabla y queda como está;
  - Æ, Œ y Ø → æ, œ y ø (3).
- `fold_for_search(text) = text.translate(str.maketrans(FOLD_SOURCE, FOLD_TARGET))`. Es 1:1: nunca borra ni añade caracteres.
- Quedan sin plegar las letras fuera de la tabla (por ejemplo Ł, Č, ß, griego y cirílico): distinguen mayúsculas y tildes (riesgo aceptado).

## Contrato de API
### `GET|HEAD /api/v1/public/assets/?south=&west=&north=&east=[&category=][&q=]`
- `south`, `west`, `north` y `east` siguen como en la 006.
- `category` y `q` son opcionales.
  - Ausente: sin filtro.
  - Presente: se valida.
  - Los nombres distinguen mayúsculas: `Category` o `Q` son desconocidos y se ignoran.
- Orden de proceso (sin cambios respecto a la 006):
  1. negociación JSON;
  2. sin autenticación;
  3. `AllowAny`;
  4. límite de peticiones;
  5. método;
  6. **validación de zona y filtros**, dentro de `get`;
  7. selector.
- 200: mismo cuerpo, mismas diez claves, mismo orden, tope de 200 e `incomplete`.
  - `Cache-Control: public, max-age=60`, `Vary: Accept-Encoding`, sin `Set-Cookie` ni `Vary: Cookie`. HEAD igual, sin cuerpo.
  - `category` válido sin categoría que le corresponda: 200 con `{"results": [], "incomplete": false}` (RF-4).

### Errores (formato único de la 006, `no-store`, sin eco del valor)
| Estado | `code` | Cuándo |
|---|---|---|
| 400 | `invalid_parameters` + `params` | Falla algún límite de zona o algún filtro. `params` lleva un código por parámetro que falla: los de la zona (orden de la 006) y después `category` y `q` |
| 400 | `zone_inverted` / `zone_too_large` | Solo si los cuatro límites y los filtros presentes son válidos |
| 405 | `method_not_allowed` | Sin cambios (OPTIONS incluido) |
| 429 | `throttled` + `retry_after` | Sin cambios; se aplica antes de validar los filtros |

Códigos por parámetro (el primero que falle, en este orden):
| Parámetro | Códigos |
|---|---|
| `category` | `repeated` (más de un valor) → `empty` (valor vacío) → `too_long` (> 50 caracteres) → `invalid_format` (no cumple `\A[a-z0-9]+(?:-[a-z0-9]+)*\Z`) |
| `q` | `repeated` → `empty` (vacío o vacío tras recortar) → `too_long` (> 64 puntos de código tras NFC y recorte) → `control_char` (algún carácter Cc) |

- `ERROR_CODES` (core/api.py:9-24) no cambia: los códigos nuevos solo viajan dentro de `params`, que `ApiError` no comprueba (api.py:36-46).

### Permisos (constitución, punto 5)
| Ruta y método | Anónimo | Usuario con sesión | Propietario | Staff |
|---|---|---|---|---|
| GET/HEAD con o sin filtros | 200 con los bienes visibles que cumplen los filtros | Lo mismo que el anónimo | Lo mismo; nunca sus pausados ni la ubicación exacta | Lo mismo |
| Otros métodos, con o sin filtros | 405 (429 con el límite superado) | ídem | ídem | ídem |
- No hay detalle: no hay 404 ni 403 por objeto.

### Descripción legible por máquina
- `OpenApiParameter("category", STR, QUERY, required=False, description="Identificador de categoría…")` y lo mismo para `q`.
  - `_bound_parameter` (views.py:26-33) se queda para los límites; los filtros usan una función hermana con `required=False`.
- Regeneración (pendiente de OK):
  - `docker compose run --rm --no-deps -e DB_HOST=db-inexistente.invalid -u "$(id -u)" --entrypoint "" backend python manage.py spectacular --format openapi-json --file openapi.json --validate --fail-on-warn --lang en`;
  - `cd frontend && npm run api:gen`.
  - La CI compara los dos (ci.yml:44 y :84).

## Lógica
**Backend (funciones puras, sin Django en `folding.py` ni en `filters.py`)**
- `filters.py`:
  - `@dataclass(frozen=True) Filters(category_slug: str | None, title_fragment: str | None)` y `NO_FILTERS`;
  - `parse_filters(params: Mapping[str, list[str]]) -> Filters | dict[str, str]`:
    - `category`: `None` → sin filtro; más de un valor → `repeated`; `""` → `empty`; `len > 50` → `too_long`; sin `SLUG_PATTERN.fullmatch` → `invalid_format`;
    - `q`: `None` → sin filtro; más de un valor → `repeated`; `text = unicodedata.normalize("NFC", value).strip()`; `""` → `empty`; `len(text) > 64` → `too_long`; carácter Cc → `control_char`;
    - si todo es válido, `title_fragment = fold_for_search(text)`;
  - el patrón de categoría se copia de categories/models.py:9 para que el módulo siga puro, y un test exige que sean iguales;
  - `parse_public_query(params) -> PublicQuery | ZoneError`: ejecuta `parse_zone` (sin cambios) y `parse_filters`. Si hay errores de filtros, devuelve `ZoneError("invalid_parameters", {errores de límites, si los hay, y errores de filtros})`; si no, devuelve el `ZoneError` de la zona o `PublicQuery(zone, filters)`.
- `str.strip()` quita los espacios Unicode que reconoce `str.isspace()` (espacio, \t \n \v \f \r, \x1c-\x1f, U+0085, NBSP, U+1680, U+2000-U+200A, U+2028, U+2029, U+202F, U+205F y U+3000). No quita U+200B ni U+FEFF (son Cf): con ellos el texto se busca tal cual y no coincide con ningún título, porque los títulos rechazan Cf salvo ZWJ (rules.py:150-151).
- Selector:
  - `visible_assets_in_zone(*, zone, limit, filters=NO_FILTERS)`; el valor por defecto hace que los tests de la 006 sigan pasando sin modificarse;
  - sobre el mismo queryset (`status="active"`, `owner__is_active=True` y el rango de ST_X y ST_Y), si hay categoría `.filter(category__slug=…)` y si hay texto `.filter(title_folded__contains=…)`;
  - luego `order_by("-created_at", "-id")`, `.values(*PUBLIC_FIELDS)` y `[:limit + 1]`. Una sola consulta.
  - Prohibidos `__regex`, `__icontains` (UPPER depende de LC_CTYPE), `RawSQL`, `extra` y concatenar SQL.
- Vista: `get` llama a `parse_public_query(dict(request.query_params.lists()))`; si hay error lanza `ApiError(code, params)`, y si no, llama al selector con `zone` y `filters`. El resto queda igual (views.py:64-78).

**Frontend (funciones puras, vitest en node)**
- `FilterState = { category: string | null; text: string }`.
  - `toggleCategory(state, slug)` activa, quita si es el mismo o sustituye;
  - `setText(state, raw)` guarda lo escrito;
  - `clearFilters()`.
- `appliedFilters(state) -> { category?: string; q?: string }`: el texto sustituye los Cc por espacio y se recorta; si queda vacío no se envía. Un filtro está activo si está en `appliedFilters`.
- `filtersQuery(applied)`: `URLSearchParams` con orden fijo `category` y después `q`, añadido tras `boxToQuery` (requestBox.ts:61-68). El mismo filtro da siempre la misma URL, que aprovecha la caché de 60 s.
- `fetchAssets(box, signal, filters = NO_FILTERS)`: el tercer argumento es opcional y los tests existentes (publicAssets.test.ts:152-221) no cambian.
- Planificador (scheduler.ts): un chip, Intro, borrar texto, «Quitar filtros» y «Reintentar» usan `runNow()`; escribir usa `schedule()` (300 ms, `REQUEST_DELAY_MS`). `start()` siempre aborta la anterior y `isCurrent()` descarta su respuesta.
- `MapPage` guarda los filtros en estado (para pintar) y en una ref (para que `run` lea los vigentes, como `boundsRef`). Si `appliedFilters` no cambia (por ejemplo, al añadir un espacio final), no se pide de nuevo.
- `viewState({ styleFailed, request, atInitialView, filtersActive })` → `empty { canReset, filtered }` y `results { cards, incomplete, filtered }`.

## Interfaz
- Móvil primero (375 px). La barra de filtros va en el flujo, encima del mapa y del panel:
  - fila 1: `form role="search"` con la etiqueta `sr-only` «Buscar por título» (sin etiqueta visible: la lupa decorativa y el texto de ayuda «Buscar…» orientan), un `input type="search"` (`maxLength=64`, `autoComplete="off"`, sin atributo `name`, `enterKeyHint="search"`) con el botón «Borrar texto» de 44×44 dentro del campo (patrón `.field-box`/`.eye` de fields.css), y «Quitar filtros» al final de la fila, solo con algún filtro activo;
  - fila 2: `div role="group" aria-label="Categorías"` con 12 `button aria-pressed` de 44 px que se desplazan en horizontal (`overflow-x-auto`); cada chip es una parada de Tab y el navegador lo desplaza a la vista al enfocarlo;
  - la barra tiene altura fija (dos filas de 44 px más los márgenes, unos 108 px), así «Quitar filtros» no cambia la altura y no mueve los controles del mapa;
  - desde 900 px, una sola fila: el campo mide 400 px (alineado con la columna del panel) y los chips van a su derecha.
- El mapa (con la atribución y el zoom arriba a la derecha, MapView.tsx:88-89) y el panel quedan debajo de la barra: nada los tapa.
- Chip activo:
  - fondo azul de la identidad (#1647B8) con texto blanco, borde más grueso y una marca de verificación (svg `aria-hidden`), así no depende solo del color;
  - `aria-pressed="true"` lo anuncia como activado;
  - nunca usa el limón; en `forced-colors`, contorno de 2 px como `.btn`.
- El formulario hace `preventDefault` en el envío. Sin `name` ni `action`, el texto no puede acabar en la URL aunque falle el JS, y `autoComplete="off"` evita el historial de formularios.
- Foco: al pulsar «Quitar filtros» en la barra, el foco va al campo de búsqueda; en el panel, a la cabecera (patrón `focusHeader`, ResultsPanel.tsx:42-44).
- Estados del panel:
  - carga: «Buscando bienes…»;
  - resultados con filtros: «1 bien en esta zona con estos filtros», «N bienes en esta zona con estos filtros», «Mostrando N bienes con estos filtros. Puede haber más: acerca el mapa para verlos todos»;
  - vacío con filtros: «No hay bienes en esta zona con estos filtros» con «Quitar filtros» (y además «Volver a la zona inicial» si no está en la vista inicial);
  - vacío sin filtros y «Acerca el mapa…»: igual que en la 006; los filtros siguen activos;
  - error: el mensaje de la 006 con «Reintentar», que repite la petición con los mismos filtros.
- Región de estado (`role="status"`, ResultsPanel.tsx:56): la cabecera pasa de `<p>` a `<h2>` dentro de la región y se anuncia una vez por petición.
- `h1` oculto con `sr-only` como primer hijo de `main` en MapPage: «Bienes en alquiler en el mapa», distinto de la etiqueta del canvas («Mapa de bienes en alquiler»).
- Con el estilo fallido no se pintan ni la barra ni el panel: quedan el `h1` y el mensaje con `role="alert"` (MapView.tsx:164-172).
- Movimiento reducido: los chips solo tienen transiciones dentro de `prefers-reduced-motion: no-preference`, y el desplazamiento al foco es el nativo.
- Categoría desconocida para el cliente: no tiene chip; su bien sale en la lista con su `category_name` y la imagen de «other» (categoryImage.ts:19-21).

## Medición del rendimiento
- Sitio: `apps/assets/tests/test_list_query_plan.py`, marcada como medición. Solo corre con `--run-measurement` y siempre en la BD de test.
  - Orden (cada una con OK): `docker compose exec backend pytest -q -s --run-measurement apps/assets/tests/test_list_query_plan.py`.
  - Después de una migración, con `--create-db`.
- Sondeo del entorno (impreso, sin aserciones): `SHOW server_version`, `SHOW lc_ctype`, `SHOW server_encoding`, y la volatilidad de `translate`.
- Volumen:
  - 500 propietarios (5 desactivados) y 50 000 bienes con `random.Random(8)`: 80 % activos y 20 % pausados;
  - el 40 % en un cuadrado de 1°×1° alrededor de Valencia (39–40, −1–0) y el 60 % repartido por la caja de coherencia (27,5–44; −18,5–5);
  - categorías: las 12 sembradas («kayak» ~8 %, «ski» ~2 %);
  - títulos combinando una lista de 40 sustantivos con y sin tildes, un adjetivo y un número; ninguno contiene «zzzz»;
  - `created_at` repartido en 365 días;
  - `bulk_create` en lotes de 5000 y luego `ANALYZE assets_asset`, dentro de la transacción del test, que se revierte.
  - Los bienes se crean sin pasar por el servicio, así que los títulos del generador están en NFC por construcción.
- Zonas: Z1 típica de 0,4°×0,4° en Valencia (39,3–39,7; −0,6 – −0,2) y Z2 máxima de 6 grados² (38,5–40,5; −2–1).
- Consultas en Z1 y Z2: sin filtro; categoría `kayak`; categoría `ski`; texto «bici»; peor selectividad con texto de 1 carácter («a») y de 2 («es»); texto sin coincidencias («zzzz», obliga a recorrer todo); categoría y texto a la vez.
- Antes (T1):
  - sin filtro con el selector real: se captura su SQL con `CaptureQueriesContext` y se ejecuta `EXPLAIN (ANALYZE, BUFFERS) <sql>`;
  - las consultas candidatas con filtros se construyen en el propio módulo (mismo encadenado que selectors.py:26-38, más `category__slug` o `title__icontains`), porque la columna plegada aún no existe.
- Después (T6): todo con el selector real y sus filtros; las candidatas se borran.
- Por consulta: 1 ejecución de calentamiento y 5 medidas. Se registran la mediana de «Execution Time», el nodo de acceso a assets_asset, «Rows Removed by Filter» y los buffers compartidos.
- Criterios:
  - sin filtro no empeora: la mediana de después en Z1 y Z2 es ≤ la de antes × 1,10 + 1 ms, con el mismo nodo de acceso;
  - umbral con filtro: categoría y «bici» en Z1 ≤ 1,5 × la mediana sin filtro de después en Z1;
  - los peores casos (1 y 2 caracteres, «zzzz» y Z2) se registran sin umbral.
- Si un criterio falla, se registra con su propuesta y no bloquea la entrega.
- Recomendación de índice: si en Z2 sin filtro el plan recorre assets_asset entero (Seq Scan con «Rows Removed by Filter» > 80 % de la tabla) y la mediana supera 20 ms, se propone, en un cambio aparte, un índice GiST funcional sobre `public_location::geometry`:
  - la consulta añade `&&` con `ST_MakeEnvelope(w, s, e, n, 4326)` como prefiltro y mantiene ST_X/ST_Y como refinado, así no cambia el criterio de pertenencia de la 006;
  - se descarta `ST_MakeEnvelope(...)::geography` sobre el GiST actual, porque en geography los lados son arcos de círculo máximo y cambiaría qué bienes entran en los bordes.

## Decisiones
| Decisión | Opciones | Elegida | Qué evita | Coste |
|---|---|---|---|---|
| D1 Comparación sin tildes ni mayúsculas | a) unaccent; b) columna normalizada escrita por los servicios; c) colación ICU no determinista; d) columna generada con `translate()` y tabla fija | d | Extensión nueva (a), desincronización y relleno con RunPython (b), dependencia de la versión menor de PostgreSQL (c) | Migración 0005; solo pliega letras latinas de Europa occidental |
| D2 Dónde se valida | A) función pura dentro de `get`; B) serializer o filter_backend | A | B correría en `initial()`, antes o al margen del límite, y con mensajes de DRF que repiten el valor | Una función más en `get` |
| D3 Nombres y códigos | A) `category`, `q`, códigos en `params`; B) `category_slug`, `text`; C) códigos generales nuevos | A (contrato aprobado) | C obligaría a tocar `ERROR_CODES` y el cliente | Cambiar el test de parámetros desconocidos |
| D4 Unión de errores de zona y filtros | A) `invalid_parameters` con todos los parámetros que fallan; la semántica de zona solo con todo válido; B) dos códigos generales | A | B rompe el formato único (un solo `code`) | La zona invertida se ve después de corregir el filtro |
| D5 Origen de los chips | A) lista fija en el cliente; B) endpoint público de categorías | A | B: contrato nuevo, otra superficie de permisos, límite y caché | Una categoría nueva necesita su imagen y un despliegue del frontend, que ya hacían falta |
| D6 Contenido del chip | A) solo nombre; B) imagen y nombre | A | Fila más ancha a 375 px y más peso | Menos reconocible de un vistazo |
| D7 Espera del buscador | A) 300 ms con el planificador del mapa; B) temporizador propio de 400 ms | A | Dos caminos de cancelación que podrían pintar una respuesta vieja | Algo más de peticiones al escribir despacio |
| D8 Disposición | A) barra en el flujo encima del mapa; B) superpuesta arriba a la izquierda | A | B choca con la atribución no compacta y el zoom a 375 px | Unos 108 px menos de mapa a 375 px |
| D9 Encabezados | A) `h1` oculto y cabecera del panel como `h2`; B) `h2` fijo visible «Bienes en esta zona» | A | B quita una línea al panel de 40dvh | El texto del `h2` cambia con el estado |
| D10 Medición | A) test de pytest con opción propia; B) comando de gestión | A | B correría con los ajustes de desarrollo y tocaría su BD | Una opción en conftest.py |
| D11 Índice espacial | A) medir y decidir después, en un cambio aparte; B) GiST funcional ya; C) GiST de geography con envolvente geography | A | C cambia los bordes de la 006; B es una migración sin datos que la justifiquen | Posible cambio posterior |

### Comparación sin tildes ni mayúsculas (D1)
| Opción | Ventajas | Inconvenientes | ñ | Extensión o dependencia |
|---|---|---|---|---|
| a) `unaccent` (`title__unaccent__icontains`) | Cubre muchos alfabetos; sin columna nueva | Extensión nueva y `django.contrib.postgres` en INSTALLED_APPS (hoy no está, base.py:9-20); `icontains` genera `UPPER(…)`, que depende de `LC_CTYPE`; `unaccent()` es STABLE (supuesto), así que un índice funcional exige un envoltorio IMMUTABLE propio; recorre la tabla | Las reglas por defecto pliegan ñ → n; separarlas exige un fichero de reglas propio en la imagen | Extensión: necesitaría aprobación expresa |
| b) Columna normalizada calculada en Python por los servicios (NFKD, sin Mn, casefold) | Unicode completo; sin extensión; igual en la BD de test | Desincronización: `create_asset` y `_apply_update` deben escribirla; migración con RunPython de relleno; `make_asset` y los `bulk_create` de los tests construyen `Asset(...)` directamente; NFKD cambia caracteres de compatibilidad; casefold alarga (ß → ss); un texto de solo marcas combinantes queda vacío al plegar y el LIKE coincidiría con todo | NFKD separa ñ en n + U+0303: ñ → n salvo excepción explícita | Ninguna; migración |
| c) Colación ICU no determinista (`CreateCollation(..., provider="icu", deterministic=False)` y `Collate("title", …)` con `contains`) | Sin columna; reglas de idioma de ICU | LIKE con colaciones no deterministas existe desde PostgreSQL 18 (notas de la versión 18, «Allow LIKE with nondeterministic collations», postgresql.org/docs/18/release-18.html); ILIKE y regex no lo admiten; PostgreSQL 18.6 corrige un fallo con `\` (release-18-6) y la versión menor real es desconocida (etiqueta flotante `postgis/postgis:18-3.6`, docker-compose.yml:3); penalización de rendimiento, sin índice btree útil, se supone ICU en la imagen, necesita `django.contrib.postgres` y es difícil de probar | Con `und-u-ks-level1`, ñ = n; con `es-u-ks-level1` podría mantenerse distinta (supuesto) | Colación nueva por migración y `django.contrib.postgres`: necesitaría aprobación expresa |
| d) Columna generada `translate(title, FOLD_SOURCE, FOLD_TARGET)` almacenada, con la misma tabla en Python para el texto buscado | Sin extensión ni dependencia; la BD la recalcula en cada escritura y no puede desincronizarse; servicios, fixtures y demo intactos; no depende de `LC_CTYPE` (no usa `lower`); 1:1, así que el plegado nunca vacía el texto; la ñ se elige; un test prueba carácter a carácter que Python y la BD coinciden | Solo pliega las letras de la tabla: Ł, Č, ß, griego o cirílico siguen distinguiendo mayúsculas y tildes; ampliar la tabla es otra migración que reescribe la tabla; depende de que el título esté en NFC; una letra descompuesta (a + U+0301) no se pliega | Distinta de la n; Ñ → ñ | Ninguna; migración |

## Respuestas a las Dudas abiertas de la spec
| Duda | Respuesta |
|---|---|
| Nombres de los parámetros y códigos nuevos | `category` y `q`. Códigos en `params`: `repeated`, `empty`, `too_long`, `invalid_format` (categoría) y `control_char` (texto). El código general sigue siendo `invalid_parameters` (D3, D4) |
| Espacio en blanco al recortar y comparación sin tildes (¿ñ = n?) | `str.strip()`, igual que los títulos (ver Lógica). Comparación: D1 (d). La ñ es distinta de la n y la Ñ se pliega a ñ |
| De dónde salen los chips y qué hace el cliente con una categoría que no conoce | Lista fija de 12 en el cliente (D5). Una categoría desconocida no tiene chip; sus bienes salen en la lista con su nombre de la API y la imagen de «other» |
| ¿Imagen o solo nombre? | Solo nombre (D6) |
| Espera, umbral y volumen | 300 ms (D7); umbrales y 50 000 filas en Medición |
| Qué cambia en la consulta si la medición lo exige | Índice GiST funcional sobre `public_location::geometry` con `&&` y `ST_MakeEnvelope` como prefiltro, manteniendo ST_X/ST_Y; cambio aparte, fuera de las 10 tareas |
| Disposición a 375 px | Barra de altura fija en el flujo, encima del mapa (D8) |
| Texto de los encabezados y qué queda con el estilo fallido | `h1` oculto «Bienes en alquiler en el mapa»; `h2` = cabecera del panel; con el estilo fallido solo el `h1` y el mensaje de alerta (D9) |
| [NECESITA ACLARACIÓN] Categoría nueva que el cliente no conoce | Sin chip hasta actualizar el cliente; sus bienes se ven sin filtro y con el filtro de texto. No es un error ni rompe la validación (validate.ts:16 no restringe el slug) |

## Blast radius
- Backend:
  - views.py:43-60: parámetros en `extend_schema` y llamada al parseo;
  - selectors.py:23-41: nuevo argumento con valor por defecto;
  - models.py:52-73: campo nuevo;
  - migración 0005; zone.py y test_zone.py sin cambios.
- test_public_list_api.py:
  - 381-389 (`{"category": "pool"}` y `{"q": "taladro"}` dejan de ser desconocidos, y «pool» es una categoría sembrada, 0002_seed_categories.py:10): se cambian por nombres desconocidos y por las variantes con mayúsculas (`Category`, `Q`);
  - 891-895: el conjunto de parámetros pasa a seis, y `required` es True solo en los cuatro límites;
  - 56-62 (`PLANNED_CODES`) no cambia.
- test_models.py:65-99 (`EXPECTED_FIELDS` y `EXPECTED_COLUMNS` ganan `title_folded`) y 113-119 (la regla de valor por defecto y nulo con la columna generada).
- Tests que comparan el SQL del INSERT: `RETURNING` gana la columna generada (se revisan en T2). test_migrations.py debe cuadrar con 0005.
- test_selectors.py:474-528: siguen igual sin filtros; los casos con filtros son nuevos.
- test_architecture.py y test_core/test_api.py:69: sin cambios (los servicios no se tocan y `ERROR_CODES` queda igual).
- backend/conftest.py (opción nueva) y openapi.json:317-349 (dos parámetros más).
- Frontend: publicAssets.ts:74-78, loadAssets.ts:14-47, viewState.ts:27-65, header.ts:5-32, ResultsPanel.tsx:18-60, MapPage.tsx:13-92, es.ts:69-101, schema.gen.ts y los tests de cada uno.
- La posición del aviso flotante (useFreeZoneTop.ts) depende de dónde quedan los controles del mapa: con la barra encima, se comprueba en el navegador.

## Riesgos
| Riesgo | Mitigación |
|---|---|
| A 375 px la barra (unos 108 px) y el panel (40dvh) dejan poco mapa | Altura fija y compacta; se mide en el navegador a 375×667. El panel colapsable es de la 007 |
| Con (d), las letras fuera de la tabla distinguen mayúsculas y tildes (riesgo aceptado) | Ampliar la tabla es una migración posterior |
| Un título que no esté en NFC (entrada por `bulk_create` o fixture, no por el servicio) no se pliega bien | Los servicios lo guardan en NFC (rules.py:131); el test de plegado usa letras precompuestas; la BD no lo impone |
| `translate` no fuese IMMUTABLE | Comprobado: `provolatile = 'i'` en el contenedor de la BD; si la migración fallase, lo haría en la BD de test y no en silencio |
| Un texto de 1 o 2 caracteres en la zona máxima obliga a recorrer y ordenar muchos bienes | Medición de peor caso; el límite por IP sigue; índice en un cambio aparte si hace falta |
| El aviso flotante queda mal anclado si la barra cambia de altura | Altura fija; comprobación en el navegador con y sin filtros |
| El texto queda en el log de accesos de runserver junto a la IP | Aceptado en la spec para desarrollo; retención en la 011 |
| Un título de tarea supera los 30 min (T5, T8) | Se avisa al llegar; T5 puede partirse en dos commits (vista y contrato) |

## Estrategia de tests
Regla de este plan: cada test lleva el fallo concreto que lo pone en rojo. Un test sin fallo plausible no entra.

### Backend (pytest)
- B1. Misma consulta con activo, cuenta activa y zona, con categoría y con texto coincidentes (selector y API).
  - Rojo si: el filtro se aplica sin `status="active"` o sin `owner__is_active=True`, y aparecen un bien pausado o uno de una cuenta desactivada.
- B2. Comodines literales: «%», «_», «\», «.*» y comillas solo coinciden con títulos que los contienen.
  - Rojo si: el texto se compara con un patrón sin escapar, y «%» devuelve todos los bienes.
- B3. RF-2, solo el título: textos iguales a la descripción, al email del propietario, a una coordenada y al nombre de la categoría («Piscina», con título sin esa palabra) no encuentran nada.
  - Rojo si: el filtro mira también `description`, el propietario o `category__name`.
- B4. `q` con solo caracteres de formato (U+200B, U+202E) o solo marcas combinantes (U+0301) no devuelve todo.
  - Rojo si: el recorte o el plegado vacía el texto y el patrón queda en `%%`.
- B5. Plegado: cada carácter de `FOLD_SOURCE`, plegado en Python, coincide con `title_folded` de la BD (título de un carácter insertado con `make_asset`), y lo mismo con algunos de fuera de la tabla (Ł, ß, ж, α), que quedan igual en las dos. Además, `FOLD_SOURCE` y `FOLD_TARGET` tienen la misma longitud y no repiten caracteres.
  - Rojo si: una pareja de la tabla está solo en Python o solo en la expresión del modelo, o si el destino es más corto (`translate` borraría caracteres).
- B6. Comparación: «esqui» encuentra «Esquí»; «BICI» encuentra «bicicleta»; «ESQUÍ» encuentra «esqui»; el fragmento al principio, en medio y al final; un texto en NFD igual que en NFC; «ano» no encuentra «año» y «año» sí; «AÑO» encuentra «año».
  - Rojo si: se pliega solo una de las dos partes, no se pasa el texto a NFC o la ñ se pliega a n.
- B7. Validación pura de `parse_filters` y `parse_public_query` (test_filters):
  - repetido, `?q=` y `?q` sin `=`, solo espacios (incluidos NBSP y U+3000, con escapes) → `empty`;
  - 64 aceptado, 65 rechazado, 64 rodeado de espacios aceptado, y 65 en NFD que son 64 en NFC aceptado → rojo si se mide antes de NFC o antes de recortar;
  - Cc interior → `control_char`; U+200B pasa y no rechaza (los Cf no se rechazan);
  - identificadores `-ski`, `ski-`, `sports--area`, `ski\n`, con mayúsculas, de 51 caracteres, vacío y repetido → error → rojo si se usa `re.match` con `$` en lugar de `fullmatch` o si se mide la longitud después del patrón; `sports-area` y `ski` válidos;
  - el patrón de categoría es igual al de categories/models.py:9 → rojo si una de las dos copias cambia;
  - unión: `south=abc&q=` da los dos códigos; zona invertida con `q` demasiado largo da solo `q`, y al corregirlo, `zone_inverted` → rojo si la semántica de zona se evalúa antes que los filtros.
- B8. API, petición 61 con filtros inválidos da 429, no 400.
  - Rojo si: los filtros se validan antes del límite de peticiones (en `initial()`).
- B9. API, errores sin eco y `no-store`: se amplía `assert_error_format` (test_public_list_api.py:153) y `test_input_errors_are_not_stored_and_do_not_echo_the_values_or_log_them` (361) con los valores enviados de `category` y `q`. Además, una petición 200 con un `q` centinela, con los logs al nivel de producción (INFO), no deja el texto en `caplog`.
  - Rojo si: el cuerpo del error o un log incluye el valor recibido, o falta `Cache-Control: no-store`.
- B10. RF-1, RF-4 y RF-6 en selector y API: la categoría filtra; una categoría válida que no existe da 200 con lista vacía e `incomplete=false`; categoría y texto juntos devuelven solo los que cumplen los dos; un bien que coincide con el texto pero está fuera del cuadro no aparece, con y sin categoría.
  - Rojo si: se responde 400 o 404 a la categoría inexistente, los filtros se combinan con O, o el texto se aplica fuera del rango de la zona.
- B11. RF-5, tope: con 201 bienes que cumplen el filtro se devuelven 200 e `incomplete=true`; con 201 en la zona pero solo 5 que cumplen, `incomplete=false`.
  - Rojo si: el filtro se aplica después del `LIMIT` o el tope se cuenta antes de filtrar.
- B12. Tests de fugas de la lista pública parametrizados con «sin filtro / categoría / texto / ambos»: mismo cuerpo para anónimo, propietario y staff (`force_login`); lista blanca de claves de la fila y del SELECT; SQL sin `exact_location` ni `description`; respuesta sin ubicación exacta. Los de crear, editar o borrar (test_leaks.py) no se tocan.
  - Rojo si: el filtro añade `exact_location`, `description` u otra columna al SELECT o a la respuesta, o resuelve el filtro en una segunda consulta.
- B13. Contrato: `test_the_openapi_description_is_valid_and_documents_the_list` (891-895) pasa a seis parámetros con `required` True solo en los cuatro límites, y `test_unknown_parameters_are_ignored` (381-389) usa nombres que de verdad son desconocidos.
  - Rojo si: `openapi.json` se queda con la descripción antigua o los filtros son obligatorios.

### Excluidos, con el motivo
- `Vary: Cookie` con filtros: la spec lo describe en un caso límite (specs/008-search-filters/spec.md:130, «Llegan la misma petición con filtros con y sin cookie de sesión: la respuesta es la misma y no se declara variable por `Cookie` (RF-5).») pero el criterio de finalización de RF-5 no lo lista (spec.md:176, «…los mismos campos, el mismo orden, el tope, la marca de lista incompleta, la caché pública de 60 s y `no-store` en los errores (RF-5).»). Los filtros no tocan la sesión ni las cookies; ya lo prueban test_public_list_session.py:95-134 y test_public_list_api.py:662-744 sobre la misma vista.
- HEAD y OPTIONS con filtros: la spec lo describe en un caso límite (spec.md:129) y no lo pide como test. El método se resuelve antes de leer la query, y ya lo prueban test_public_list_api.py:575 y 588.
- Columna plegada en el SELECT: lo cubre el test existente `test_the_select_clause_has_no_columns_outside_the_whitelist` (test_selectors.py:513).

### Frontend (vitest)
- F1. `appliedFilters` y `filtersQuery`: el texto se recorta, los Cc pasan a espacio, un texto vacío no genera `q`; el espacio, `&`, `%`, `#`, ñ y un emoji se codifican; el orden `category` → `q` es fijo.
  - Rojo si: se envía `q=` vacío (el servidor respondería 400) o un `&` sin codificar corta el parámetro.
- F2. `toggleCategory`: activar, quitar al pulsar la misma y sustituir.
  - Rojo si: quedan dos categorías activas o no se quita al repetir.
- F3. `CATEGORY_CHIPS` es igual a `CATEGORY_KEYS` (testing/categoryKeys.ts), cada uno con nombre en es.ts y «Otros» al final.
  - Rojo si: se añade una categoría con imagen y sin chip, o con chip y sin nombre.
- F4. `viewState`, `statusText` y `headerText` con filtros: vacío con filtros muestra «Quitar filtros» y no «Volver a la zona inicial» cuando ya está en la vista inicial; «Acerca el mapa…» no cambia; con un error, los filtros no cambian.
  - Rojo si: el vacío con filtros muestra el texto de sin filtros, o un error borra los filtros.
- F5. «Reintentar» repite la petición con los mismos filtros (loadAssets).
  - Rojo si: el reintento llama al fetcher sin filtros.
- F6. Marcado de `FilterBar` (react-dom/server): grupo con etiqueta, chips `aria-pressed`, campo con etiqueta «Buscar por título», `maxLength=64`, sin `name`, `autoComplete="off"`, «Quitar filtros» solo con filtro activo.
  - Rojo si: se añade un `name` al campo (el texto podría ir a la URL), falta `aria-pressed` o «Quitar filtros» sale sin filtro.
- F7. `ResultsPanel`: la cabecera es un `<h2>` dentro de la región de estado y el vacío con filtros pinta «Quitar filtros».
  - Rojo si: la cabecera vuelve a ser un `<p>` o falta el botón.

### Verificación en navegador (Chrome DevTools a 375 y 1280 px; se registra en validation.md)
- RF-7: fila de chips recorrible con Tab hasta el último, sin tapar la atribución ni el zoom, controles de 44 px.
- RF-8: cada clic pide una vez y cancela la anterior (pestaña de red).
- RF-9: espera de 300 ms, Intro inmediato, y borrar quita el filtro.
- RF-10: chip activo y texto visibles, y «Quitar filtros» devuelve las 24 tarjetas de la demostración.
- RF-11: mensaje y anuncio de la región de estado con filtros sin resultados.
- RF-12: error simulado (red cortada y 500) con «Reintentar».
- RF-13: árbol de accesibilidad con un solo `h1` oculto y la cabecera del panel como `h2`; con el estilo bloqueado, solo el `h1`.
- Privacidad: la URL no cambia al filtrar, `localStorage` y `sessionStorage` quedan vacíos, y la red solo va al propio origen y a OpenFreeMap.
- Accesibilidad: teclado, foco visible, contraste AA del chip activo, sin limón, movimiento reducido emulado y consola sin errores.

### Trazabilidad RF → verificación
| RF | Verificación |
|---|---|
| RF-1 | B1, B10 y navegador (un chip deja solo sus tarjetas y círculos con la demostración) |
| RF-2 | B2, B3, B5, B6 |
| RF-3 | B4, B7, B8, B9 |
| RF-4 | B10 |
| RF-5 | B11, B12, B13 |
| RF-6 | B10 y navegador (chip y texto a la vez) |
| RF-7 | F3, F6 y navegador |
| RF-8 | F1, F2 y navegador |
| RF-9 | F1 y navegador |
| RF-10 | F2, F6 y navegador |
| RF-11 | F4, F7 y navegador |
| RF-12 | F4, F5 y navegador |
| RF-13 | F7 y navegador |
| RNF Rendimiento | Medición antes y después (T1, T6) en validation.md |
| RNF Contrato | CI (`spectacular --validate --fail-on-warn` y `diff`) y `npm run api:check` |

### Pruebas de mecanismo (privacidad y seguridad; sobre copias, con sha256 antes y después)
Solo cuatro, todas en el backend. En cada una, el test indicado debe ponerse en rojo.
- M1. Quitar `status="active"` o `owner__is_active=True` del queryset filtrado (T4) → B1.
- M2. Buscar también en `description` (T4) → B3.
- M3. Quitar el escape de comodines: comparar con un LIKE sin escapar, `.extra(where=["title_folded LIKE %s"], params=[f"%{fragment}%"])`, en lugar de `contains` (T4) → B2, porque «%» devuelve todos los bienes.
- M4. Desincronizar la tabla de Python de la de la BD, quitando una pareja solo en Python o solo en la expresión del modelo (T2) → B5.

## Reparto estimado en tareas (10)
- T1. Medición inicial del plan de la consulta (RNF Rendimiento).
- T2. Título plegado como columna generada (RF-2); mutación M4.
- T3. Validación pura de los filtros y unión con la zona (RF-3, RF-4).
- T4. Selector con filtros (RF-1, RF-2, RF-4, RF-5, RF-6); mutaciones M1, M2 y M3.
- T5. Endpoint con filtros y contrato (RF-1 a RF-6).
- T6. Medición después y decisión sobre el índice (RNF Rendimiento).
- T7. Estado de filtros y petición filtrada (RF-8, RF-9, RF-10, RF-12).
- T8. Barra de filtros: buscador y chips (RF-7 a RF-10).
- T9. Panel con filtros y encabezados de la pantalla (RF-11 a RF-13).
- T10. Validación de punta a punta y en el navegador (RF-1 a RF-13).
- El índice GiST, si la medición lo pide, queda fuera de estas 10 tareas.

## Afirmaciones no verificadas
**Verificado en este repositorio o en el contenedor:**
- En el catálogo de la base `postgres` del contenedor `db` (imagen `postgis/postgis:18-3.6`), `translate(text, text, text)` y `normalize(text, text)` tienen `provolatile = 'i'`.
- En el contenedor del backend, `GeneratedField` tiene `db_returning = True` (`generated.py:13`), exige `db_persist` verdadero o falso (`generated.py:18, 27-28, 32`) y comprueba el soporte del backend (`generated.py:123-128, 151-176`). PostgreSQL declara `supports_stored_generated_columns = True` y `supports_virtual_generated_columns = False` (`postgresql/features.py:67-68`).
- La documentación de Django 5.2.18 (Context7, `docs/ref/models/fields.txt`) pide funciones IMMUTABLE en PostgreSQL y expresiones deterministas que solo referencien campos de la misma tabla.
- El título se guarda en NFC al escribirse (`rules.py:39-47, 131`; `services.py:208, 322`).
- `test_public_list_api.py:381-389` usa `{"category": "pool"}` y `{"q": "taladro"}` como parámetros desconocidos, y «pool» es una categoría sembrada (0002_seed_categories.py:10).
- La vista valida dentro de `get` (views.py:59-62); `_bound_parameter` fuerza `required=True` (views.py:26-33); `ApiError` solo comprueba el código general (core/api.py:36-38) y el `no-store` lo pone core/api.py:70.
- `SLUG_PATTERN = r"\A[a-z0-9]+(?:-[a-z0-9]+)*\Z"` (categories/models.py:9); `contains_control_character` solo cubre Cc (core/text.py:6); los títulos rechazan Cf salvo ZWJ (rules.py:150-151).
- `public_location` tiene el GiST de geography por defecto y `exact_location` no tiene índice (models.py:66-69).

**Supuestos (se comprueban en un test, en el sondeo de T1 o en el navegador):**
- Los parámetros de la expresión (`Value(FOLD_SOURCE)`, `Value(FOLD_TARGET)`) se incrustan bien en la DDL de la migración: se revisa con `sqlmigrate` en T2.
- `contains` de Django escapa `\`, `%` y `_`: lo fija B2, que se pone en rojo si no lo hace.
- `?q` sin `=` llega como `['']` (QueryDict): lo fija B7.
- PostgreSQL acepta `NOT NULL` en la columna generada tal como la emita Django: se revisa con `sqlmigrate`.
- `CaptureQueriesContext` devuelve el SQL con los valores ya ligados y se puede anteponer `EXPLAIN (ANALYZE, BUFFERS)`: se comprueba en T1.
- DRF ejecuta `check_throttles` en `initial()` antes de `get`: lo fija B8.
- La versión menor de PostgreSQL 18 no se conoce (etiqueta flotante); solo afectaba a la alternativa c.
- Contraste AA del chip activo (blanco sobre #1647B8): calculado, no medido.
- Chrome no guarda en el historial de formularios un campo sin `name` y con `autoComplete="off"`.

## Skills que aplican
- sdd y django-drf.
- frontend-design y web-design-guidelines (.agents/skills/).
- Mientras no existan las skills react-ts y testing: jsdom no calcula layout (la fila de chips y la barra se comprueban en el navegador) y los mocks de fetch respetan AbortSignal.
