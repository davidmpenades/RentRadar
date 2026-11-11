# Tareas 016 — Sistema visual
Spec: specs/016-visual-system/spec.md · Plan: specs/016-visual-system/plan.md
Máximo 10 tareas: hay 8 (la T6 lleva dos commits), en orden lineal de dependencia (T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8). El paso previo y el cierre no son tareas: no producen código de la aplicación.

Cada tarea deja en verde `npx vitest run`, `npm run build` y `npx eslint <ficheros tocados>`, y cambia solo el frontend: no hay API, migraciones ni dependencias nuevas. Los tests de vitest se escriben primero y fallan por la razón esperada; vitest corre sin entorno de navegador, así que la parte visual y la interacción se comprueban en el navegador a 1280 y 375 px con la consola sin errores. Cuenta de pruebas: la T1 ya necesita sesión para comprobar «Salir» y su estado deshabilitado. Se registra una sola cuenta, `t16-a@example.com`, en la primera tarea que la necesite, con la autorización expresa del desarrollador en ese momento, y su sesión se reutiliza en el resto de tareas. Solo se crea otra si la sesión se pierde, otra vez con su OK. Levantar el stack se pregunta antes. Sin pruebas de mecanismo: la spec no toca privacidad ni seguridad.

## Paso previo a la T1 (sin commit)
Línea base A del rendimiento, con la rama tal como está antes de cualquier tarea:
- `cd frontend && npm run build` y copia de `dist/` a `~/rentradar-perf/a`, fuera del repositorio.
- Comprobar que `~/rentradar-perf/a/index.html` y su carpeta `assets/` existen.
- Anotar el commit del que sale (`git log --oneline -1`) para `validation.md`.

## Tareas

- [x] **T1. Botones y anillo de foco.** RF-1, RF-10, RF-15
  - Ficheros:
    - Crea `frontend/src/styles/buttons.css`: `btn`, `btn-primary`, `btn-secondary`, `btn-form`, con relieve, pulsado, deshabilitado, transiciones solo con movimiento normal, colores forzados y `touch-action: manipulation`. El secundario lee `--btn-secondary-bg` con el cielo `#DFE8FF` por defecto.
    - Modifica `frontend/src/styles/index.css`: tokens nuevos en `@theme`, anillo global azul de 2 px a 2 px, anillo de tinta de 3 px ampliado a `.maplibregl-map :focus-visible`, importa `buttons.css`.
    - Modifica `TopBar.tsx` («Registrarse», «Salir»), `NotFoundPage.tsx` («Ir al mapa»), `MapView.tsx` («Reintentar» del mapa base), `ResultsPanel.tsx` («Reintentar», «Volver a la zona inicial»), `LogoutNotice.tsx` («Reintentar») y `RegistrationForm.tsx` («Crear cuenta» como `btn-form`; el botón «Mostrar contraseña» actual no se toca hasta la T2).
  - Antes de empezar: consultar con Context7 que Tailwind 4.3.3 aplica `@layer components` en ficheros importados y que `:has()` va bien en sus selectores; y comprobar con un `npm run build` si la ruta del fichero de la fuente en `dist` es estable (decide la precarga opcional de la T8; el resultado se anota en el informe de la tarea).
  - Tests:
    - vitest (se adaptan primero): `TopBar.test.ts`, `ResultsPanel.test.ts` y `RegistrationForm.test.ts` pasan de afirmar `min-h-11 min-w-11` a afirmar `btn` más la clase de tipo en cada botón; el aviso de salida, en los tests de `LogoutNotice` que aún viven en `TopBar.test.ts`.
    - Navegador: estilo calculado de `box-shadow` en reposo, pulsado y deshabilitado («Crear cuenta» enviando, «Salir» saliendo); `transition-duration` mayor que 0 y, con `prefersReducedMotion: "reduce"`, igual a 0; `outline` de 2 px `#1647B8` con separación de 2 px en el principal, el secundario («Salir») y el enlace de la marca; tabulando hasta un enlace de la atribución, el `outline` sigue siendo el de tinta de 3 px; 44 × 44 px; colores forzados (contorno de 2 px en los botones, también el secundario). «Salir» y su estado deshabilitado se comprueban con la sesión de `t16-a@example.com`, que se registra aquí con la autorización expresa del desarrollador.
  - Commit: `feat(frontend): add button styles and blue focus ring`
  - Hecho cuando: los tests adaptados fallan primero y luego pasan; vitest, build y eslint en verde; la comprobación en el navegador a 1280 y 375 px sin errores de consola.

