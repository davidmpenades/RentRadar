# Tareas 006 — Mapa público: ver los bienes

- [x] **T1. DRF con su formato de errores y no-store.** RF-3, RF-5 (formato), RNF Errores, Dependencias
  - Dependencias de Python aprobadas (tabla del plan, con versiones exactas y hashes).
  - Qué: backend/requirements.in, requirements.txt (pip-compile con hashes, sin typing_extensions), config/settings/base.py (INSTALLED_APPS, REST_FRAMEWORK, SPECTACULAR_SETTINGS), apps/core/api.py (`ApiError`, manejador y tabla de códigos), apps/core/negotiation.py (negociación), apps/core/tests/test_api.py, config/tests/test_api_settings.py.
  - Por qué: el manejador de DRF da el formato único y `no-store` sin tocar Django. Los handlers globales se descartan: son de la 011.
  - Pruebas: ajustes (un renderer, autenticación vacía, `IsAuthenticated` por defecto, `NUM_PROXIES=0`, `URL_FORMAT_OVERRIDE` None); el manejador con `ApiError`, `MethodNotAllowed` y `Throttled` da el formato, `no-store`, `Retry-After` y nunca `detail`; conjunto de códigos igual a la tabla.
  - Revisar: el diff del lock (hashes x86_64 y aarch64 de rpds-py y PyYAML).
  - Commit: `build(api): add drf with uniform error format`
  - Hecho cuando: la imagen se construye con `--require-hashes` y pytest y ruff están en verde.

- [x] **T2. Identificador público UUID v4 con migración en tres ficheros.** RF-2
  - PARAR: OK previo (migración y privacidad). `migrate` en la BD de desarrollo solo con OK en ese momento.
  - Qué: apps/assets/models.py, migraciones 0002, 0003 y 0004, tests/test_models.py, tests/test_public_id.py.
  - Por qué: un default de AddField daría el mismo UUID a todas las filas. Se descarta generarlo en el servicio: rompería `make_asset`.
  - Pruebas: casos de RF-2 de la Estrategia, más `sqlmigrate` revisado. Mutaciones.
  - Revisar: el SQL de las tres migraciones y el `reverse_code`.
  - Commit: `feat(assets): add public_id uuid with backfill`
  - Hecho cuando: pytest en verde con `--create-db`, `makemigrations --check` limpio y mutaciones registradas en validation.md.

- [x] **T3. Validación de la zona en una función pura.** RF-3
  - PARAR: OK previo (validación de entrada).
  - Qué: apps/assets/zone.py y tests/test_zone.py.
  - Por qué: los campos de DRF aceptarían `1e1`, NaN o espacios y no dan Decimal exacto. Se descarta `serializers.DecimalField`.
  - Pruebas: casos de RF-3 de la Estrategia. Mutaciones.
  - Revisar: la gramática y el orden de los códigos.
  - Commit: `feat(assets): validate public map zone`
  - Hecho cuando: pytest y ruff en verde y mutaciones registradas.

- [x] **T4. Selector de la lectura pública.** RF-1, RF-2, RF-4
  - PARAR: OK previo (privacidad). Depende de T2.
  - Qué: apps/assets/selectors.py y tests/test_selectors.py.
  - Por qué: la lista blanca no carga la exacta y el rango sobre coordenadas coincide con la definición de zona. Se descarta `ST_Intersects` sobre geography.
  - Pruebas: casos de RF-1 y RF-4 de la Estrategia contra la BD. El selector devuelve exactamente las diez claves de la lista blanca, sin `id`, `owner` ni `exact_location`, y `latitude` y `longitude` coinciden con la ubicación pública del bien y no con la exacta. Prueba aplazada desde la T2. Mutaciones.
  - Revisar: el SQL capturado.
  - Commit: `feat(assets): add public assets selector`
  - Hecho cuando: pytest y `test_architecture` en verde y mutaciones registradas.

