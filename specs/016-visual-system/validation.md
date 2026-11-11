# Validación — 016-visual-system
Rama: `feature/016-visual-system` · Entorno: frontend en el host (Vite 8.3.5, Vitest 5.0.5, Tailwind 4.3.3, maplibre-gl 6.14.0), Chrome DevTools MCP y stack de Docker Compose para la API pública

Validación en curso: T1 a T8 hechas. La validación completa (cada RF, contraste, rendimiento, accesibilidad, recorrido con teclado) se escribe al cierre con `/sdd-validate`. Hasta entonces este fichero recoge las notas de implementación, para que no se pierdan.

## Notas de implementación (T1–T8)
Fecha: 2026-11-10 (T1–T3) y 2026-11-11 (T4 a T8) · Commits: T1 `e252367`, T2 `9355bdb`, T3 `4ea4c34`, T4 `6453e26`, T5 `7692688` (hook) y `1493758` (aviso), más `d6912d1` (movimiento de los tests), T6 `f8cc84c` (refactor) y `322318c` (icono), T7 `e2dc7e7`, T8 `b2de3b0`. Cada tarea cierra con vitest, eslint de los ficheros tocados y `npm run build` en verde: tras la T3, 27 ficheros y 1038 tests; tras la T4, 27 ficheros y 1043 tests; tras la T5, 29 ficheros y 1056 tests; tras la T6, 30 ficheros y 1082 tests; tras la T7, 31 ficheros y 1088 tests; tras la T8, 31 ficheros y 1092 tests. `package.json` y `package-lock.json` no cambian.

### Estado del entorno
| Elemento | Estado |
|---|---|
| Línea base A del rendimiento | `~/rentradar-perf/a`, compilada del commit `d458e30` (`docs(spec-016): tasks`), antes de la T1. `index.html` y `assets/` comprobados; idéntica a `frontend/dist` en el momento de la copia. |
| Vite de desarrollo | Puerto 5173, en la terminal del desarrollador. No se lanza, para ni relanza desde la sesión. |
| Stack de Docker Compose | `backend` y `db` arriba y sanos. La T3 solo lee la API pública. Al empezar la T4 estaba parado (el proxy de Vite devolvía 502) y se levantó antes de repetir el registro. |
| Cuentas de prueba | `t16-a@example.com`, creada en la T1 en la BD de desarrollo desde el formulario de registro: su sesión se cerró por un clic accidental (`POST /api/v1/auth/logout/` 204 a las 08:11:37 UTC). `t16-b@example.com`, creada en la T4 con autorización expresa, también desde el formulario: su sesión se cerró en la T5 (ver el recorrido final). `t16-c@example.com`, creada en la T5 con autorización expresa, desde el formulario: su sesión se cerró con el reintento de la salida. Las contraseñas se generaron en la página y no se guardaron. Ninguna sesión queda abierta. |
| Navegador | Una pestaña abierta, sin sesión. Las pestañas de prueba aisladas se cierran al terminar. El perfil de Chrome DevTools MCP solo admite un navegador: con otro servidor `chrome-devtools-mcp` activo, `new_page` falla con «already running». |

### T1. Botones y anillo de foco
- **Estado pulsado de RF-1:** leído de la hoja de estilos (la herramienta no mantiene `:active`), no medido. Las reglas `.btn-primary:active` y `.btn-secondary:active` y los valores resueltos de `--shadow-btn-primary-pressed` y `--shadow-btn-secondary-pressed` constan en esta nota: 12/24 px pasa a 3/8 px en el principal y 6/16 px a 2/6 px en el secundario, con `scale(.97)`.
- **«Salir» y el estado deshabilitado:** medidos primero con sondas (botones temporales con las mismas clases) y después con el elemento real durante una salida en vuelo: `box-shadow: none`, `opacity 0.6`, `cursor: not-allowed`, `aria-disabled="true"` sin `disabled`, `tabIndex 0`, sin respuesta al puntero y un segundo clic sin segunda petición (POST 1 a 1).
- **«Crear cuenta» enviando:** la primera lectura quedó invalidada porque se tomó con la transición de 0,14 s en curso (`box-shadow` aún con el valor de reposo). Se repitió 450 ms después, en una pestaña aislada sin sesión y con `fetch` sustituido: el POST no salió del navegador, sin escrituras en la BD.
- **Salida fallida:** simulada con la red en `Offline` desde las herramientas del navegador y un retraso de 5 s del POST para tener una ventana «en vuelo»; la petición no llegó al servidor. Aviso y «Reintentar» medidos con el aviso actual, que sigue arriba y en limón hasta la T4 y la T5.
- **Colores forzados:** medidos los botones reales y sondas del secundario, del botón de formulario y del deshabilitado: contorno de 2 px, sin sombra ni degradado, deshabilitado en `GrayText`.
- **Incidencia de entorno:** un cambio de viewport con la red cortada recargó la página y Chrome mostró su página de «sin conexión». Sin efecto en los resultados.

### T2. Campos, ojo e indicador
- **Campos de 48 px** (`min-height: 3rem`): con el borde de 2 px el interior mide 44 px y el ojo de 44 × 44 cabe dentro del borde, a 2 px de arriba y de la derecha, sin taparlo. Cumple el mínimo de 44 px del plan y alinea los campos con «Crear cuenta», que también mide 48.
- **Regla de Edge** (`::-ms-reveal` y `::-ms-clear { display: none }`): se comprueba por el texto de la hoja y por el CSS emitido por el build. Chrome descarta los pseudo-elementos que no conoce y no los guarda en su CSSOM, así que no se ve ahí. Sin prueba en Edge real.
- **Estados con el POST sustituido** («Creando la cuenta…» y «No hay conexión»): medidos con `fetch` sustituido en una pestaña aislada, sin tocar el servidor.
- **Etiqueta fija:** se mantiene al enfocar y escribir. Un único caso de posición distinta, al enviar, es la desaparición de los mensajes de error previos, no un movimiento de la etiqueta.
- **Aceptado:** el anillo de foco del ojo cruza el borde del campo, porque el ojo está dentro del borde y su anillo se dibuja a 2 px de él.
- **Aceptado:** el indicador de error conserva su rojo `#B3261E` en colores forzados en lugar de tomar el color del sistema; contra el negro da unos 3,4:1.
- **Teclado:** orden email, contraseña, ojo, «Crear cuenta»; Espacio alterna el ojo y Enter envía el formulario. En todas las paradas, anillo azul de 2 px a 2 px.