- [x] **T2. Campos, ojo e indicador.** RF-2, RF-3, RF-4, RF-5, RF-10, RF-15
  - Ficheros:
    - Crea `frontend/src/styles/fields.css`: `field`, `field-box`, `eye`, con borde, error, sombra interior, transición de estado, solo lectura, hover del ojo, `touch-action: manipulation` y la regla `::-ms-reveal` / `::-ms-clear`.
    - Crea `frontend/src/ui/Indicator.tsx` y `frontend/src/register/EyeIcons.tsx` (`EyeIcon` y `EyeOffIcon`).
    - Modifica `RegistrationForm.tsx`: campos con `field`; el ojo va dentro de la caja del campo, tras la entrada y antes de la ayuda, con `aria-label` fijo «Mostrar contraseña», `aria-pressed` y `aria-controls`; error general con indicador y texto en tinta, sin limón; envío en curso sin indicador y en gris; los mensajes de campo con su indicador.
    - Modifica `index.css` para importar `fields.css`.
  - Tests:
    - vitest (`RegistrationForm.test.ts`, el ojo se localiza por su `aria-label`): nombre fijo y `aria-pressed` en los dos estados; icono abierto o tachado (el trazo `M3 3l18 18` solo con la contraseña visible); orden entrada, ojo, ayuda con `indexOf`; el error general lleva el indicador y ninguna clase de fondo ni `lemon`; el envío no lleva indicador; `aria-invalid` y `aria-describedby` siguen asociados.
    - Navegador: la etiqueta no se mueve al enfocar y escribir; borde `#B3261E` con error; el ojo alterna ver y ocultar, conserva el valor, no mueve el foco y funciona con el campo en solo lectura durante el envío; el ojo es el siguiente en el orden de tabulación tras el campo; 44 × 44 px del ojo y de los campos; anillo del campo y del ojo; la regla `::-ms-reveal` existe en la hoja; transición del campo mayor que 0 con movimiento normal y 0 con reducido.
  - Commit: `feat(frontend): add field styles and password eye toggle`
  - Hecho cuando: los tests fallan primero y luego pasan; vitest, build y eslint en verde; recorrido del formulario de registro solo con teclado a 1280 y 375 px.

- [x] **T3. Superficies de cristal y panel.** RF-8, RF-9, RF-10
  - Ficheros:
    - Crea `frontend/src/styles/surfaces.css`: `glass` con sus variables (`--glass-bg`, `--glass-blur`, `--glass-btn-bg`, `--glass-btn-bg-hover`), borde, sombra y radio; respaldos sólidos bajo `@supports not`, transparencia reducida y contraste alto; colores forzados aparte. `.glass` redefine `--btn-secondary-bg` para el secundario translúcido.
    - Modifica `index.css`: `--panel-height: max(40dvh, 15rem)` en `:root` y la importación.
    - Modifica `ResultsPanel.tsx`: el panel es una sola superficie `glass`, con `height: var(--panel-height)` en lugar de `h-[40dvh] min-h-60` y con `data-results-panel`; las tarjetas no llevan fondo propio.
  - Tests:
    - vitest (`ResultsPanel.test.ts`): el panel lleva `glass` y `data-results-panel`; las tarjetas no llevan clase de superficie; la altura sale de la variable.
    - Navegador: `backdrop-filter` de 22 px y fondo `rgb(236 243 255 / 0.88)` en el panel; la barra y la tarjeta del registro opacas; contraste alto emulado → sólido; colores forzados → contorno visible y sin sombra; transparencia reducida y falta de desenfoque por el procedimiento de variables del plan (se anota el límite); panel sobre la línea de un círculo y sobre una etiqueta oscura; el panel a 375 px conserva su altura de antes; cuentas de contraste de la tabla del plan recalculadas con los colores finales.
  - Commit: `feat(frontend): add glass surfaces and restyle the results panel`
  - Hecho cuando: los tests fallan primero y luego pasan; vitest, build y eslint en verde; el panel idéntico en altura y comportamiento a 1280 y 375 px, y legible sobre el peor fondo.