- [x] **T5. Endpoint GET /api/v1/public/assets/ con caché, límite y respuesta idéntica.** RF-1, RF-2, RF-3, RF-4, RF-5
  - PARAR: OK previo (seguridad, privacidad y contrato de la API). Depende de T1, T3 y T4.
  - Qué: apps/assets/{views,serializers,urls}.py (vista, `PublicListThrottle`, `extend_schema`), config/urls.py, apps/core/middleware.py (`mark_response_cookieless` y `CleanMarkedResponseMiddleware`), base.py (MIDDLEWARE con el nuevo el primero), backend/conftest.py (`cache.clear()` autouse), tests/test_public_list_api.py, apps/core/tests/test_middleware.py, docs/architecture.md.
  - Por qué: `AnonRateThrottle` con `NUM_PROXIES=0` cubre RF-5 sin código propio. El middleware actúa solo sobre las respuestas que la vista marca expresamente, así ninguna vista futura bajo `/api/` pierde sus cookies; es la única forma de quitar las que Session y CSRF añaden después de la vista. `http_method_names` hace que OPTIONS dé 405. `parse_zone` recibe un `Mapping` de listas, así que la vista le pasa `dict(request.GET.lists())`.
  - Pruebas: casos de RF-1 a RF-5, Permisos, Caché, Respuesta idéntica (con `csrftoken` mal formado y `sessionid` corta), Errores y Logs de la Estrategia; el middleware deja limpia la respuesta marcada y conserva las cookies de una sin marcar; `spectacular --validate --fail-on-warn` limpio. Conjunto exacto de claves de la raíz y de cada bien en el JSON, sin `id` ni ubicación exacta, y las coordenadas de cada bien son las de la ubicación pública. Prueba aplazada desde la T2. Mutaciones.
  - Revisar: la forma del JSON, la ruta y la tabla de permisos.
  - Commits, en este orden: `feat(api): add cookieless response middleware` (middleware.py, test_middleware.py y base.py) y `feat(api): add public assets list endpoint` (el resto).
  - Hecho cuando: pytest y ruff en verde y mutaciones registradas.

- [x] **T6. Comando de demostración.** RF-6, RF-7
  - PARAR: OK previo (crea una cuenta con contraseña; comprobación de entorno).
  - Qué: settings/{development,test,production}.py (`ENVIRONMENT`), apps/assets/demo.py, apps/assets/management/commands/create_demo_assets.py, tests/test_demo_command.py y casos en config/tests/test_settings.py.
  - Por qué: `ENVIRONMENT` falla cerrado y sobrevive a `override_settings`. Se descarta `SETTINGS_MODULE`, que vale None bajo `override_settings`.
  - Pruebas: casos de RF-6 y RF-7 y Logs de la Estrategia. Mutaciones.
  - Revisar: los datos de demostración (menos de 4 km, categorías, radios y el par repetido).
  - Commit: `feat(assets): add demo assets command`
  - Hecho cuando: pytest en verde y mutaciones registradas.

- [x] **T7. Esqueleto de frontend/ y contrato del cliente.** RNF Contrato, Desconfianza, Dependencias
  - Dependencias de npm aprobadas (tabla del plan, con versiones exactas).
  - Qué: frontend/{package.json, package-lock.json, .npmrc, .nvmrc, index.html, vite.config.ts, tsconfig*.json, eslint.config.js, .env.example}, src/main.tsx (monta la app), src/styles/index.css, src/i18n/es.ts, src/api/{schema.gen.ts, validate.ts}, backend/openapi.json, .github/workflows/ci.yml (paso de desfase en backend y job `frontend-quality`), docs/architecture.md (frontend).
  - Por qué: el contrato antes que la pantalla. Se descartan guardas escritas a mano en lugar de Zod.
  - Pruebas: vitest de `validateResponse`; `openapi-typescript --check` y `diff` de la descripción en CI. Mutaciones de Zod.
  - Revisar: package.json (19 dependencias exactas) y el esquema Zod frente a openapi.json.
  - Commit: `build(frontend): scaffold app with api contract`
  - Hecho cuando: `npm ci --ignore-scripts`, vitest, build y eslint en verde; CI en verde con los dos controles de desfase.

- [x] **T8. Cuadro pedido, planificador y petición a la API.** RF-9, RF-12 (decisión de no pedir), RF-13 (contrato)
  - Depende de T7.
  - Qué: src/map/{requestBox.ts, scheduler.ts}, src/api/publicAssets.ts y sus tests.
  - Por qué: funciones puras con reloj y temporizador inyectados. Se descarta `toFixed`: daría claves distintas para el mismo cuadro.
  - Pruebas: casos de RF-9 de la Estrategia; `classifyFailure`; fetch simulado que respeta AbortSignal (timeout, `Content-Type`, JSON roto).
  - Revisar: el paso de 0,05°, el margen de 0,5 y los 300 ms.
  - Commit: `feat(map): compute requested box and fetch assets`
  - Hecho cuando: vitest, build y eslint en verde.

