# Validación — 016-visual-system
Rama: `feature/016-visual-system` · Entorno: frontend en el host (Vite 8.3.5, Vitest 5.0.5, Tailwind 4.3.3, maplibre-gl 6.14.0), Chrome DevTools MCP y stack de Docker Compose para la API pública

Validación en curso: T1 a T4 hechas. La validación completa (cada RF, contraste, rendimiento, accesibilidad, recorrido con teclado) se escribe al cierre con `/sdd-validate`. Hasta entonces este fichero recoge las notas de implementación, para que no se pierdan.

## Notas de implementación (T1–T4)
Fecha: 2026-11-10 (T1–T3) y 2026-11-11 (T4) · Commits: T1 `e252367`, T2 `9355bdb`, T3 `4ea4c34`, T4 `6453e26`. Cada tarea cierra con vitest, eslint de los ficheros tocados y `npm run build` en verde: tras la T3, 27 ficheros y 1038 tests; tras la T4, 27 ficheros y 1043 tests. `package.json` y `package-lock.json` no cambian.

### Estado del entorno
| Elemento | Estado |
|---|---|
| Línea base A del rendimiento | `~/rentradar-perf/a`, compilada del commit `d458e30` (`docs(spec-016): tasks`), antes de la T1. `index.html` y `assets/` comprobados; idéntica a `frontend/dist` en el momento de la copia. |
| Vite de desarrollo | Puerto 5173, en la terminal del desarrollador. No se lanza, para ni relanza desde la sesión. |
| Stack de Docker Compose | `backend` y `db` arriba y sanos. La T3 solo lee la API pública. Al empezar la T4 estaba parado (el proxy de Vite devolvía 502) y se levantó antes de repetir el registro. |
| Cuentas de prueba | `t16-a@example.com`, creada en la T1 en la BD de desarrollo desde el formulario de registro: su sesión se cerró por un clic accidental (`POST /api/v1/auth/logout/` 204 a las 08:11:37 UTC). `t16-b@example.com`, creada en la T4 con autorización expresa, también desde el formulario, con la sesión abierta para la T5. Las contraseñas se generaron en la página y no se guardaron. |
| Navegador | Una pestaña abierta, con la sesión de `t16-b@example.com`. Las pestañas de prueba aisladas se cierran al terminar. El perfil de Chrome DevTools MCP solo admite un navegador: con otro servidor `chrome-devtools-mcp` activo, `new_page` falla con «already running». |

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
- Estados de la T5 con la sesión de `t16-b@example.com`, abierta. Si se pierde, cuenta nueva con autorización expresa.
- Al final de la T5: el reintento ante `csrf_failed` y el reintento con éxito, que cierra la sesión y por eso va el último.