### T3. Superficies de cristal y panel
- **Procedimiento de respaldo, transparencia reducida y falta de desenfoque** (`emulate` no admite ninguna de las dos): el cuerpo real de cada regla se ejercita copiándola del CSSOM y sustituyendo solo su condición por una que se cumpla (`@media all`, `@supports not (x-sin-soporte: 1)`); en ambos casos el panel queda en `rgb(237 243 255)` con `backdrop-filter: none` y el secundario en `rgb(223 232 255)`. Las condiciones originales se validan aparte: `CSS.supports` da falso para `not (...)` y verdadero para su interior, y `matchMedia('(prefers-reduced-transparency: reduce)')` es reconocida (`media` distinto de `not all`).
- **Límite:** el cuerpo de las reglas se ejercita de verdad y las condiciones se validan por separado, pero no se ha visto en un navegador realmente sin soporte ni con el ajuste del sistema operativo activo.
- **Contraste alto y colores forzados:** emulación real de la herramienta. Contraste alto: fondo `rgb(237 243 255)` y filtro `none`. Colores forzados: fondo `Canvas`, borde de 2 px `CanvasText`, sin sombra ni filtro. En contraste alto el borde sigue siendo el blanco al 95 %: la spec pide el mismo borde en la superficie sólida.
- **Alfa emitida por el build:** el minificador emite `#ecf3ffe0`, es decir 0,8784 (cuantización de 8 bits), por encima del 0,8. Con ese alfa, texto principal 12,12:1 y precio 5,44:1.
- **Contraste recalculado** con los colores finales, tinte al 88 % sobre el negro puro, que sigue siendo el peor fondo: texto principal 12,16, secundario 6,02, precio 5,46, icono de radio 6,02, anillo 5,46, indicador de error 4,47 (sólida 5,87); texto en error 4,47, que no llega a 4,5 y no se usa sobre cristal; texto del secundario 15,96 (blanco al 70 %) y 14,51 (cielo, hover 13,45); texto blanco del principal 5,06 / 5,71 / 7,99. Coincide con la tabla del plan.
- **Medidas del panel:** altura de 324,797 px a 375 × 812 (el valor esperado, `max(0,4 × 812, 240)`), 240 px a 667 × 375, panel inferior de 280 px a 899 px y columna de 400 px a 900 px, con las esquinas superiores o las derechas de 24 px según el caso. La barra superior y la tarjeta del registro son opacas.
- **Arrastre sintético del mapa:** el desplazamiento con eventos de ratón sintéticos funciona a 1280 px sin táctil. Con la emulación táctil a 375 px funciona si los eventos llevan `buttons: 1` y `bubbles: true` (ver la medición de prueba).
- **Test vigilado con mutación:** `surfaces.test.ts` se probó con el alfa de `--glass-bg` a 0,79, sobre el propio fichero de la tarea (aún sin commitear) con copia de seguridad fuera del repositorio. Falla un solo test, `el tinte del cristal tiene al menos el 80 % de opacidad`, con `expected 0.79 to be greater than or equal to 0.8`; los otros 5 pasan. Restaurado a 0,88: 6 de 6 y sha256 idéntico antes y después (`adf89ed0889309ff524ccfd595a3a8ba7d4632f7029524e13b5dece1bf0d0fb9`, también con `cmp` contra la copia). Antes de eso el test falló primero por `ENOENT` (el fichero no existía) y después por la cadena vacía de Vitest, no por la razón de fondo.
- **`vite.config.ts`:** una línea, `test.css: { include: [/\.css\?raw$/] }`, porque Vitest sustituye por vacío los CSS importados, incluso con `?raw`. Leer el fichero con `node:fs` habría exigido `@types/node`, que no está instalado. No cambia el build ni las dependencias.
- **Decisiones respecto al plan:**
  - El radio queda fuera de `.glass` y lo aplica cada superficie con `--radius-surface`.
  - La variable `--glass-filter` sustituye a `--glass-blur`, para que el respaldo deje `backdrop-filter: none` y no `blur(0)`.
  - El secundario sobre cristal redefine `--btn-secondary-bg` y su hover directamente, sin `--glass-btn-bg`.
  - La miniatura de la tarjeta pasa de 12 a 16 px, como en la variante aprobada.
  - `surfaces.test.ts` se añade a los tests previstos.
- **Capturas** del panel (1280 y 375 px, sobre el peor fondo y en colores forzados) en `prototypes/016-visual-system/capturas/`, que no se versiona.

### T4. Cerrar aviso
- **Marcado A (provisional):** el contenedor sigue superpuesto (`absolute inset-x-0 top-0 z-20`, sin eventos de puntero), en el mismo sitio y con el mismo limón. Dentro hay una tarjeta siempre montada, con fondo, margen y relleno solo cuando hay aviso: sin aviso mide 0 px de alto y no tapa el mapa. La región `role="status"` va dentro de la tarjeta y contiene solo el mensaje; «Reintentar» (`btn-primary`) y «Cerrar aviso» (`btn-secondary`) van fuera de la región, para que el anuncio no incluya el nombre de los botones. La T5 sustituye este marcado por la zona anclada y la tarjeta de cristal.
- **Estado:** `dismissResult()` devuelve el aviso a ninguno y el foco a «Salir», sin anuncio. `dismissNotice` solo toca el aviso y la petición de foco: ni el estado de sesión ni el anuncio.
- **Tests adelantados de la T5:** «la región solo contiene el mensaje de la 009» y «ningún botón queda dentro de la región». Viven por ahora en `TopBar.test.ts`, con los demás del aviso, y la T5 los mueve a `LogoutNotice.test.ts`.
- **Test de cableado:** comprueba que «Reintentar» llama solo a `onRetry` y «Cerrar aviso» solo a `onDismiss`. `renderToStaticMarkup` no muestra a qué función va cada `onClick`, así que el test llama al componente y recorre su árbol de elementos. Se comprobó con mutación: se intercambiaron los dos `onClick` de `LogoutNotice.tsx` y falló solo ese test, con `expected "vi.fn()" to be called 1 times, but got 0 times` en `onRetry`; los otros 18 de `TopBar.test.ts` pasaron. sha256 antes y después `f05500868897c1eb49b74195b109ffe9a890c80191b15510065ab4393689822d`, y `cmp` idéntico a la copia.
- **Tests escritos primero:** cinco fallaron antes de implementar, cada uno por su razón: `dismissResult is not a function`; `es.session.dismiss` sin definir en lugar de «Cerrar aviso»; el segundo botón ausente (`expected undefined to be defined`); la región con «Reintentar» dentro (recibido `No se ha podido salir. Inténtalo de nuevo.Reintentar`); y un `<button` dentro de la región.
- **Desviación:** el reintento con éxito y el reintento ante `csrf_failed` pasan al final de la T5. Una salida con éxito cierra la sesión de `t16-b@example.com`, que la T5 necesita, y no hay pantalla de entrada hasta la 015, así que perderla obligaría a registrar otra cuenta.
- **Cuenta:** `t16-b@example.com` registrada desde `/register`, con la contraseña generada en la página y asignada al campo no controlado (24 caracteres alfanuméricos de `crypto.getRandomValues`), sin salir de ahí. La sesión queda abierta para la T5. Un primer intento, con el stack parado, no llegó al backend (502 de Vite); su contraseña se descartó.
- **Recorrido en el navegador**, un ancho cada vez, con el ancho aplicado con `emulate` antes de cortar la red (la página no se recargó) y la red en `Offline` para la salida fallida:

| Paso | 1280 × 800 | 375 × 812 (móvil, táctil) |
|---|---|---|
| Sin aviso | Tarjeta de 0 px de alto; en el borde superior de la zona, bajo la barra, está el `canvas` del mapa | Igual |
| Salida fallida | Mensaje y dos botones; tarjeta de 60 px (y 64 a 124); «Reintentar» 135,5 × 44 y «Cerrar aviso» 147,9 × 44; foco en «Salir» | Tarjeta de 96 px (y 64 a 160), en dos filas; botones iguales; foco en «Salir»; sin scroll horizontal |
| Regiones de estado | Aviso: «No se ha podido salir. Inténtalo de nuevo.»; global: vacía | Igual |
| «Cerrar aviso» con clic | Tarjeta a 0 px, región del aviso vacía, foco en «Salir», barra en «Salir», región global sin cambios (vacía) | Igual |
| «Salir» otra vez | El aviso reaparece con el mensaje | Igual (96 px) |
| «Reintentar» | Se retira al empezar (región vacía, 0 px) y reaparece 45 ms después; foco en «Salir» | Igual, a los 33 ms |
| Teclado | Dos Tab desde «Salir» hasta «Cerrar aviso»; Enter y Espacio lo cierran y el foco acaba en «Salir»; anillo sólido de 2 px `rgb(22, 71, 184)` | Igual con Enter y con Espacio |

- **Consola:** sin errores de la aplicación. Solo `net::ERR_INTERNET_DISCONNECTED` de las peticiones cortadas (5 a 1280 y 4 a 375), un 502 del primer intento con el stack parado y dos avisos de estilo de MapLibre sobre `highway-shield-*`.
- **Red:** quitada una sola vez al final, con el viewport a 1280 × 800 y sin completar la salida; comprobada con `GET /api/v1/auth/session/` (200), la barra en «Salir» y `navigator.onLine`. No se midió por separado a 375. Entre los dos anchos se quitó la limitación para aplicar el ancho antes de volver a cortar.
- **Incidencia de entorno:** el servidor MCP solo lee scripts dentro de su raíz de trabajo, así que los de medida se pasaron en línea.
- **No comprobado en la T4:** el reintento con éxito y el de `csrf_failed` (ver la desviación).

### T5. Anclaje y región de estado del aviso
- **Commits:** `d6912d1` mueve sin cambios los seis tests del aviso de `TopBar.test.ts` a `LogoutNotice.test.ts` (el bloque original y el movido tienen el mismo sha256, `8cb4bc9d5851451c3925741cac5087d3878cf5e008f515392d8f8dc973d4f5d0`; el blob del índice era el de la copia «solo movimiento»). `7692688` añade `freeZoneTop` y `useFreeZoneTop`. `1493758` ancla el aviso: `notice.css`, `LogoutNotice.tsx`, `AppShell.tsx`, `index.css` y los tests.
- **Marcado final:** zona `notice-zone` (`absolute`, `z-index: 20`, sin eventos de puntero, contenedor de consulta), tarjeta `notice-card glass` siempre montada con `data-open` e `inert` mientras no hay aviso, región `role="status"` con `sr-only top-0 left-0`, párrafo visible con `aria-hidden`, indicador `size-6` y botones fuera de la región. La zona de contenido lleva `notice-host`, que `notice.css` usa con `:has([data-results-panel])` para los cuatro casos de `bottom` y `left`.
- **Decisiones respecto al plan:**
  - La tarjeta se localiza por la clase `notice-card`, la misma del selector `.notice-card[data-open]`; un test lo cruza con `notice.css`.
  - El cálculo de `--free-top` vive en `freeZoneTop` (función pura, `Math.ceil(borde inferior de los controles − borde superior de la zona) + 8`, y 0 sin controles), con tests de los casos y del redondeo. El hook solo mide.
  - El contenido de la tarjeta sigue montado al cerrarse, para que la salida pueda animarse; `inert` evita que reciba clic o teclado durante esos 240 ms.
  - Las dos filas se deciden con una consulta de contenedor (zona por debajo de 576 px, es decir, tarjeta por debajo de 560 px), no con el ancho de la ventana.
- **Observador:** raíz `.notice-host`, `{ childList: true, subtree: true }`, sin atributos ni `characterData` (el cambio de tamaño de la atribución lo sigue el `ResizeObserver` de los controles). Solo vuelve a buscar los controles cuando cambia el elemento, y `--free-top` se escribe solo si cambia el valor.
- **Contadores del observador** (mismas opciones y raíz que el hook, creado desde `evaluate_script`, con 301 movimientos de ratón sintéticos por arrastre):
  - Sin red, un arrastre de 5 s: 0 llamadas durante el arrastre y 2 al asentarse (cambio del panel). Con `attributes` habrían sido 294 llamadas y 588 registros, todos del mapa. `setProperty('--free-top')`: 0 llamadas.
  - Con red, tres arrastres de 5 s con 1,5 s de pausa: 0 llamadas durante cada arrastre y 2 en cada pausa o cierre, todas del panel, con una petición al API por tramo y cuadros distintos. `--free-top`: 0 escrituras.