- [x] **T4. «Cerrar aviso».** RF-6, RF-7
  - Ficheros:
    - Modifica `frontend/src/session/sessionState.ts`: `dismissResult()` devuelve el aviso a ninguno y el foco a «Salir», sin anuncio.
    - Modifica `SessionProvider.tsx`: `dismissNotice` en el contexto; no toca el estado de sesión ni el anuncio.
    - Modifica `frontend/src/i18n/es.ts`: «Cerrar aviso».
    - Modifica `LogoutNotice.tsx` y `AppShell.tsx`: botón secundario «Cerrar aviso» de 44 px fuera de la región de estado, sobre la posición actual del aviso.
  - Tests:
    - vitest (`sessionState.test.ts`): `dismissResult` da `notice` nula y foco `logout`, y no devuelve anuncio; el texto «Cerrar aviso» sale del catálogo; el aviso renderizado lleva dos botones.
    - Navegador, con la sesión de `t16-a@example.com` de la T1 (solo se crea otra cuenta si esa sesión se pierde, con el OK del desarrollador), y la salida fallida simulada cortando la petición desde las herramientas del navegador: «Cerrar aviso» retira el aviso y el foco pasa a «Salir»; un nuevo fallo lo vuelve a mostrar; la sesión, la barra y lo que se anuncia no cambian; «Reintentar» sigue retirando el aviso al empezar y el reintento ante `csrf_failed` funciona.
  - Commit: `feat(frontend): let users dismiss the logout notice`
  - Hecho cuando: los tests fallan primero y luego pasan; vitest, build y eslint en verde; el recorrido «fallo, cerrar, nuevo fallo, reintentar» comprobado a 1280 y 375 px.

- [x] **T5. Anclaje y región de estado del aviso.** RF-6, RF-7, RF-8, RF-10, RF-15
  - Ficheros:
    - Crea `frontend/src/styles/notice.css`: zona del aviso (`absolute`, `z-20`, sin eventos de puntero) con los cuatro casos de `bottom` y `left`, `--free-top`, tarjeta de cristal de 22 px de radio y 560 px como máximo, en dos filas por debajo de 560 px; entrada y salida con `data-open`, solo con movimiento normal.
    - Crea `frontend/src/map/useFreeZoneTop.ts`: `ResizeObserver` y `MutationObserver`, escribe `--free-top` con `style.setProperty` desde una ref.
    - Modifica `LogoutNotice.tsx`: región `role="status"` oculta a la vista, siempre montada y con solo el mensaje; tarjeta siempre montada con `data-open`; párrafo en `aria-hidden`; indicador de 24 px; botones fuera de la región.
    - Modifica `AppShell.tsx`: la zona usa el hook y monta el aviso.
    - Crea `frontend/src/app/LogoutNotice.test.ts` y mueve a él los seis tests del aviso que hay en `TopBar.test.ts` (los quita de allí), adaptados al marcado nuevo; el de cableado, que comprueba que cada botón llama solo a su función, se conserva.
  - Tests:
    - vitest (`LogoutNotice.test.ts`): la región solo contiene el mensaje y está vacía sin aviso; ningún botón dentro de la región; la tarjeta está siempre montada y `data-open` solo aparece con aviso; el párrafo lleva `aria-hidden`; el mensaje es el de la 009. Los dos de la región (solo con el mensaje y ningún botón dentro) ya pasan desde la T4: aquí son guardas, no tests que fallen primero.
    - Navegador, con la sesión de `t16-b@example.com` creada en la T4 (solo se crea otra cuenta si esa sesión se pierde, con el OK del desarrollador en ese momento): límites de la tarjeta, del zoom, de la atribución, de la barra y del panel a 375 y 1280 px (sin cruzarse), y a 667 × 375 y con el texto al 200 % (puede tapar parte del panel, nunca el zoom, la atribución ni la barra); cruzar 900 px con el aviso visible; página sin mapa («Página no encontrada», registro) y error del mapa base; `pointer-events` calculado de la zona (`none`) y de la tarjeta (`auto`) y arrastre del mapa fuera de la tarjeta; el aviso sigue visible a los 60 s y tras navegar; el árbol de accesibilidad expone el mensaje una sola vez y el anuncio es solo el mensaje; aparición y salida mayores que 0 con movimiento normal y 0 con reducido; anillo del aviso. Al final: con la red cortada, «Salir» muestra el aviso; al volver la red, «Reintentar» sale bien (el aviso desaparece, se anuncia «Has salido», la barra pasa a «Registrarse» y el foco va a «Registrarse»). Esa salida cierra la sesión, por eso va la última. Si «Reintentar» no sale bien, es un fallo de la 009: se para ahí.
  - Commit: `feat(frontend): anchor the logout notice to the free map zone`
  - Hecho cuando: los tests fallan primero y luego pasan; vitest, build y eslint en verde; los límites en pantalla registrados para `validation.md`.