- [x] **T9. Rutas, mapa base, círculos y fallo del estilo.** RF-8, RF-10, RF-13 (estilo), RF-14
  - PARAR: OK previo (terceros y URLs del estilo). Depende de T8.
  - Qué: src/app/{route.ts, NotFoundPage.tsx}, src/main.tsx (rutas: `/` y `/map/` normalizan a `/map`), src/map/{style.ts, geodesy.ts, circles.ts, MapView.tsx}, src/pages/MapPage.tsx (aviso y petición de bienes) y sus tests.
  - Por qué: polígono geodésico y estilo descargado y validado. Se descartan la capa `circle` y el evento `error` como detector del fallo del estilo.
  - Petición de bienes (RF-9, RF-10): la T9 cablea `moveend`, `requestBox`, el planificador, `fetchPublicAssets` y `setData` de los círculos. `MapPage` guarda solo los bienes:
    - comprueba `isCurrent()` antes de pintar;
    - si el cuadro no se pide (`tooLarge`, `outOfRange`) o la petición falla, vacía los círculos;
    - los errores que `classifyFailure` no clasifica también vacían los círculos y van a `console.error`;
    - no muestra nada más: `viewState`, el panel y los errores visibles son de la T10.
  - Estilo (RF-13): se descarga con timeout de 10 s, `credentials: "omit"` y `Content-Type` JSON, con tope de 1 MiB sobre el texto leído. Un fallo de red, el tope, un JSON roto o un estilo no válido dan el estado de fallo del estilo.
  - Atribución: al validar el estilo, el campo `attribution` de cada fuente se sustituye por un texto fijo del código, con los enlaces escritos aquí (`rel="noopener noreferrer"`). Las opciones de la fuente pisan al TileJSON, y la atribución del tercero no se pinta.
  - Errores de MapLibre: `transformRequest` lanza `BlockedUrlError` (mensaje fijo, sin la URL) para toda URL que no pase `isAllowedMapUrl`. El listener del evento `error` solo silencia esa clase; el resto va a `console.error`.
  - Pruebas: vitest de `resolveRoute`, haversine 99–101 %, círculos únicos, `validateStyleUrl`, `validateStyleJson`, `isAllowedMapUrl`, la sustitución de la atribución (con una atribución hostil en la entrada y sin mutar el estilo original), el listener (un error que no sea `BlockedUrlError` no se silencia) y la decisión de pintar con `isCurrent()`. Mutaciones. DevTools a 375 y 1280 px: la atribución visible lleva los enlaces propios (`rel="noopener noreferrer"`, que el TileJSON no trae), el worker carga en dev y en `vite preview`, una sola petición tras parar el mapa y consola limpia.
  - Revisar: atribución y aviso visibles; red solo al propio origen y a OpenFreeMap.
  - Commit: `feat(map): render base map and asset circles`
  - Hecho cuando: vitest, build y eslint en verde; DevTools sin errores en consola.

- [ ] **T10. Lista del panel, vacío y errores de la API.** RF-11, RF-12, RF-13 (petición)
  - PARAR: OK previo (texto público como salida: XSS). Depende de T9.
  - Qué: src/panel/{ResultsPanel.tsx, AssetCard.tsx, header.ts}, src/state/viewState.ts, src/i18n/format.ts, src/assets/categories/*.svg y sus tests. Sobre la petición que cablea la T9, añade `viewState`, el panel y los errores visibles de la petición.
  - Por qué: tarjetas no interactivas y una sola altura, como fija la spec. Se descarta reutilizar el HTML del prototipo (usa `innerHTML`).
  - Pruebas: vitest de `headerText`, `isCircleVisible`, `viewState` y formato del precio; título como texto con `react-dom/server` (mutación). DevTools a 375 y 1280 px.
  - La página decide qué muestra el panel si `classifyFailure` propaga un error inesperado (solo clasifica causas conocidas): nunca se queda en «Buscando bienes…».
  - Movimiento reducido: el movimiento propio de «Volver a la zona inicial» no pasa `essential`, se comprueba en DevTools con la emulación y las transiciones CSS del panel se desactivan con `prefers-reduced-motion`.
  - Revisar: textos del catálogo y medidas del panel.
  - Commit: `feat(panel): list assets with empty and error states`
  - Hecho cuando: vitest, build y eslint en verde. Después, la validación de punta a punta (24 tarjetas en la vista inicial) queda registrada en validation.md.