- **Regresión de la región `sr-only`:** al ser `absolute` sin anclar dentro de un contenedor flex alineado al final, caía en el borde inferior de la zona y asomaba 1 px (`scrollHeight` 801 en 800 px de alto): aparecía una barra de desplazamiento de 15 px y todo se estrechaba. Se vio en el navegador, no en vitest. Se añadió un test (rojo con `expected [ 'sr-only' ] to deeply equal ArrayContaining ["top-0", "left-0"]`) y se corrigió con `top-0 left-0`; después, 1280 × 800 exactos sin barra.
- **Tests:** siete rojos antes de implementar, cada uno por su razón (sin `notice-zone`, sin `sr-only`, sin `notice-card` ni `data-open`, sin `aria-hidden`, sin indicador y CSS vacío); después `inert` y `freeZoneTop`, con rojo por el valor esperado, y el anclaje de la región. El test del contenedor superpuesto afirmaba antes que el primer `div` llevaba `absolute inset-x-0 top-0`; ahora, que lleva `notice-zone` y que su regla de `notice.css` declara `position: absolute`, `z-index: 20` y `pointer-events: none`.
- **Medidas en el navegador** (la zona de contenido mide lo mismo con aviso y sin él; consola sin errores propios):
  - **1280 × 800:** `--free-top` 126 px; zona en `top` 126, `bottom` 0 y `left` 400; tarjeta de 560 × 74 px (x 560 a 1120) a 8 px del fondo; indicador de 24 × 24; «Reintentar» de 135,5 × 44 y «Cerrar aviso» de 147,9 × 44; sin cruces con la barra, el zoom, la atribución ni el panel.
  - **375 × 812:** zona con `bottom` 324,8 px (`--panel-height`) y `left` 0; tarjeta de 359 × 130 px en dos filas, a 8 px del panel. Sin panel (página no encontrada): `bottom` 0 y `left` 0, a 8 px del fondo.
  - **667 × 375 apaisado:** la tarjeta empieza 8 px bajo los controles (y 182) y queda sobre el panel; sin tocar la barra, el zoom ni la atribución.
  - **Cruce de los 900 px** con el aviso visible, en modo móvil y sin recarga: a 899 px `left` 0, `bottom` 280 y tarjeta de 560 × 74; a 900 px `left` 400, `bottom` 0 y tarjeta de 484 × 106 en dos filas.
  - **Cuatro casos de `bottom` y `left`** con captura: menos de 900 px con y sin panel, y desde 900 px con y sin panel. También con el error del mapa base (sin panel): `top`, `bottom` y `left` 0, tarjeta centrada y sin tocar el «Reintentar» del mapa.
  - **Puntero:** zona `none` y tarjeta `auto`; fuera de la tarjeta el hit-test devuelve el `canvas` y un arrastre mueve el mapa con el aviso abierto.
  - **Permanencia y navegación:** el aviso sigue abierto a los 83 s y tras navegar a otra página y volver, sin recarga; al recrearse el mapa `--free-top` pasa de 0 a 126 px en menos de 300 ms.
  - **Accesibilidad:** el árbol expone el mensaje una sola vez, dentro de la región; los botones van fuera de ella.
  - **Desenfoque:** con el tinte al 8 % (estilo en línea, solo en la página), sin filtro asoman la etiqueta «Beniparrell» y las carreteras bajo la tarjeta y con el filtro no: el desenfoque ve el mapa y la contención de la zona no lo impide.
  - **Movimiento:** con movimiento normal `transition-duration` 0,24 s; la salida se anima de verdad (a 60 ms sigue en `display: flex` con opacidad 0,68 y a unos 255 ms es `none`); con `reduce`, 0 s. `@starting-style`: la tarjeta entra con opacidad 0 y `translateY(8px)` y sube de forma continua hasta 1 a los 292 ms del clic.
  - **Durante la salida:** `inert` activo, el hit-test en el centro de los botones devuelve el `canvas`, 0 clics y 0 peticiones, y `focus()` sobre «Reintentar» no mueve el foco.
  - **Teclado y foco:** Tab hasta «Reintentar» y «Cerrar aviso», anillo sólido de 2 px `rgb(22, 71, 184)` a 2 px; Enter cierra y el foco acaba en «Salir».
  - **Contraste alto y colores forzados** (emulados): contraste alto, tinte `#edf3ff` sin filtro; colores forzados, fondo `Canvas`, borde de 2 px `CanvasText`, sin sombra ni filtro y botones con borde de 2 px (el indicador conserva su rojo, como se aceptó en la T2).
  - **Al 200 % del texto (aproximado, ver abajo):** tarjeta de 343 × 468 px, 8 px bajo los controles y sin tocar la barra, el zoom ni la atribución; tapa parte del panel, como prevé la spec.
- **No verificable con las herramientas:** la transparencia reducida (`emulate` no la admite) y el texto al 200 % (solo se aproximó con `font-size: 200%` en `html`, que no es el ajuste del navegador).
- **Incidencias de entorno:** pasar de no móvil a móvil con `emulate` recarga la página (entre viewports móviles, también con la red cortada, no). El servidor MCP no escribe fuera de su raíz de trabajo: ni capturas ni snapshots a un directorio temporal.
- **Salida sin la cookie `csrftoken`:** se borró la cookie y se pulsó «Salir» con un clic real. No apareció el aviso: el cliente reintenta una vez ante `csrf_failed`, y la secuencia fue `POST /api/v1/auth/logout/` 403, `GET /api/v1/auth/session/` 200 (cookie nueva) y `POST /api/v1/auth/logout/` 204. La barra pasó a «Registrarse», se anunció «Has salido» y el foco fue al enlace «Registrarse». La sesión de `t16-b@example.com` quedó cerrada así. `GET /api/v1/auth/session/` después: `{"user": null}`. No es un fallo de la 009: la secuencia prevista en `tasks.md` no podía producir el aviso, y se sustituyó por la del reintento desde el aviso. Esa secuencia comprueba en el navegador el reintento ante `csrf_failed` que quedó pendiente en la T4 y que el plan pide en «Comportamiento conservado».
- **Reintento con éxito desde el aviso** (con `t16-c@example.com`, registrada desde `/register` con `POST` 201 y comprobada con `GET /session/`): con la red cortada, clic real en «Salir» y aviso abierto; al devolver la red, clic real en «Reintentar»:
  - A los 100 ms: `data-open` ausente, `inert` activo, tarjeta aún en `display: flex` (salida en curso), región del aviso vacía, región global «Has salido», `document.activeElement` el enlace «Registrarse» y barra «Registrarse».
  - A los 600 ms y a los 1500 ms: lo mismo con la tarjeta en `display: none`.
  - Peticiones de salida: `POST /logout/` cortada (`net::ERR_INTERNET_DISCONNECTED`) y, tras devolver la red, `POST /logout/` 204. Consola: dos avisos de estilo de MapLibre y el `ERR_INTERNET_DISCONNECTED` del corte.