- [x] **T6. Lista blanca compartida e icono.** RF-13, RF-14 (una tarea, dos commits)
  - Ficheros:
    - Crea `frontend/src/testing/svgWhitelist.ts`: las reglas de la 006 movidas sin cambios (`TAG`, `ATTRIBUTE` y las cuatro comprobaciones).
    - Modifica `frontend/src/panel/categorySvg.test.ts`: usa el módulo; sus cuatro `it` conservan nombre y lo que comprueban.
    - Crea `frontend/public/icon.svg` (el del plan) y `frontend/src/brand/icon.test.ts`.
  - Tests:
    - vitest: `categorySvg.test.ts` sigue dando los mismos resultados con las 11 imágenes; `icon.test.ts` aplica la lista blanca al icono, comprueba al menos tres rellenos distintos, sombra más oscura y brillo más claro que la base (por orden de dibujo), ninguno es `#F5D547`, 1,5:1 entre base y sombra y entre base y brillo, y 3:1 de la silueta contra blanco; un SVG de prueba con degradado, escala, color de tres cifras y `<g>` debe fallar. Se confirma que `?raw` lee un fichero de `public/`.
  - Commits, en este orden:
    1. `refactor(frontend): share svg whitelist rules`, solo con `svgWhitelist.ts` y `categorySvg.test.ts`, sin cambiar lo que comprueba.
    2. `feat(frontend): add RentRadar icon`, con `icon.svg` e `icon.test.ts`.
  - Hecho cuando: tras el primer commit, `categorySvg.test.ts` da los mismos resultados con las 11 imágenes y su diff solo mueve reglas; tras el segundo, los tests de `icon.test.ts` fallan primero y luego pasan; en los dos, vitest, build y eslint en verde.

- [x] **T7. Marca en la barra e icono de la pestaña.** RF-11, RF-12, RF-15
  - Ficheros:
    - Modifica `TopBar.tsx`: dentro del enlace de la marca, `<img src="/icon.svg" alt="" width="36" height="36">` y el nombre en un `<span translate="no">` que se oculta a la vista por debajo de 900 px y se muestra desde 900 px; hover del enlace; el enlace mide al menos 44 × 44 px.
    - Modifica `frontend/index.html`: `<link rel="icon" href="/icon.svg" type="image/svg+xml">` en lugar del icono vacío.
    - Crea `frontend/src/app/indexHtml.test.ts` y modifica `TopBar.test.ts`.
  - Tests:
    - vitest: la marca contiene la imagen con `alt=""` y el nombre «RentRadar» dentro del enlace aunque se oculte a la vista, con `translate="no"` y la clase de 44 px; `index.html` declara el icono del sitio y ya no `data:,`.
    - Navegador: a 375 px el nombre no se ve, el nombre accesible del enlace sigue siendo «RentRadar», el enlace mide al menos 44 × 44 px y la barra con la marca y «Registrarse» o «Salir» no desborda; al cruzar 900 px el nombre aparece o se oculta sin cambiar el nombre accesible; capturas del icono a 16 px sobre blanco y sobre el gris oscuro con `emulate colorScheme` claro y oscuro (lienzo de 16 × 16 con el icono real), con 1,5:1 entre capas, 3:1 de silueta contra cada fondo (`#202124` y `#35363A`) y la sombra desplazada respecto a la base; anillo del enlace de la marca.
  - Commit: `feat(frontend): show the RentRadar icon in the top bar and tab`
  - Hecho cuando: los tests fallan primero y luego pasan; vitest, build y eslint en verde; la consola sin errores y el icono cargado desde `/icon.svg`.

