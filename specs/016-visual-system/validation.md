# Validación — 016-visual-system
Rama: `feature/016-visual-system` · Entorno: frontend en el host (Vite 8.3.5, Vitest 5.0.5, Tailwind 4.3.3, maplibre-gl 6.14.0), Chrome DevTools MCP y stack de Docker Compose para la API pública

Validación en curso: T1 a T3 hechas. La validación completa (cada RF, contraste, rendimiento, accesibilidad, recorrido con teclado) se escribe al cierre con `/sdd-validate`. Hasta entonces este fichero recoge las notas de implementación, para que no se pierdan.

## Notas de implementación (T1–T3)
Fecha: 2026-11-10 · Commits: T1 `e252367`, T2 `9355bdb`, T3 `4ea4c34`. Cada tarea cierra con vitest, eslint de los ficheros tocados y `npm run build` en verde: tras la T3, 27 ficheros y 1038 tests. `package.json` y `package-lock.json` no cambian.

### Estado del entorno
| Elemento | Estado |
|---|---|
| Línea base A del rendimiento | `~/rentradar-perf/a`, compilada del commit `d458e30` (`docs(spec-016): tasks`), antes de la T1. `index.html` y `assets/` comprobados; idéntica a `frontend/dist` en el momento de la copia. |
| Vite de desarrollo | Puerto 5173, en la terminal del desarrollador. No se lanza, para ni relanza desde la sesión. |
| Stack de Docker Compose | `backend` y `db` arriba y sanos. La T3 solo lee la API pública. |
| Cuenta de prueba | `t16-a@example.com`, creada en la T1 en la BD de desarrollo desde el formulario de registro. Su sesión se cerró por un clic accidental (`POST /api/v1/auth/logout/` 204 a las 08:11:37 UTC). La T4 necesita una cuenta nueva, con autorización expresa del desarrollador en ese momento. La contraseña se generó en la página y no se guardó. |
| Navegador | Pestaña 3 abierta, sin sesión. Las pestañas de prueba aisladas se cierran al terminar. El perfil de Chrome DevTools MCP solo admite un navegador: con otro servidor `chrome-devtools-mcp` activo, `new_page` falla con «already running». |

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
- **Arrastre sintético del mapa:** el desplazamiento con eventos de ratón sintéticos funciona a 1280 px sin táctil. Con la emulación táctil a 375 px no se ha probado, y es relevante para el gesto de la medición de rendimiento.
- **Test vigilado con mutación:** `surfaces.test.ts` se probó con el alfa de `--glass-bg` a 0,79, sobre el propio fichero de la tarea (aún sin commitear) con copia de seguridad fuera del repositorio. Falla un solo test, `el tinte del cristal tiene al menos el 80 % de opacidad`, con `expected 0.79 to be greater than or equal to 0.8`; los otros 5 pasan. Restaurado a 0,88: 6 de 6 y sha256 idéntico antes y después (`adf89ed0889309ff524ccfd595a3a8ba7d4632f7029524e13b5dece1bf0d0fb9`, también con `cmp` contra la copia). Antes de eso el test falló primero por `ENOENT` (el fichero no existía) y después por la cadena vacía de Vitest, no por la razón de fondo.
- **`vite.config.ts`:** una línea, `test.css: { include: [/\.css\?raw$/] }`, porque Vitest sustituye por vacío los CSS importados, incluso con `?raw`. Leer el fichero con `node:fs` habría exigido `@types/node`, que no está instalado. No cambia el build ni las dependencias.
- **Decisiones respecto al plan:**
  - El radio queda fuera de `.glass` y lo aplica cada superficie con `--radius-surface`.
  - La variable `--glass-filter` sustituye a `--glass-blur`, para que el respaldo deje `backdrop-filter: none` y no `blur(0)`.
  - El secundario sobre cristal redefine `--btn-secondary-bg` y su hover directamente, sin `--glass-btn-bg`.
  - La miniatura de la tarjeta pasa de 12 a 16 px, como en la variante aprobada.
  - `surfaces.test.ts` se añade a los tests previstos.
- **Capturas** del panel (1280 y 375 px, sobre el peor fondo y en colores forzados) en `prototypes/016-visual-system/capturas/`, que no se versiona.

### Pendiente para la validación
- Medición de rendimiento A/B con la CPU a 4×, calentamiento y seis pasadas alternadas.
- Un gesto de arrastre con emulación táctil a 375 px (ver la nota del arrastre sintético).
- Comparación de los colores de «positron» con una descarga nueva del estilo.
- Estados de la T4 y la T5 con una cuenta nueva.