- **Dos `csrf_failed` seguidos en la salida:** lo cubre `frontend/src/api/session.test.ts`, en `describe("logout")`, el test «si el segundo intento vuelve a dar csrf_failed, es el error general y no hay un tercer envío». Simula `csrfFailed`, quién soy, `csrfFailed` y comprueba el resultado `{ kind: "failed", reason: "csrf" }` y las peticiones salida, sesión, salida, sin tercera. El caso con un solo fallo y éxito en el reintento es «ante csrf_failed pregunta quién soy y reintenta una vez, releyendo el token». No se ha reproducido en el navegador.

### T6. Lista blanca compartida e icono
- **Commits:** `f8cc84c` (`refactor(frontend): share svg whitelist rules`, con `svgWhitelist.ts` y `categorySvg.test.ts`) y `322318c` (`feat(frontend): add RentRadar icon`, con `icon.svg` e `icon.test.ts`).
- **Refactor:** los 45 `it` de `categorySvg.test.ts` (4 por cada una de las 11 imágenes y el de la lista de la semilla) son idénticos antes y después. El diff se revisó con `--color-moved` y `allow-indentation-change`: solo mueve reglas. Mutación de comprobación: añadir `<linearGradient/>` a `pool.svg` hace fallar el test de etiquetas con el módulo compartido. `TAG` y `ATTRIBUTE` se exportan; las listas de etiquetas y atributos siguen privadas.
- **`?raw` desde `public/`:** `import icon from "../../public/icon.svg?raw"` funciona sin cambiar la configuración de Vite ni de vitest ni añadir dependencias. Con esto queda comprobada la afirmación del plan sobre el icono; la de `index.html` sigue pendiente de la T7.
- **`icon.test.ts`, rojo y verde:** con un `icon.svg` provisional (solo el `path` del pin, válido para la lista blanca) fallaban 3 de 26, por su aserción:
  - «al menos tres rellenos distintos»: `expected 1 to be greater than or equal to 3`.
  - «la sombra es más oscura que la base y el brillo más claro»: `capa 1 del dibujo: expected undefined to be defined`.
  - «1,5:1 entre base, sombra y brillo»: `capa 1 del dibujo: expected undefined to be defined`.

  Los otros 23 pasaban ya con el provisional: las 4 reglas de la lista blanca, «sin limón» y «silueta 3:1» (la base ya era `#4A82EE`) y las 17 guardas (la referencia y los 16 casos negativos). Con el icono del plan, 26 de 26 en verde; el fichero es idéntico al SVG de `plan.md`.
- **Casos negativos** (cada uno parte de un icono válido y cambia un solo rasgo; el test exige que falle exactamente esa lista de reglas y que las demás no fallen):

  | SVG de prueba | Reglas que fallan |
  |---|---|
  | Degradado (`<linearGradient>`, `id`, `fill="url(#g)"`) | etiquetas, atributos y referencias |
  | `scale(2)` en `transform` | atributos |
  | Color de tres cifras (`#48E`) | atributos |
  | Etiqueta `<g>` | etiquetas |

- **Mutaciones sobre `icon.svg`** (una cada vez, con copia fuera del repositorio; tras cada una, `cmp` y sha256 iguales al original). Cada una hizo fallar solo su test, por su aserción, y los otros 25 siguieron en verde. Colores comprobados antes fuera del repositorio:

  | Mutación | Test que falla | Aserción |
  |---|---|---|
  | Punto (capa 5) a `#F5D547` | ninguna capa usa el limón | `expected '#F5D547' not to be '#F5D547'` |
  | Base (capa 0) a `#8FB3F5` (2,11:1 contra blanco; mantiene el orden de luminancias, 6,66:1 con la sombra y 1,62:1 con el brillo) | la silueta se distingue del blanco al menos 3:1 | `expected 2.1138… to be greater than or equal to 3` |
  | Brillo y sombra intercambiados | la sombra es más oscura que la base y el brillo más claro | `expected 0.7533… to be less than 0.2359…` |
  | Brillo (capa 1) a `#5A8EF0` (más claro que la base, 1,15:1) | 1,5:1 entre la base y la sombra y el brillo | `expected 1.1474… to be greater than or equal to 1.5` |

- **Contrastes calculados en el test** (WCAG 2.x), iguales a los del plan: base `#4A82EE` contra sombra `#0F2763` 3,84; contra brillo `#D3E2FD` 2,81; contra blanco 3,67. Luminancias: sombra 0,0245 < base 0,2359 < brillo 0,7533.
- **Verificación:** vitest, 30 ficheros y 1082 tests; eslint de `icon.test.ts` sin avisos; `npm run build` en verde, con `dist/icon.svg` idéntico a `public/icon.svg`. `package.json` y `package-lock.json` sin cambios.
- **Incidencia de entorno:** la primera sesión de la T6 arrancó en segundo plano y su guardián obligó a trabajar en un worktree aparte. El refactor se hizo y se commiteó allí y llegó a la rama con un avance rápido, con el mismo hash (`f8cc84c`). Al cerrar Claude Code puede quedar vivo un proceso `claude daemon run --origin transient`.