- [ ] **T8. Pulido de la página.** Presentación (sin RF)
  - Ficheros:
    - Modifica `frontend/index.html`: `theme-color`, `color-scheme` y preconexión a `tiles.openfreemap.org`; la precarga de la fuente solo si la T1 comprobó una ruta estable (si no, se anota en `validation.md`).
    - Modifica `index.css`: `color-scheme: light`.
    - Modifica `frontend/src/i18n/format.ts` (`formatRadius` con U+00A0) y `AssetCard.tsx` (U+00A0 entre «/» y la unidad).
    - Modifica `RegistrationForm.tsx` y `NotFoundPage.tsx`: `text-wrap: balance` en el `h1`.
    - Modifica `format.test.ts`, `ResultsPanel.test.ts` e `indexHtml.test.ts`.
  - Tests:
    - vitest: `format.test.ts` espera `500 m` y `1 km` con U+00A0 (construido con `String.fromCharCode(160)`) y un caso fija el U+00A0 de `formatPrice` antes de «€»; `ResultsPanel.test.ts` espera U+00A0 también tras «/»; `indexHtml.test.ts` comprueba las etiquetas de la cabecera. Estos son los dos tests de la 006 que cambian de cadena esperada, sin cambiar lo que comprueban.
    - Navegador: etiquetas de la cabecera presentes; `text-wrap: balance` y `touch-action: manipulation` por estilo calculado; ninguna distancia ni precio se parte entre la cifra y su unidad a 375 px.
  - Commit: `feat(frontend): polish page head, number units and titles`
  - Hecho cuando: los tests fallan primero y luego pasan; vitest, build y eslint en verde; el panel a 375 px sin cortes entre cifra y unidad.

## Cierre (sin tarea de código)
Tras la T8, con `/sdd-validate` y la aprobación del usuario:
- **Medición de rendimiento:** compilar la versión B a `~/rentradar-perf/b`, servir A y B con `vite preview` en los puertos 4173 y 4174 (con el stack levantado y la autorización del desarrollador), calentamiento de cada versión descartado y seis pasadas A, B, A, B, A, B a 375 px con la CPU 4×, con su tráfico de red, sus medianas y el veredicto del umbral de la spec. Si no aprueba, se ajusta la superficie con el usuario sin bajar del 80 % de opacidad y se repite.
- **`validation.md`:** cada RF con su verificación; la tabla de contraste recalculada (cristal y sólida, también con el negro puro, y el panel sobre la zona más oscura del mapa); la comparación de los colores de «positron» con una descarga nueva del estilo; los límites en pantalla del aviso; las comprobaciones de respaldo y preferencias (con el límite de las dos que se hacen por variables); la accesibilidad; las capturas de la pestaña en los dos temas con los grises medidos; el resultado de la precarga opcional; `git diff` de `package.json` y `package-lock.json` vacío y ningún uso del limón; recorrido solo con teclado a 1280 y 375 px y la consola sin errores.
- **Commits de cierre:** `docs(spec-016): validation` y, con la spec en «implementada», `docs(memory): close spec 016`.
- **Ajustes de texto de la spec:** MEMORY.md (spec activa pasa a la 007) y el punto 8 de `specs/015-login/notes.md` («el formulario de entrada usa los campos, el ojo y los botones de la 016»).