### T7. Marca en la barra e icono de la pestaña
- **Commit:** `e2dc7e7` (`feat(frontend): show the RentRadar icon in the top bar and tab`, con `TopBar.tsx`, `TopBar.test.ts`, `indexHtml.test.ts` e `index.html`).
- **Decisiones:**
  - **Utilidades en vez de clase de componente:** el enlace de la marca lleva `min-h-11 min-w-11` y `hover:bg-ink/6` como utilidades, porque el plan solo crea clases de componente para botones, campos, superficies y aviso (D1). `min-w-11` hace falta porque por debajo de 900 px el enlace solo contiene el icono, de 36 px.
  - **`rounded-lg`:** esquinas de 8 px para que el fondo del hover y el anillo tengan esquinas redondeadas.
  - **`px-1`:** la captura a 1280 px con el puntero sobre la marca mostraba la «r» de «RentRadar» pegada al borde del fondo del hover (0 px). Con `px-1` quedan 4 px a cada lado y a 375 px el enlace sigue midiendo 44 × 44 (36 + 8). El test no cambia.
  - **Nombre oculto con `sr-only`**, no con `hidden`, para que siga siendo el nombre accesible; se muestra desde 900 px con `min-[900px]:not-sr-only`, la misma forma que usa el panel.
- **Tests:** 6 rojos antes de implementar, cada uno por su aserción, y los 13 de `TopBar.test.ts` que ya existían siguen en verde (en total 19 en los dos ficheros):

  | Test | Rojo |
  |---|---|
  | La marca mide 44 px de ancho (`min-h-11` y `min-w-11`) | `expected [ 'inline-flex', 'min-h-11', …(3) ] to deeply equal ArrayContaining` |
  | Icono decorativo de 36 × 36 | `expected {} to deeply equal { src: '/icon.svg', alt: '', … }` |
  | Nombre en un `span` con `translate="no"` | `expected undefined to be 'no'` |
  | Nombre con `sr-only` por debajo de 900 px y visible desde 900 px, sin `hidden` | `expected [ '' ] to deeply equal ArrayContaining` |
  | `index.html` declara un solo icono, `/icon.svg` | `expected [ { rel: 'icon', href: 'data:,' } ] to deeply equal [ { rel: 'icon', href: '/icon.svg', type: 'image/svg+xml' } ]` |
  | `index.html` ya no declara `data:,` | `expected '<!doctype html>…' not to contain 'data:,'` |

  Después, vitest completo: 31 ficheros y 1088 tests en verde; eslint de los tres ficheros sin avisos; `npm run build` en verde, con `dist/index.html` apuntando a `/icon.svg` y `dist/icon.svg` presente. `package.json` y `package-lock.json` sin cambios.
- **`?raw` lee `index.html`:** `import html from "../../index.html?raw"` funciona sin cambiar la configuración ni añadir dependencias. Con esto se cierra lo que la T6 dejó pendiente para esta tarea.
- **Recorrido en el navegador** (sin sesión; Chrome 156; `/map`, `/register` y `/no-existe`, a 375 y 1280 px; el hover y el anillo con teclado, también a 899 y 900 px):

  | Punto | Resultado | Valor medido |
  |---|---|---|
  | Nombre oculto a 375 px | OK | `sr-only`: 1 × 1 px, `clip-path: inset(50%)`, en las tres páginas |
  | Nombre visible a 1280 px | OK | 104 × 28 px, `position: static`, en las tres páginas |
  | Nombre accesible «RentRadar» | OK | Árbol de accesibilidad: `link "RentRadar"` a 375, 899 y 1280 px; el `<img alt="">` no se anuncia |
  | Enlace de al menos 44 × 44 | OK | Con `px-1`: 44 × 44 a 375 y 899 px; 156,1 × 44 a 900 y 1280 px (148,1 × 44 antes de `px-1`) |
  | Barra sin desbordar con «Registrarse» | OK | `scrollWidth` igual a `clientWidth` en la barra y en el documento a 375, 899, 900 y 1280 px; «Registrarse» termina en x = 359 a 375 px; la barra mide 56 px |
  | Cruce de 899 a 900 px, sin recarga | OK | A 899 px el nombre es `absolute` (1 × 1) y a 900 px `static` (104 px); la marca puesta en `window` se conserva; el nombre accesible no cambia |
  | Anillo del enlace, con teclado | OK | `outline` 2 px sólido `rgb(22, 71, 184)` con separación de 2 px, medido a 375, 899, 900 y 1280 px; el contorno ocupa de x = 12 y de y = 1,5 a 53,5, dentro de la barra, con `overflow: visible`; visible en la captura |
  | Hover del enlace | OK | Fondo de tinta al 6 % (`oklab(0.208 … / 0.06)`), radio de 8 px; con `px-1`, 4 px de aire a cada lado de la imagen y del nombre |
  | `/icon.svg` | OK | `fetch` sin caché: 200, `image/svg+xml`, 502 bytes; `link rel=icon` e `<img>` apuntan a `http://localhost:5173/icon.svg`. La petición del favicon no aparece en la red de la página; la del `<img>` salió con 304 por la caché |
  | Consola sin errores | OK | Sin mensajes en `/register` y `/no-existe`; `/map` solo tiene dos avisos de estilo de MapLibre (`highway-shield-non-us` y `highway-shield-us-interstate`), los mismos de la T5 |

  El recorrido de las tres páginas se hizo antes de añadir `px-1`; tras añadirlo se volvieron a medir el enlace, la barra y el anillo en `/register`, a 375, 899, 900 y 1280 px, porque el cambio es solo de relleno del mismo componente.
- **Icono a 16 y 32 px:** el `/icon.svg` real, con `width` y `height` sustituidos por el tamaño y dibujado en un lienzo del mismo tamaño a `devicePixelRatio` 1. Solo se cuentan píxeles interiores (alfa 255 sobre lienzo transparente), no los de borde. Con `colorScheme` claro y oscuro el resultado es idéntico (mismo hash): el lienzo no depende del tema.

  | Medida (criterio) | 16 × 16 | 32 × 32 | Umbral |
  |---|---|---|---|
  | Píxeles puros de la base `#4A82EE` | 26 | 165 | informativo |
  | Sombra (el píxel interior más oscuro) frente a la base | 3,84 (`#0F2763`, píxel 11,8) | 3,84 (píxel 23,13) | 1,5 |
  | Brillo (el mejor píxel interior de los 3 × 3 alrededor del centro del brillo, sin contar los de la esfera) frente a la base | 2,58 (`#C6D9FC`, píxel 4,3; ninguno llega a `#D3E2FD`) | 2,81 (`#D3E2FD`, píxel 9,6) | 1,5 |
  | Silueta (píxel puro de la base) contra `#FFFFFF` | 3,67 | 3,67 | 3 |
  | Silueta contra `#202124` | 4,38 | 4,38 | 3 |
  | Silueta contra `#35363A` | 3,29 | 3,29 | 3 |
  | Centroide de la sombra frente al de la esfera | (10; 9) frente a (7; 6,25) | (20,72; 17,72) frente a (15,18; 12,87) | abajo y a la derecha |

  A 16 px el brillo mide unos 2 px y el suavizado lo mezcla con la base: queda por encima del 1,5:1 con 2,58, sin llegar al 2,81 del icono a tamaño completo. Los píxeles de borde (42 de 133 a 16 px y 91 a 32 px) se mezclan con el fondo y bajan hasta 1:1: no son un criterio de la spec y no se cuentan.
- **Gris de las pestañas:** valores supuestos, `#202124` (pestañas inactivas) y `#35363A` (pestaña activa), con Chrome 156 (`Chrome/156.0.0.0`, Linux). No se capturó el sistema, porque saldría el escritorio entero y no solo Chrome.
- **La pestaña real no se puede capturar con el MCP:** las capturas de página no incluyen la barra de pestañas. Por eso la comprobación es el icono real dibujado en un lienzo, como prevé el plan.
- **Incidencias de entorno:** la primera medición salió con el esquema «dark» del sistema, sin emular; se repitió con `colorScheme` claro y oscuro explícitos. `emulate` con `isMobile` recarga la página, como en la T5. El servidor MCP no escribe fuera de su raíz de trabajo (ver la T5): los resultados se leyeron en línea.

### T8. Pulido de la página
- **Commit:** `b2de3b0` (`feat(frontend): polish page head, number units and titles`, con `index.html`, `index.css`, `format.ts`, `format.test.ts`, `AssetCard.tsx`, `ResultsPanel.test.ts`, `RegistrationForm.tsx`, `NotFoundPage.tsx` e `indexHtml.test.ts`).
- **`theme-color`:** `#FFFFFF`, el fondo de la barra (`bg-white`). Se eligió porque ni la spec ni el plan fijan un valor; solo nombran la etiqueta.
- **Precarga de la fuente: no se hace.** El build saca las fuentes con hash en el nombre (por ejemplo `bricolage-grotesque-latin-wght-normal-DLoelf7F.woff2`), así que escribir ese nombre a mano en `index.html` se rompería sin avisar al actualizar el paquete. Además es opcional y está fuera de la spec. Es lo que `tasks.md` pide anotar; en las notas de la T1 no consta una comprobación de ruta estable.
- **Preconexión:** `<link rel="preconnect" href="https://tiles.openfreemap.org" crossorigin>`. Lleva `crossorigin` porque MapLibre pide el estilo y las teselas en modo CORS, y sin ese atributo el navegador no reutiliza la conexión.
- **Espacio duro:** `formatRadius` usa el escape de U+00A0 dentro del template literal. Las herramientas de edición convierten los escapes `\uXXXX` en el carácter literal (invisible en el diff), así que `format.ts` se escribió con un script de Python fuera del repositorio, con `chr(92)`; después se comprobó con `grep` que ningún fichero tocado contiene el carácter literal. En `AssetCard.tsx` se usa la entidad `&nbsp;`, visible en el diff, como ya hacía la línea.
- **eslint y U+00A0 literal** (solo comprobación, sin cambiar la configuración; `--print-config` y `--stdin` con `--stdin-filename`): `no-irregular-whitespace` está activa como error en `format.ts` y `AssetCard.tsx` (viene de `js.configs.recommended`) con `skipStrings: true`, `skipTemplates: false`, `skipJSXText: false`, `skipComments: false` y `skipRegExps: false`. Un U+00A0 literal dentro de un template literal (`format.ts`) y en texto JSX (`AssetCard.tsx`) da error (`Irregular whitespace not allowed`); en una cadena entre comillas no da aviso (`skipStrings`), y el escape de U+00A0 en un template tampoco. No cubre CSS ni HTML.
- **Tests, de rojo a verde:** 7 rojos antes de implementar, cada uno por su razón, de 92 en los tres ficheros afectados:

  | Test | Rojo |
  |---|---|
  | `indexHtml`: `theme-color` | `expected [] to deeply equal [ { name: 'theme-color', … } ]` |
  | `indexHtml`: `color-scheme` | `expected [] to deeply equal [ { name: 'color-scheme', … } ]` |
  | `indexHtml`: preconexión con `crossorigin` | `expected [] to deeply equal [ { rel: 'preconnect', … } ]` |
  | `format`: 500 m, 1 km y 2 km (3 tests) | `expected '500 m' to be '500 m'` (el recibido llevaba espacio normal; el espacio duro no se ve en el mensaje) |
  | `ResultsPanel`: espacios duros alrededor de «/» | falla `toContain` de la cadena con espacio duro antes y después de «/»: la tarjeta traía uno antes y un espacio normal después |

  - **Guarda desde el principio:** el caso de `formatPrice` (`12,50 €` y `30 €` con espacio duro antes de «€») pasó sin implementar, porque `Intl.NumberFormat("es-ES")` ya devuelve U+00A0.
  - **Después:** los 3 ficheros dan 92 de 92; vitest completo, 31 ficheros y 1092 tests en verde; eslint de los ficheros tocados sin avisos; `npm run build` en verde, con las tres etiquetas en `dist/index.html`. `package.json` y `package-lock.json` sin cambios.
- **Navegador** (sin sesión; `/map`, `/register` y `/no-existe`, a 375 y 1280 px):

  | Punto | Resultado | Valor medido |
  |---|---|---|
  | Etiquetas de la cabecera | OK | `theme-color` `#FFFFFF`, `color-scheme` `light` y `preconnect` a `https://tiles.openfreemap.org` con `crossorigin` (`crossOrigin` = `anonymous`), a 375 y 1280 px |
  | `color-scheme` calculado en `:root` | OK | `light` |
  | `text-wrap` de los `h1` | OK | `balance` en «Crear una cuenta» y «Página no encontrada», a 375 y 1280 px |
  | `touch-action` | OK | `manipulation` en «Registrarse», «Crear cuenta», «Mostrar contraseña» (el ojo), «Ir al mapa», «Reintentar» y «Cerrar aviso» |
  | Distancias a 375 px | OK | Las 24 tarjetas: un `Range` sobre la cifra y su unidad ocupa una sola línea (`getClientRects`, una sola posición vertical); separador U+00A0 en las 24 |
  | Importes a 375 px | OK | Las 24: «cifra y €» en una línea con U+00A0 antes de «€», y « / unidad» con U+00A0 a ambos lados; el precio entero cabe en una línea |
  | Mismo recorrido a 1280 px | OK | 24 de 24, sin cortes |
  | Consola sin errores propios | OK | Sin mensajes en `/register` y `/no-existe` a 375 y 1280 px; `/map` solo tiene los dos avisos de estilo de MapLibre (`highway-shield-non-us` y `highway-shield-us-interstate`), a 375 y 1280 px |

- **Texto al 200 % (dato informativo):** con `font-size: 200%` en `html` (que no es el ajuste real del navegador), a 375 px, cifra y unidad siguen en una línea en las 24 tarjetas y el precio entero también. La frase «Zona de unos…» sí se parte en varias líneas, como es normal: solo se comprobó que la cifra y su unidad no se separan.
- **NO VERIFICABLE con el MCP:** que la preconexión reutilice de hecho la conexión del estilo y de las teselas. Solo se ve la etiqueta y su atributo, no el reparto de conexiones.

### Medición de rendimiento de prueba (no oficial)
Fecha: 2026-11-10 · A: `d458e30` · B: `0ad08b7` · 375 px, táctil, CPU 4× · orden A, B, B, A (T1-A, T2-B, T3-B, T4-A), una pestaña por traza.
- **Conclusión:** procedimiento validado: dos compilaciones servidas, gesto reproducible, recuento por fotograma y perfil de CPU. La GPU solo se ve de forma indirecta. La métrica de la spec está saturada en este portátil, con unos 60 fps y casi 0 % de perdidos en las dos versiones, y no distingue A de B. Sin veredicto sobre los 22 px.
- **Fotogramas** (fps; perdidos): T1-A 59,82; 0 %. T2-B 59,87; 0,33 %. T3-B 59,54; 0,33 %. T4-A 59,67; 0 %.
  - Los 0,33 % de B son un fotograma sin presentar completo en los primeros 90 ms del gesto: a los 25 ms, solo con `DROPPED`, en T2-B; a los 85 ms, solo con `PRESENTED_PARTIAL`, en T3-B. A no tiene ninguno.
  - Cada traza de B tiene además un intervalo de 33,3 ms entre `requestAnimationFrame` medido por el script; A no tiene ninguno. Son dos datos separados: el script no guardó el instante del intervalo y, con los `FireAnimationFrame` de la traza, el hueco coincide con el fotograma sin presentar en T2-B y no en T3-B (unos 22 ms de diferencia).
  - Fotogramas en pareja (`PRESENTED_ALL` más `PRESENTED_PARTIAL`): 99,3 % a 99,7 % en las cuatro. En el calentamiento B lo estuvo solo la mitad de la ventana, así que no se usa como medida del cristal.
- **Hilo principal:** A 2688 y 2843 ms; B 3224 y 2998 ms, +12,5 % de media.
  - Las dos trazas de B quedan por encima de las dos de A: por azar saldría 1 de cada 6 veces. La dirección (B por encima) la fijó el calentamiento (+14 %) antes de grabar A, B, B, A.
  - Perfil de CPU: +360 ms, de ellos +243 en MapLibre y sus librerías y +44 en llamadas nativas a WebGL, sin muestras de `flush`, `finish` ni `readPixels` (`drawElements` pasa de 25 a 29 ms).
  - Ralentización casi uniforme (+10 % a +19 %) en MapLibre, WebGL, recolección de basura e incluso `dispatchEvent` del script del gesto. El código de la app no aparece en el perfil.
- **GPU:**
  - `GPUTask` no distingue las versiones (A 335 y 373 ms; B 357 y 342 ms), y todas llevan el `renderer_pid` de la pestaña.
  - La traza del MCP no tiene eventos de dibujo de viz ni de Skia en el proceso de GPU: el coste del desenfoque solo se ve de forma indirecta.
  - `VizCompositorThread` +42 % (A 216 y 234 ms; B 323 y 314 ms): pista encontrada a posteriori, mirando varios hilos con las trazas ya grabadas. Sin probabilidad.
  - T4-A tiene `CrGpuMain` anómalo (3784 ms, 232 tareas de unos 13 ms): causa desconocida y sin efecto en los fotogramas.
- **Límites:** GPU integrada del portátil (AMD Lucienne), no la de un móvil; el 4× solo frena la CPU; dos trazas por versión, con una diferencia entre las dos de la misma versión del 5 % al 7 % en el hilo principal y de hasta el 11 % en la GPU; escena solo con el panel, porque el aviso de cristal aún no existe; solo Chromium.
- **Herramientas y trazas** (fuera del repositorio): `~/rentradar-perf/tools` (scripts del gesto y del análisis, con `LEEME.txt`) y `~/rentradar-perf/prueba-2026-11-10` (seis trazas: calentamiento y las cuatro de arriba).

### Pendiente para la validación
- Medición de rendimiento A/B con la CPU a 4×, calentamiento y seis pasadas alternadas.
- Comparación de los colores de «positron» con una descarga nueva del estilo.
- Texto al 200 % con el ajuste real del navegador y transparencia reducida del sistema: no se pueden emular con las herramientas (ver la T5).
- Dos `csrf_failed` seguidos en la salida: cubiertos solo por vitest; no se ha reproducido en el navegador.
- Gris real de las pestañas de Chrome: `#202124` y `#35363A` son valores supuestos (ver la T7); si la validación puede medirlos, manda la medición.
- Ninguna sesión abierta: `/sdd-validate` pedirá una cuenta nueva, con autorización expresa, si repite alguna comprobación con «Salir».
- Para el `/sdd-change` de la medición oficial: la T5 comprobó que el aviso sigue abierto mientras se arrastra el mapa, así que se cumple la condición para que la escena con panel y aviso entre en ella.
