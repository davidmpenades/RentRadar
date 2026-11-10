# Plan 016 — Sistema visual
Spec: specs/016-visual-system/spec.md (aprobada)

## Resumen
Solo frontend: ni API, ni modelo de datos, ni dependencias. Los estilos comunes pasan a cuatro ficheros de clases de componente (botones, campos, superficies y aviso) sobre los tokens de `@theme`, y las pantallas existentes los usan. El aviso de fallo de salida se reescribe como superficie de cristal anclada a la zona libre del mapa, con «Cerrar aviso». El icono de RentRadar es un SVG único en `public/` que usan la barra y la pestaña, y la lista blanca de SVG de la 006 pasa a un módulo que comparten su test y el del icono.

La variante elegida es la **B «escarchado»**. Los prototipos no se versionan: este plan es la única fuente de sus valores.

## Valores de la variante B
### Superficies (panel y aviso de cristal; barra y tarjeta del registro sólidas)
| Valor | Fijado |
|---|---|
| Tinte del cristal | `#ECF3FF` al 88 % (`rgb(236 243 255 / 0.88)`) |
| Desenfoque | 22 px |
| Superficie sólida (respaldo) | `#EDF3FF`, misma forma, borde y sombra |
| Radios | superficies 24 px (panel: esquinas superiores por debajo de 900 px, derechas desde 900 px), aviso 22 px, tarjetas 16 px, campos 12 px, botones píldora |
| Borde | 1 px blanco al 95 % (`rgb(255 255 255 / 0.95)`) |
| Sombra | `0 10px 36px rgb(24 44 96 / 0.26), 0 0 0 1px rgb(24 44 96 / 0.08), inset 0 0 0 2px rgb(255 255 255 / 0.7), inset 0 3px 0 #ffffff` (el filo de luz: anillo interior de 2 px y brillo superior de 3 px) |
| Sombra del campo | `inset 0 2px 0 rgb(24 44 96 / 0.08)` |
| Anchura máxima del aviso | 560 px; por debajo de 560 px el texto y los botones van en dos filas |
| Transiciones | 0,14 s (relieve, estado de campo); 0,24 s (aparición y salida del aviso: opacidad y 8 px de desplazamiento); solo con `prefers-reduced-motion: no-preference` |

### Botones (píldora, 16 px semibold, mínimo 44 × 44 px)
| Pieza | Valor |
|---|---|
| Principal, fondo | degradado vertical `#3468DB` → `#1647B8`, borde 1 px `#123F9F`, texto blanco, relleno lateral 26 px |
| Principal, hover | degradado `#2C5FD2` → `#123F9F` |
| Principal, reposo | `0 2px 4px rgb(15 39 99 / 0.22), 0 12px 24px -6px rgb(22 71 184 / 0.55), inset 0 1px 0 rgb(255 255 255 / 0.25)` |
| Principal, pulsado | `0 1px 2px rgb(15 39 99 / 0.22), 0 3px 8px -3px rgb(22 71 184 / 0.4), inset 0 1px 0 rgb(255 255 255 / 0.12)` y escala 0,97 (el desenfoque de la sombra pasa de 12/24 px a 3/8 px) |
| Principal de formulario | 48 px de alto, relleno lateral 32 px; con el puntero la sombra pasa a `0 2px 4px rgb(15 39 99 / 0.26), 0 16px 30px -6px rgb(22 71 184 / 0.68), inset 0 1px 0 rgb(255 255 255 / 0.25)`. Solo «Crear cuenta»; el resto mide 44 px |
| Secundario sobre superficie blanca (barra, tarjeta del registro) | relleno cielo `#DFE8FF` (hover `#D3E0FF`), borde 1 px `rgb(255 255 255 / 0.9)`, texto tinta |
| Secundario sobre cristal | relleno `rgb(255 255 255 / 0.7)` (hover `0.9`), mismo borde y sombra, sin desenfoque propio (decisión D3) |
| Secundario, reposo | `0 1px 2px rgb(30 45 80 / 0.08), 0 6px 16px -6px rgb(30 45 80 / 0.16), inset 0 1px 0 rgb(255 255 255 / 0.9)` |
| Secundario, pulsado | `0 0 1px rgb(30 45 80 / 0.1), 0 2px 6px -3px rgb(30 45 80 / 0.14)` y escala 0,97 (la sombra de 6/16 px pasa a 2/6 px) |
| Secundario en superficie sólida | relleno `#DFE8FF` (hover `#D3E0FF`) |
| Deshabilitado (`aria-disabled="true"`) | sin sombra, opacidad 0,6, `cursor: not-allowed`, sin hover ni pulsado |
| Colores forzados | contorno de 2 px `ButtonText` y sin sombra; deshabilitado en `GrayText` |

### Campo, ojo, indicador y anillo
- **Campo**: borde 2 px `#424B5A`, fondo blanco, radio 12 px, sombra interior del campo, mínimo 44 px, solo lectura al 70 % de opacidad. `aria-invalid="true"` → borde `#B3261E`. El botón propio de ver contraseña de Edge se oculta con `::-ms-reveal` y `::-ms-clear`.
- **Ojo**: botón de 44 × 44 px dentro del campo, al final, con el radio del campo, fondo transparente (hover: tinte tinta al 6 %), icono de 24 px en `currentColor`. Nombre accesible fijo «Mostrar contraseña», `aria-pressed`, `aria-controls`.
- **Indicador**: círculo de radio 10 con `M12 7v6M12 16.5v.5`, `viewBox="0 0 24 24"`, trazo 2 redondeado, `currentColor` con el color de error; 24 px en el aviso y en el error general, 18 px junto a los mensajes de campo.
- **Ojo abierto**: `M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z` más `circle cx=12 cy=12 r=3`. **Ojo tachado**: `M9.9 5.2A10 10 0 0 1 12 5c6.4 0 10 7 10 7a17 17 0 0 1-3.2 4M6.6 6.6A17 17 0 0 0 2 12s3.6 7 10 7c1.7 0 3.2-.4 4.5-1M9.9 9.9a3 3 0 0 0 4.2 4.2` más `M3 3l18 18`; los dos con trazo 2 redondeado.
- **Anillo de foco**: `outline: 2px solid #1647B8; outline-offset: 2px`, global (sustituye al de tinta de 3 px). Todo el subárbol del mapa (zoom, enlaces de la atribución y lienzo, que son lo que recibe el foco del teclado) conserva el anillo de la 006 (tinta, 3 px). El selector actual de `index.css` solo cubre el botón de zoom y el botón compacto de la atribución, que con `compact: false` no se muestra; la regla se amplía a `.maplibregl-map :focus-visible`.

### Icono de RentRadar (`icono-a` de los prototipos)
Pin con esfera de radar, `viewBox="0 0 64 64"`. Orden de dibujo, que es lo que usa el test para distinguir las capas:

| Orden | Capa | Forma | Relleno |
|---|---|---|---|
| 0 | tono base | `path` del pin | `#4A82EE` |
| 1 | brillo | `ellipse` en el borde superior izquierdo, `rotate(-45 20 14)` | `#D3E2FD` |
| 2 | sombra dura | `circle` desplazado 5 px abajo y a la derecha | `#0F2763` |
| 3 | esfera | `circle` | `#E6EFFF` |
| 4 | cuña | `path` | `#1647B8` |
| 5 | punto | `circle` | `#4A82EE` |

Cinco colores de relleno distintos; ninguno es el limón `#F5D547`. La silueta es solo el tono base.

```
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-hidden="true" width="64" height="64"><path d="M32 61 C22 51 10 40 10 26 A22 22 0 0 1 54 26 C54 40 42 51 32 61 Z" fill="#4A82EE"/><ellipse cx="20" cy="14" rx="7" ry="3.4" fill="#D3E2FD" transform="rotate(-45 20 14)"/><circle cx="37" cy="31" r="13" fill="#0F2763"/><circle cx="32" cy="26" r="13" fill="#E6EFFF"/><path d="M32 26 L32 16 A10 10 0 0 1 42 26 Z" fill="#1647B8"/><circle cx="26" cy="31" r="2.4" fill="#4A82EE"/></svg>
```

### Regla: el error sobre cristal
Sobre una superficie de cristal el error lleva solo el **indicador**; el texto va en tinta `#14181F`. El texto en `#B3261E` solo se usa sobre la tarjeta blanca del registro (6,54:1 contra blanco). Sobre el cristal al 88 % y el negro puro, `#B3261E` da 4,47:1: no llega a 4,5:1 como texto, pero sí al 3:1 del indicador. El aviso de salida (RF-6) sigue la regla por ese contraste. El error general del registro (RF-4) lleva el texto en tinta porque la spec lo pide, aunque vaya sobre la tarjeta blanca; los mensajes de cada campo, también sobre la tarjeta blanca, conservan el texto en color de error con su indicador.

### Colores nuevos y su contraste
Peor fondo: negro puro, cota de las etiquetas (contraste de WCAG 2.x con el tinte al 88 % compuesto sobre cada fondo de referencia; calculado con el tinte real). Umbrales: 4,5 texto normal, 3 componentes no textuales.

| Par | Color | Umbral | Cristal 88 % (negro puro) | Sólida `#EDF3FF` | Resultado |
|---|---|---|---|---|---|
| Texto principal | `#14181F` | 4,5 | 12,16 | 15,98 | Aprobado |
| Texto secundario | `#424B5A` | 4,5 | 6,02 | 7,91 | Aprobado |
| Texto del secundario sobre su relleno | `#14181F` | 4,5 | 15,96 (blanco al 70 %) | 14,51 (cielo `#DFE8FF`; hover 13,45) | Aprobado |
| Precio | `#1647B8` | 4,5 | 5,46 | 7,18 | Aprobado |
| Mensaje del aviso | `#14181F` | 4,5 | 12,16 | 15,98 | Aprobado |
| Texto en color de error sobre cristal | `#B3261E` | 4,5 | 4,47 | 5,87 | No llega en cristal: no se usa (regla anterior) |
| Icono de radio de la tarjeta | `#424B5A` | 3 | 6,02 | 7,91 | Aprobado |
| Anillo de foco | `#1647B8` | 3 | 5,46 (cristal), 6,89 (página `#E8EEFF`) | 7,18 (sólida), 7,99 (blanco) | Aprobado |
| Indicador de error | `#B3261E` | 3 | 4,47 | 5,87 (6,54 sobre blanco) | Aprobado |
| Borde del campo | `#424B5A` | 3 | — | 8,80 (blanco) | Aprobado |
| Icono del ojo | `#14181F` | 3 | — | 17,79 (blanco) | Aprobado |
| Texto blanco del principal | `#FFFFFF` | 4,5 | — | 5,06 contra `#3468DB`, 5,71 contra `#2C5FD2`, 7,99 contra `#1647B8` | Aprobado |

El borde del secundario no se mide (spec): contra el aviso sobre negro puro da 1,46:1. Con el tinte al 88 %, el precio azul llega a 5,46:1 (al 80 % daba 4,32:1). Los demás fondos de referencia (compuestos, 4,5 y más para texto): tinta 13,20–16,17, gris 6,53–8,00, azul 5,93–7,26 y error 4,85–5,94 sobre línea, agua, fondo, blanco y calle.

Colores del icono (el gris de las pestañas se mide en la validación; los de Chrome son provisionales):

| Comprobación | Valor | Umbral |
|---|---|---|
| Silueta `#4A82EE` contra blanco | 3,67 | 3 |
| Silueta contra el gris de las pestañas inactivas `#202124` | 4,38 | 3 |
| Silueta contra el gris de la pestaña activa `#35363A` | 3,29 | 3 |
| Tono base contra sombra `#0F2763` | 3,84 | 1,5 |
| Tono base contra brillo `#D3E2FD` | 2,81 | 1,5 |

Se mide también contra `#35363A` porque es el caso más exigente de los dos grises; si la versión de Chrome de la verificación da otros valores, manda la medición.

### Fondos de referencia del mapa base (estilo «positron»)
Origen: `https://tiles.openfreemap.org/styles/positron` (55 capas, descargado el 2026-11-07). Luminancia WCAG sobre el RGB.

| Elemento | Capa | Hex | Luminancia |
|---|---|---|---|
| Fondo | `background` | `#F2F3F0` | 0,8927 |
| Parques | `park` | `#E6E9E5` | 0,8076 |
| Agua | `water` | `#C2C8CA` | 0,5704 |
| Edificios (relleno / contorno) | `building` | `#EAEAE5` / `#DBDBDA` | 0,8200 / 0,7079 |
| Calle menor | `highway_minor` | `#E0E0E0` | 0,7454 |
| Calle mayor (borde / interior) | `highway_major_casing`, `highway_major_inner` | `#D5D5D5` / `#FFFFFF` | 0,6654 / 1,0000 |
| Autovía (borde) | `highway_motorway_casing` | `#D5D5D5` | 0,6654 |
| Límite administrativo | `boundary_2` | `#B2B2B2` | 0,4452 |
| Etiqueta de ciudad y pueblo | `label_city`, `label_town` | `#000000` | 0,0000 |
| Halo de etiqueta | `label_city` | `#FFFFFF` | 1,0000 |
| Etiqueta de calle | `highway-name-major` | `#666666` | 0,1329 |
| Etiqueta de agua | `water_name_point_label` | `#495E91` | 0,1147 |
| Círculo: línea | `circles-line` (`ACCENT` de `MapView.tsx`, grosor 1,5) | `#1647B8` | — |
| Círculo: relleno (12 %) | `circles-fill` | compuesto sobre cada fondo | — |

Con un tinte claro el peor fondo es el negro puro (etiquetas de ciudad y pueblo): la cota que se usa en todas las tablas.

## Archivos y responsabilidades
| Archivo | Crea/Modifica | Responsabilidad | RF |
|---|---|---|---|
| `frontend/src/styles/index.css` | Modifica | Tokens nuevos en `@theme` (cielo del secundario, degradado del principal, tinte y sólido del cristal, radios, sombras), `--panel-height: max(40dvh, 15rem)` definida una sola vez en `:root`, anillo de foco global azul y anillo de tinta de 3 px ampliado a `.maplibregl-map`, `color-scheme: light`, importa los cuatro ficheros nuevos | RF-15, Presentación |
| `frontend/src/styles/buttons.css` | Crea | Clases `btn`, `btn-primary`, `btn-secondary`, `btn-form`: relieve, pulsado, deshabilitado, transiciones, colores forzados, `touch-action: manipulation`. El secundario lee `--btn-secondary-bg` con el cielo `#DFE8FF` por defecto; `.glass` la redefine (T3) | RF-1, RF-9, RF-10, RF-15 |
| `frontend/src/styles/fields.css` | Crea | Clases `field`, `field-box`, `eye`: borde, error, sombra, transición de estado, solo lectura, ojo con su hover, regla `::-ms-reveal` | RF-2, RF-3, RF-10, RF-15 |
| `frontend/src/styles/surfaces.css` | Crea | Clase `glass` con sus variables y los respaldos (sin desenfoque, transparencia reducida, contraste alto, colores forzados) | RF-8, RF-9, RF-10 |
| `frontend/src/styles/notice.css` | Crea | Zona y tarjeta del aviso: anclaje con `--panel-height` y `--free-top`, entrada y salida | RF-6, RF-10 |
| `frontend/src/ui/Indicator.tsx` | Crea | `Indicator` (SVG propio, decorativo, tamaño por clase): lo usan el aviso, el error general y los mensajes de campo | RF-2, RF-4, RF-6 |
| `frontend/src/register/EyeIcons.tsx` | Crea | `EyeIcon` y `EyeOffIcon`, que solo usa el formulario de registro | RF-3 |
| `frontend/public/icon.svg` | Crea | Icono de RentRadar: un solo fichero para la barra y la pestaña | RF-11 a RF-14 |
| `frontend/index.html` | Modifica | `link rel="icon"` al SVG; `theme-color`, `color-scheme` y preconexión a `tiles.openfreemap.org`; la precarga de la fuente es opcional (ver «Afirmaciones no verificadas») | RF-12, Presentación |
| `frontend/src/app/TopBar.tsx` | Modifica | Marca con icono decorativo y nombre (oculto a la vista por debajo de 900 px), `translate="no"`, hover del enlace, botones con las clases nuevas | RF-1, RF-11, Presentación |
| `frontend/src/app/LogoutNotice.tsx` | Modifica | Aviso de cristal con indicador, mensaje, «Reintentar» y «Cerrar aviso»; región de estado siempre montada solo con el mensaje | RF-6, RF-7, RF-8 |
| `frontend/src/map/useFreeZoneTop.ts` | Crea | Mide dónde acaban el zoom y la atribución y lo escribe como `--free-top` en la zona con `style.setProperty` desde una ref, sin estado de React; vive en `map/` porque depende de las clases de MapLibre | RF-6 |
| `frontend/src/app/AppShell.tsx` | Modifica | La zona usa el hook, monta el aviso y le pasa el cierre | RF-6, RF-7 |
| `frontend/src/app/NotFoundPage.tsx` | Modifica | Enlace «Ir al mapa» como botón principal; `text-wrap: balance` en el título | RF-1, Presentación |
| `frontend/src/map/MapView.tsx` | Modifica | «Reintentar» del error del mapa base como botón principal | RF-1 |
| `frontend/src/panel/ResultsPanel.tsx` | Modifica | Panel como superficie de cristal (una sola) con `height: var(--panel-height)` en lugar de `h-[40dvh] min-h-60`, marcado `data-results-panel` para anclar el aviso, botones principales | RF-1, RF-8 |
| `frontend/src/panel/AssetCard.tsx` | Modifica | Las tarjetas no llevan superficie propia (RF-8); espacio de no separación entre «/» y la unidad del precio (Presentación) | RF-8, Presentación |
| `frontend/src/register/RegistrationForm.tsx` | Modifica | Campos con la clase `field`, ojo al final del campo y antes de la ayuda, error general con indicador y texto en tinta, envío en curso en gris, «Crear cuenta» como principal de formulario, `text-wrap: balance` en el título | RF-1 a RF-5, Presentación |
| `frontend/src/session/sessionState.ts` | Modifica | `dismissResult()`: el aviso pasa a ninguno y el foco va a «Salir» | RF-7 |
| `frontend/src/session/SessionProvider.tsx` | Modifica | `dismissNotice` en el contexto: aplica `dismissResult` sin tocar el estado de sesión ni el anuncio | RF-7 |
| `frontend/src/i18n/es.ts` | Modifica | «Cerrar aviso» | RF-6 |
| `frontend/src/i18n/format.ts` | Modifica | Espacio de no separación (U+00A0) entre cifra y unidad en `formatRadius` | Presentación |
| `frontend/src/testing/svgWhitelist.ts` | Crea | Reglas de la lista blanca de la 006 (etiquetas, atributos con la forma de su valor, prohibidos, espacio de nombres) y cuatro comprobaciones que usan los dos tests; solo exporta lo que los tests necesitan | RF-14 |
| `frontend/src/panel/categorySvg.test.ts` | Modifica | Usa el módulo compartido; sus cuatro `it` comprueban lo mismo que antes | RF-14 |
| `frontend/src/brand/icon.test.ts` | Crea | El icono cumple la lista blanca; reglas de capas y colores; 1,5:1 entre la base y la sombra y entre la base y el brillo; 3:1 de la silueta contra blanco | RF-12 a RF-14 |
| `frontend/src/session/sessionState.test.ts` | Modifica | `dismissResult` | RF-7 |
| `frontend/src/app/TopBar.test.ts` | Modifica | Marca (icono decorativo, nombre dentro del enlace, `translate="no"`); las clases de «Registrarse» y «Salir» sustituyen a `min-h-11 min-w-11`. Sus tres tests de `LogoutNotice` se mueven al fichero siguiente | RF-1, RF-11, Presentación |
| `frontend/src/app/LogoutNotice.test.ts` | Crea | Los tests del aviso se rehacen con el diseño nuevo: la región solo contiene el mensaje, la tarjeta está siempre montada con `data-open`, los botones van fuera de la región, «Cerrar aviso» del catálogo | RF-6, RF-7 |
| `frontend/src/register/RegistrationForm.test.ts` | Modifica | El ojo se localiza por su `aria-label`, porque `buttonWith` exige el texto como único contenido del botón; las aserciones de `min-h-11`, `text-danger` y `aria-invalid:border-danger` pasan a las clases nuevas; estado general con indicador; orden campo, ojo, ayuda | RF-2 a RF-5 |
| `frontend/src/panel/ResultsPanel.test.ts` | Modifica | `min-h-11` pasa a la clase de tipo; cambia la cadena esperada del importe y la unidad, que lleva espacio de no separación también tras «/» | RF-1, Presentación |
| `frontend/src/i18n/format.test.ts` | Modifica | Cambia la cadena esperada de `formatRadius` (U+00A0 construido con `String.fromCharCode(160)`) y un caso fija el U+00A0 de `formatPrice` | Presentación |
| `frontend/src/app/indexHtml.test.ts` | Crea | `index.html` leído con `?raw` declara icono, `theme-color`, `color-scheme` y preconexión (y la precarga, si se hace) | RF-12, Presentación |

## Modelo de datos y migraciones
Ninguno.

## Contrato de API
Ninguno. No hay operaciones nuevas ni cambiadas; no hay recursos por identificador, así que no hay casos nuevos de 404 ni de 403.

## Lógica
- `dismissResult(): { notice: null; focus: "logout" }` en `sessionState.ts`, junto a `logoutResult`. No devuelve anuncio: cerrar el aviso no cambia lo que se anuncia ni la sesión.
- `formatRadius` devuelve `"500 m"` y `"1 km"` con U+00A0 entre la cifra y la unidad (Presentación). `formatPrice` no cambia: `Intl.NumberFormat("es-ES")` ya devuelve U+00A0 antes de «€» y un test lo fija.
- `src/testing/svgWhitelist.ts` exporta `TAG`, `ATTRIBUTE` y cuatro funciones que llaman a `expect` (solo etiquetas, atributos con su valor, sin referencias ni scripts, espacio de nombres una sola vez); las listas de etiquetas y atributos no se exportan. Es un movimiento literal de las reglas; no cambia la lista ni lo que comprueba el test de la 006.
- El test del icono distingue las capas por su orden en el dibujo: `fill` del elemento 0 = tono base, 1 = brillo, 2 = sombra. Comprueba al menos tres rellenos distintos, `luminancia(sombra) < luminancia(base) < luminancia(brillo)`, que ninguno es `#F5D547`, 1,5:1 como mínimo entre la base y la sombra y entre la base y el brillo, y 3:1 de la silueta (la base) contra blanco. La luminancia y la razón de contraste son las de WCAG, calculadas en el propio test.

## Interfaz
**Estados y foco.** Ninguno de los estados de carga, vacío, error y éxito de la 006 y la 009 cambia; solo su presentación. El foco sigue las reglas de la 009: tras un fallo de salida, a «Salir»; tras «Cerrar aviso», a «Salir».

**Aviso flotante.**
- La zona del aviso (`absolute`, `z-20`, sin eventos de puntero) está siempre montada en la zona de contenido y ocupa de `--free-top` hasta el borde inferior de la zona libre; la tarjeta (`pointer-events: auto`) se alinea abajo (`justify-content: safe flex-end`). Si es más alta que la zona, se desborda hacia abajo sobre el panel; nunca hacia arriba sobre el zoom.
- `--panel-height` se define una sola vez, en `:root`; el panel la usa como altura por debajo de 900 px (desde 900 px es una columna de 400 px con altura automática) y el aviso lee la misma variable, de modo que la 007 la cambia en un solo sitio. Con panel significa `:has([data-results-panel])` en la zona; con el estilo fallido el panel no se pinta y el aviso baja solo. Los extremos de la zona del aviso en los cuatro casos:
  - menos de 900 px, con panel: `bottom: var(--panel-height)`, `left: 0`;
  - menos de 900 px, sin panel (página sin mapa, «Página no encontrada», registro, error del mapa base): `bottom: 0`, `left: 0`;
  - desde 900 px, con panel: `bottom: 0`, `left: 400px`;
  - desde 900 px, sin panel: `bottom: 0`, `left: 0`.
- `--free-top` lo publica `useFreeZoneTop` (en `map/`) escribiéndolo con `zone.style.setProperty` desde una ref, sin estado de React, para no volver a pintar `AppShell` y `MapPage` en cada cambio de la atribución. Usa un `ResizeObserver` sobre la zona y sobre `.maplibregl-ctrl-top-right`, y un `MutationObserver` de la zona con su subárbol para volver a buscarlo cuando el mapa se crea o se destruye y cuando MapLibre cambia la atribución. Valor: borde inferior de los controles menos borde superior de la zona, más 8 px; 0 si no hay controles.
- **Marcado accesible.** `<div role="status" class="sr-only">` siempre montado con solo el mensaje (vacío cuando no hay aviso): cada fallo se anuncia y el anuncio no incluye «Reintentar» ni «Cerrar aviso». La tarjeta visible está siempre montada y se muestra con `data-open` mientras hay aviso; cerrada es `display: none` sin `!important` (no se usa `hidden`: el preflight de Tailwind lo fija con `!important` e impediría la salida animada). Su párrafo lleva `aria-hidden="true"`, para que el mensaje no se lea dos veces. Los dos botones van fuera de la región. «Deshabilitado» es `aria-disabled`, como en la 009.
- «Reintentar» llama a `logout`, que ya retira el aviso al empezar y lo vuelve a mostrar si falla; «Cerrar aviso» llama a `dismissNotice`.
- Tamaños: «Reintentar» y «Cerrar aviso» de 44 px; indicador de 24 px.

**Panel.** Una sola superficie de cristal; sus tarjetas conservan el filete inferior de hoy y ninguna es translúcida. Los botones del panel son principales. La lista conserva su desplazamiento propio.

**Registro.** El ojo va dentro de la caja del campo, después de la entrada y antes de la ayuda, así que es el siguiente en el orden de tabulación. El campo reserva 52 px a la derecha para el icono. El error general lleva el indicador y el texto en tinta, sin fondo; el envío en curso va sin indicador, sin fondo y en `#424B5A`.

**Marca.** `<a href="/map">` con `<img src="/icon.svg" alt="" width="36" height="36">` y `<span translate="no">RentRadar</span>`. El nombre se oculta a la vista por debajo de 900 px con `sr-only` (sigue siendo el nombre accesible) y se muestra desde 900 px. El enlace mide al menos 44 × 44 px.

**Foco no recortado.** El anillo azul se dibuja con `outline` (fuera del control, por encima de su sombra). Ningún contenedor con `overflow` oculto o con desplazamiento lo recorta: los controles de esta spec están a 16 px o más de los bordes de sus contenedores con desplazamiento (el panel y el `main` del registro), por encima de los 4 px que ocupa el anillo con su separación. Una regla para las specs siguientes: un control dentro de un contenedor con `overflow` necesita al menos 4 px de margen.

## Decisiones
| Decisión | Opciones | Elegida | Qué evita | Coste |
|---|---|---|---|---|
| D1. Dónde viven los estilos de las piezas | Cadenas de utilidades en cada TSX; clases de componente en CSS; componentes React `<Button>` | Clases de componente en CSS (`@layer components`), por pieza | Repetir 12 líneas de sombras en los nueve botones, y un componente que no vale para `<a>` y `<button>` a la vez | Cuatro ficheros CSS nuevos; los tests que afirmaban `min-h-11` pasan a afirmar la clase y la medida de 44 px queda solo en CSS, comprobada en el navegador |
| D2. Respaldo sólido | Cuatro bloques que repiten cada declaración; cuatro variables que cambian en cada condición | Cuatro variables (`--glass-bg`, `--glass-blur`, `--glass-btn-bg`, `--glass-btn-bg-hover`) que cambian bajo `@supports not`, transparencia reducida y contraste alto; colores forzados aparte | Que un respaldo se quede atrás cuando cambie la superficie, y poder verificarlo por el valor de las variables | Una indirección más |
| D3. Desenfoque propio del secundario | Con desenfoque de 12 px (como dice la spec); sin él | Sin `backdrop-filter` propio, solo translucidez (la definición de «secundario» de la spec ya no habla de desenfoque) | Un cristal anidado ve solo el fondo de su cristal, no el mapa: el desenfoque no aporta nada y añade una pasada de composición por botón | Ninguno |
| D4. Región de estado del aviso | `role="status"` en el párrafo visible; región oculta a la vista siempre montada con el párrafo visible en `aria-hidden` | La segunda | Que el aviso se anuncie al aparecer ya con texto (no se anuncia de forma fiable) o al salir de `display: none` | El texto está dos veces en el DOM; se comprueba en el árbol de accesibilidad |
| D5. Dónde empieza la zona libre | Constante en CSS; medirlo con JS | JS: observadores, valor escrito con `setProperty` desde una ref, hook en `map/` | Que la atribución desplegada, que cambia de altura con el ancho, tape el aviso o al revés, y volver a pintar la página en cada cambio | Un hook de unas 25 líneas que solo se prueba en el navegador |
| D6. Panel que tapa el zoom a 667 × 375 | A) dejarlo como está, registrarlo y que lo resuelva la 007; B) limitar la altura del panel en apaisado bajo; C) pasar el panel a columna en apaisado | **A.** El panel (`z-10`) ya cubre la parte baja del zoom a 667 × 375 desde la 006; el aviso queda por debajo de los controles y no se cruza con ellos | Cambiar la geometría del panel en una spec que solo cambia su presentación, justo antes de que la 007 la rehaga (plegado, medio y desplegado) | Queda un defecto heredado: el «−» del zoom queda tapado y su foco no se ve en apaisado bajo. Se anota en MEMORY.md (línea de la 007, que va justo después de la 016) |
| D7. Anillo de foco | Cambiar solo los controles de la spec; cambiar el global y dejar el subárbol de MapLibre con el suyo | Global azul; `.maplibregl-map :focus-visible` conserva el de la 006 | Que el azul se confunda con la línea azul de los círculos y que los enlaces de la atribución cambien de anillo | El `outline-none!` de la zona de contenido sigue siendo necesario |
| D8. Icono | Un SVG en `src/assets` importado con `?no-inline` y otro en `public` para la pestaña; uno solo en `public/` | Uno solo, `frontend/public/icon.svg`, referenciado como `/icon.svg` | Dos copias que se separan; que el SVG pequeño salga como `data:` (la 006 cierra `img-src` a `'self'`) | El test lo lee con `?raw` desde `public/` |
| D9. Reglas de la lista blanca | Copiarlas al test del icono; módulo común | Módulo `src/testing/svgWhitelist.ts` | Que el test del icono copie las reglas, como la spec prohíbe, y que las dos listas se separen | Un movimiento de código en el test de la 006 |
| D10. Cierre del aviso | Estado local en `LogoutNotice`; función pura y acción del contexto | `dismissResult` + `dismissNotice` | Que el cierre viva fuera de la sesión y el foco no llegue a «Salir» | Dos líneas más en el contexto |
| D11. `color-scheme` | Dejarlo; declarar `light` | `light` en `index.html` y en CSS | Que el navegador pinte controles y barras de desplazamiento oscuros bajo un tema de sistema oscuro sin modo oscuro | Ninguno |
| D12. «Cerrar aviso» | Texto; texto con icono de cierre | Solo texto, como en la variante aprobada | Un icono más sin función distinta | Si el usuario quiere una × se añade en la tarea del aviso |

## Resolución de las notas para el plan
**Secundario y foco.** Relleno, borde y sombra: valores de Botones. El anillo es un `outline` de 2 px con `outline-offset` de 2 px, que se dibuja fuera del control y por encima de su sombra, y no lo recorta un contenedor mientras haya 4 px de margen (ver Foco no recortado). Los controles de MapLibre de la 006 (zoom, enlaces de la atribución y lienzo) se quedan con su anillo de tinta de 3 px: el azul no se distinguiría de la línea de los círculos (D7).

**Medición de rendimiento.**
- *Compilaciones.* Antes de empezar la T1, desde la rama tal como está: `npm run build` y copia de `dist/` a `~/rentradar-perf/a`, fuera del repositorio. Tras la última tarea, lo mismo a `~/rentradar-perf/b`. Se sirven a la vez con `npx vite preview --outDir <ruta> --port 4173 --strictPort` (A) y `--port 4174` (B), lanzados desde `frontend/` para heredar el proxy de `/api` al backend; los dos usan los mismos bienes de demostración. Hace falta el stack levantado, con la autorización del desarrollador en ese momento.
- *Sesión.* Una pestaña nueva de Chrome por traza, con emulación `375x812x1,mobile,touch` y CPU 4× aplicada y comprobada: un bucle fijo debe tardar unas 4 veces más que sin limitar (49 ms sin limitar y 189 ms con 4× en la prueba), y el ancho de 375 px se comprueba al cargar la app, porque `about:blank` mide 981 px. Antes de cada traza, `list_pages` debe mostrar una sola pestaña de localhost y `TracingStartedInBrowser` no debe listar la otra compilación: así la página anterior no queda congelada en el historial del mismo proceso. La última pestaña no se puede cerrar: se abre la siguiente en blanco, se cierra la anterior y solo entonces se carga la compilación.
- *Gesto.* Un script con `evaluate_script` que envía al lienzo del mapa un `mousedown` en el centro, un `mousemove` por fotograma durante 5 s siguiendo `x = cx + 100·sen(2π·t/2,5 s)`, `y = cy + 60·sen(2π·t/1,25 s)`, un último `mousemove` forzado al origen exacto y un `mouseup`. Los eventos llevan `bubbles: true` y los de pulsación `buttons: 1` (`buttons: 0` en el `mouseup`): sin ellos MapLibre no arrastra. Entre el último `mousemove` y el `mouseup` hay una pausa de 250 ms en el origen, porque MapLibre descarta del búfer de inercia lo anterior a 160 ms y sin la pausa el mapa se desliza al soltar. El script deja las marcas `gesto-inicio` (antes del `mousedown`) y `gesto-fin` (justo después del último `mousemove`, antes de la pausa) con `performance.mark` y `console.timeStamp`. El mapa vuelve al punto de partida y todas las pasadas ven las mismas teselas.
- *Carga y gesto previo.* En cada carga se hace un gesto previo sin traza, con el mismo script. Después se espera a que termine la petición de la lista pública que sale al soltar y se dejan 2 s de calma antes de empezar la traza, para que la ventana no contenga red de teselas.
- *Calentamiento.* Una pasada de cada compilación, descartada, con una variante del gesto que lee el mapa por el árbol de React (solo ahí: en las trazas que cuentan no se llama a `getCenter` ni a `project`). A t = 0,625 s el punto inicial debe haberse desplazado unos 100 px en x (±5 px) y 1 s después del `mouseup` debe estar a ±5 px de la posición inicial; si no, se para.
- *Traza.* `performance_start_trace` con `reload: false` y `autoStop: false` y `filePath`; se lanza el gesto; `performance_stop_trace`. Un script `python3 -I` cuenta, entre las dos marcas, los eventos `PipelineReporter`. La unidad es el fotograma, con la clave (pid del renderizador, `layer_tree_host_id`, `frame_source`, `frame_sequence`) de `args.frame_reporter`. Un fotograma con `PRESENTED_ALL` cuenta como presentado; los que solo tienen `NO_UPDATE_DESIRED` no se cuentan. Fotogramas por segundo = fotogramas con `PRESENTED_ALL` ÷ D, con D el tiempo entre las marcas; perdidos (%) = fotogramas sin `PRESENTED_ALL` ÷ fotogramas contados. Se cuenta por fotograma y no por informe porque casi cada fotograma tiene dos (un `PRESENTED_PARTIAL` de un vsync y el `PRESENTED_ALL` un vsync después) y contar informes inventaría perdidos. Como contraste, el propio script del gesto cuenta los `requestAnimationFrame` y los intervalos de más de 25 ms.
- *Informativos* (sin umbral): porcentaje de fotogramas en pareja (`PRESENTED_ALL` más `PRESENTED_PARTIAL`; en el calentamiento A estuvo en pareja toda la ventana y B solo la mitad, así que no mide el coste del cristal); tiempo del hilo principal, del compositor y de la GPU (tareas `GPUTask` filtradas por el `renderer_pid` de la pestaña); desglose del hilo principal por tipo de tarea; perfil de CPU (`ProfileChunk`); y recuento de `MinorGC`, `MajorGC` y marcado en segundo plano. La GPU es la integrada del portátil y el 4× solo frena la CPU.
- *Límite de la traza.* Las categorías de traza que fija el MCP no recogen el dibujo del compositor de pantalla: el proceso de GPU solo trae `RunTask` y `GPUTask`, sin eventos de viz ni de Skia. El coste del desenfoque solo se ve de forma indirecta, en el tiempo de `VizCompositorThread` y de `CrGpuMain`.
- *Tráfico.* En cada pasada, `list_network_requests` con las teselas y el estilo descargados: después de la petición de la lista del gesto previo no debe haber teselas, y si una versión descarga teselas que la otra tuvo en caché, se repite la pasada.
- *Orden.* Calentamiento de A y de B (descartados) y A, B, A, B, A, B. Mediana de las tres pasadas de cada una; veredicto según el umbral de la spec.
- *Scripts.* Los scripts están en `~/rentradar-perf/tools` hasta el cierre de la 016; al cierre se decide si se versionan en `specs/016-visual-system/medicion/`.
- *Ruido observado en la prueba.* Con dos trazas por versión, la diferencia entre las dos de la misma versión fue del 5 % al 7 % en el hilo principal y de hasta el 11 % en la GPU: del orden de la diferencia entre versiones de la prueba (ver `validation.md`).
- *Propuestas para un `/sdd-change`.* Se hará una sola vez, después de la T5 y antes de la medición oficial, con estos puntos:
  - Orden cruzado A, B, B, A, A, B en lugar de A, B, A, B, A, B.
  - Dispositivo de la medición oficial: pendiente de decidir.
  - Escena con panel y aviso: entra en la medición oficial si el aviso puede seguir abierto mientras se arrastra el mapa.
  - Qué hacer con la métrica saturada, que en el portátil de la prueba no distingue A de B.
- *Palancas si no aprueba* (se acuerdan con el usuario, sin bajar del 80 % de opacidad): desenfoque de 22 a 14 px; quitar la sombra interior del cristal; quitar el desenfoque del aviso y dejarlo solo en el panel.

**Respaldo.**
- *Movimiento reducido, contraste alto y colores forzados*: `emulate` con `prefersReducedMotion: "reduce"`, `prefersContrast: "more"` y `forcedColors: "active"`; se comprueba el estilo calculado de las superficies, los botones y los campos.
- *Transparencia reducida*: `emulate` no la admite. Se localiza en `document.styleSheets` la regla `@media (prefers-reduced-transparency: reduce)`, se leen las variables que fija y se aplican esas mismas a `:root`; el estilo calculado del panel y del aviso debe ser el color sólido y `backdrop-filter: none`.
- *Sin desenfoque*: el mismo procedimiento con la regla `@supports not (…)`; el navegador de la verificación sí admite el desenfoque, así que lo que se comprueba es que la rama de respaldo produce la superficie sólida. Se anota que no se ha visto en un navegador sin soporte.
- *Límite de estas dos comprobaciones*: prueban que las variables mueven las superficies, no que el `@media` o el `@supports` estén bien escritos; un error en el nombre de la condición pasaría inadvertido. La transparencia reducida y la falta de desenfoque se anotan en `validation.md` como comprobadas por sus variables.
- *Botón propio de Edge*: se comprueba que existe la regla `::-ms-reveal { display: none }` en la hoja; Chrome no lo muestra.

**Colores de «positron».** Salen de la tabla de Valores, extraída de la descarga del estilo. En la validación se vuelve a descargar con `curl` y se comparan los valores con un script `python3 -I`; si difieren, se vuelven a medir los pares. Es el riesgo aceptado de la spec: nada lo detecta fuera de esa comprobación.

**Reglas compartidas de la lista blanca.** Módulo `src/testing/svgWhitelist.ts` (D9). Lo importan `categorySvg.test.ts` y `brand/icon.test.ts`; el primero conserva sus nombres de `it`.

**Panel que tapa el zoom a 667 × 375.** D6: se deja, se registra y el aviso se ancla bajo los controles.

**Marcado accesible.** D4 y la sección Interfaz.

**Icono, carpeta.** `frontend/public/icon.svg`: fuera de `assets/categories`, que el test de la 006 recorre entero y comprueba contra las 11 de la semilla.

**Icono, test de capas.** Por orden de dibujo (Lógica).

**Icono, pestaña.** Fichero propio del sitio en `public/`, referenciado con `<link rel="icon" href="/icon.svg" type="image/svg+xml">`.

**Icono, pestaña en dos temas.** Las capturas de página no incluyen la barra de pestañas. La captura de la pestaña es el icono real (`/icon.svg`, la misma URL que usa la pestaña) dibujado en un lienzo de 16 × 16 px sobre blanco y sobre el gris oscuro, con `emulate colorScheme` claro y oscuro para el entorno, y ampliado con `image-rendering: pixelated`; los contrastes se leen de los píxeles. El gris real de las pestañas se toma de la versión de Chrome de la verificación (`chrome://version`) y de una captura de pantalla del sistema con la ventana en tema oscuro, si el entorno la permite; si no, se registran `#202124` y `#35363A` como valores supuestos.

**Tests sin entorno de navegador.** El ojo, el foco, la persistencia del aviso y el tamaño de los controles van al navegador; en vitest, el marcado con `renderToStaticMarkup` y las funciones puras.

**Tope de tareas.** Ocho (ver «Reparto previsto»).

## Hallazgos de web-design-guidelines asignados a la 016
Las guías piden Title Case en títulos y botones: no se aplica en español.

Las mejoras están recogidas en el punto «Presentación» de los requisitos no funcionales de la spec. No tienen RF propio ni cuelgan de RF-8.

| Hallazgo | Dónde se resuelve | Verificación |
|---|---|---|
| Contenedor de estado siempre montado con el mensaje dentro | `LogoutNotice` (D4) | vitest: la región solo contiene el mensaje; árbol de accesibilidad en el navegador |
| Espacio de no separación entre cifra y unidad | `formatRadius` (`500 m`, `1 km`), `AssetCard` (`/` y unidad) y un caso que fija el de `formatPrice` | vitest: `format.test.ts` y `ResultsPanel.test.ts` con la cadena esperada nueva |
| `theme-color`, `color-scheme` y preconexión a `tiles.openfreemap.org` (la precarga de la fuente es opcional, fuera de la spec) | `index.html` y `index.css` (D11) | vitest: `indexHtml.test.ts`; etiquetas de la cabecera en el navegador |
| `touch-action: manipulation` en botones y ojo | `buttons.css`, `fields.css` | Navegador: estilo calculado |
| `translate="no"` en el nombre de la marca | `TopBar.tsx` | vitest: marcado de la marca |
| `text-wrap: balance` en los títulos | `h1` del registro y de «Página no encontrada» | Navegador: estilo calculado |
| Hover del ojo y del enlace de la marca | `fields.css`, `TopBar.tsx` | Navegador: estilo calculado con el puntero encima |

Van a la 008 (`h1` oculto de la pantalla del mapa y título del panel como `h2`) y no se arreglan los que solo afectan al prototipo.

## Blast radius
- Cambian las clases de todos los botones (barra, panel, aviso, registro, error del mapa base, «Página no encontrada»), de los campos, del panel y del aviso. Ningún comportamiento cambia.
- Tests que se reescriben o cambian, por fichero: `TopBar.test.ts` (los tres tests de `LogoutNotice` afirman hoy lo contrario del diseño nuevo, con la región `absolute inset-x-0 top-0` y el botón dentro de ella, y se rehacen en `LogoutNotice.test.ts`; las clases `min-h-11 min-w-11` de «Registrarse» y «Salir» pasan a la clase de tipo), `RegistrationForm.test.ts` (`buttonWith` exige el texto como único contenido del botón y el ojo lleva un SVG, así que se localiza por su `aria-label`; `min-h-11`, `text-danger` y `aria-invalid:border-danger`), `ResultsPanel.test.ts` (`min-h-11` de los botones).
- Dos tests de la 006 cambian de cadena esperada por Presentación, sin cambiar lo que comprueban: `format.test.ts` (`500 m` y `1 km` con U+00A0) y `ResultsPanel.test.ts` (el importe y la unidad, con U+00A0 también tras «/»).
- `categorySvg.test.ts` cambia de sitio las reglas: debe seguir dando los mismos resultados con las 11 imágenes.
- `index.css` pierde el anillo de tinta global; el subárbol de MapLibre lo conserva por `.maplibregl-map :focus-visible`.
- `ResultsPanel` deja de fijar su altura con `h-[40dvh] min-h-60` y usa `--panel-height`, con el mismo valor.
- `LogoutNotice` deja de ser una región `absolute inset-x-0 top-0` y pasa a una zona con su ancla: la posición del aviso cambia en todas las páginas.
- `sessionState.ts` y `SessionProvider.tsx` ganan una acción; el contrato del contexto crece, ninguna otra pieza lo rompe.

## Riesgos
| Riesgo | Mitigación |
|---|---|
| El cristal a 22 px de desenfoque no pasa la prueba de rendimiento a 375 px con CPU 4× | Palancas acordadas con el usuario (Medición); el secundario no añade desenfoque (D3) |
| El estilo «positron» cambia sus colores y caduca el contraste medido | Riesgo aceptado en la spec; se vuelve a comparar en la validación |
| `.maplibregl-ctrl-top-right` cambia de nombre en otra versión de MapLibre | Solo se usa para medir; sin él `--free-top` es 0 y el aviso no cruza el zoom salvo en alturas bajas. La versión está fijada en 6.14.0 |
| La salida animada con `display` discreto no funciona en algún navegador | Sin ella el aviso desaparece de golpe (el movimiento reducido ya lo hace); no rompe nada |
| El zoom queda tapado por el panel a 667 × 375 (heredado) | D6; línea de la 007 en MEMORY.md |
| La altura del panel cambiará con la 007 | El aviso se ancla a `--panel-height`; la 007 tendrá que actualizarla |
| El texto del aviso está dos veces en el DOM (D4) | Se comprueba en el árbol de accesibilidad que solo se expone una |
| Los enlaces de la atribución cambian de anillo al cambiar el global | `.maplibregl-map :focus-visible` conserva el de la 006; se comprueba tabulando hasta un enlace de la atribución |

## Estrategia de tests
| RF | Cómo se verifica |
|---|---|
| RF-1 | Chrome DevTools: estilo calculado de `box-shadow` en reposo, pulsado (Espacio mantenido, o la regla `:active` leída de la hoja si la herramienta no mantiene la tecla) y deshabilitado («Crear cuenta» enviando, «Salir» saliendo); sin cambio al pasar el puntero sobre el deshabilitado. vitest: cada botón lleva su clase de tipo |
| RF-2 | vitest: etiqueta asociada, `aria-invalid` y `aria-describedby` en el marcado. Navegador: etiqueta fija al enfocar y escribir, y borde `#B3261E` con error |
| RF-3 | vitest: nombre «Mostrar contraseña» fijo y `aria-pressed` en los dos estados. vitest: el icono abierto o tachado (el trazo `M3 3l18 18` solo con la contraseña visible) y el orden entrada, ojo, ayuda con `indexOf`. Navegador: alternancia, valor conservado, foco sin moverse, también con el campo en solo lectura |
| RF-4, RF-5 | vitest: el error general lleva el indicador y no lleva clase de fondo; el envío no lleva indicador. Navegador: colores calculados |
| RF-6 | Navegador: límites de la tarjeta, del zoom, de la atribución, de la barra y del panel a 375, 1280, 667 × 375 y con el texto al 200 %; ventana cruzando 900 px; página sin mapa y error del mapa base; `pointer-events` calculado de la zona (`none`) y de la tarjeta (`auto`), para que fuera de la tarjeta el arrastre llegue al mapa |
| RF-7 | vitest: `dismissResult` (notice nula, foco en «Salir») y que no devuelve anuncio. Navegador: el aviso sigue a los 60 s y tras navegar, «Cerrar aviso» devuelve el foco a «Salir», un nuevo fallo lo vuelve a mostrar |
| RF-8 | Navegador: el panel y el aviso con `backdrop-filter` y tinte al 88 %, las tarjetas sin fondo propio, la barra y la tarjeta del registro opacas |
| RF-9 | Navegador: contraste alto emulado; transparencia reducida y falta de desenfoque por el procedimiento de Respaldo |
| RF-10 | Navegador: `transition-duration` de botones, campos y aviso mayor que 0 con movimiento normal e igual a 0 con `prefersReducedMotion: "reduce"` |
| RF-11 | vitest: la marca contiene la imagen con `alt=""` y el nombre «RentRadar»; el enlace tiene la clase de 44 px. Navegador a 375 px: el nombre no se ve, el nombre accesible es «RentRadar» y el enlace mide al menos 44 × 44 px |
| RF-12 | Navegador: `link rel="icon"` apuntando a `/icon.svg`; capturas del icono a 16 px sobre blanco y sobre el gris oscuro, con 1,5:1 entre capas y 3:1 de silueta. vitest: `indexHtml.test.ts` fija el `link rel="icon"` |
| RF-13 | vitest (`icon.test.ts`): al menos tres rellenos distintos, sombra más oscura y brillo más claro que la base, sin limón, 1,5:1 entre capas y 3:1 de silueta contra blanco |
| RF-14 | vitest (`icon.test.ts` con el módulo compartido): etiquetas, atributos, colores de seis cifras y transformaciones permitidas. Un SVG de prueba con degradado, escala, color de tres cifras y `<g>` debe fallar |
| RF-15 | Navegador: `outline` de 2 px `#1647B8` con separación de 2 px en el principal, el secundario, el campo, el ojo y el enlace de la marca; contraste contra página, cristal y blanco; el anillo no queda oculto por la sombra; tabulando hasta un enlace de la atribución, el `outline` sigue siendo el de tinta de 3 px de la 006 |
| Contraste | Tabla de Valores recalculada con los colores finales en `validation.md`; panel sobre la línea de un círculo y sobre una etiqueta oscura |
| Accesibilidad y móvil | Medidas de 44 × 44 px, orden de tabulación (ojo tras el campo), sin desbordamiento a 375 px, colores forzados, recorrido solo con teclado, consola sin errores |
| Rendimiento | Procedimiento de Medición, registrado en `validation.md` |
| Idioma | vitest: «Cerrar aviso» sale del catálogo |
| Comportamiento conservado | La suite de la 006 y la 009 en verde, con la lista cerrada de tests cuyo selector o cadena cambian (Blast radius). vitest: la región `role="status"` contiene solo el mensaje y ningún botón. Navegador: el reintento retira el aviso al empezar y lo vuelve a mostrar si falla, el foco va a «Salir» tras el fallo y tras cerrar, y el reintento ante `csrf_failed` sigue funcionando |
| Identidad visual y dependencias | `git diff` de `package.json` y `package-lock.json` vacío; ningún uso de `bg-lemon` ni de `--color-lemon` en `src/` fuera de la definición del token |
| Colores forzados | Navegador con `forcedColors: "active"`: `outline-style`, `border` y `color` calculados en botones (también el secundario), campo, ojo y superficies de cristal; el anillo y el ojo con colores del sistema |
| Presentación | Tabla de «Hallazgos de web-design-guidelines asignados a la 016»: vitest para la distancia, el precio, la marca y `index.html`; navegador para la cabecera y los estilos calculados |

## Reparto previsto en tareas
Sin escribir todavía `tasks.md`; 8 tareas, por debajo del tope de 10, en orden lineal de dependencia (T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8):
1. Botones y anillo de foco (incluida la ampliación del anillo de tinta a `.maplibregl-map`), aplicados a la barra, el panel, el error del mapa base y «Página no encontrada». El secundario sale con el cielo por defecto. Incluye la comprobación de la ruta estable de la fuente para la precarga opcional.
2. Campos, ojo e indicador en el registro, con su estado general y el de envío.
3. Superficies de cristal con sus respaldos, `--panel-height` y el panel; `.glass` redefine el relleno del secundario.
4. «Cerrar aviso»: `dismissResult`, `dismissNotice`, la cadena del catálogo y el botón, con su test, sobre la posición actual del aviso.
5. Anclaje y región de estado del aviso: `notice.css`, `useFreeZoneTop`, `AppShell`, el marcado accesible y los tests rehechos.
6. Módulo compartido de la lista blanca, icono y test del icono.
7. Marca en la barra e icono de la pestaña.
8. Pulido: `index.html` (resto de etiquetas), espacio de no separación con los dos tests de la 006, y `text-wrap`.

La compilación A de la medición de rendimiento se hace antes de la tarea 1; no es una tarea porque no genera un commit. Después de la tarea 8 viene el cierre que exige la spec, que tampoco es una tarea de código: `/sdd-validate` con la medición B, `validation.md`, MEMORY.md y las notas de la 015.

## Afirmaciones no verificadas
Comprobadas al redactar: `Intl.NumberFormat("es-ES")` devuelve U+00A0 antes de «€»; el zoom y la atribución van arriba a la derecha, con la atribución encima, según `MapView.tsx`; el preflight de Tailwind fija `[hidden]` con `display: none !important`; `emulate` admite `prefersContrast` y `forcedColors` (esquema de la herramienta); `vite preview` admite `--outDir` y su `preview.proxy` hereda `server.proxy` (documentación). Comprobadas en la medición de prueba del 2026-11-10: `PipelineReporter` aparece en la traza que guarda `performance_stop_trace` con sus estados de presentación; `vite preview --outDir` acepta una ruta fuera de la raíz del proyecto; y los eventos de ratón sintéticos arrastran el mapa de MapLibre con la emulación táctil activa si llevan `buttons: 1` y `bubbles: true`.

Pendientes de comprobar:
- Que `:active` se activa con Espacio mantenido en este entorno y que `press_key` permite mantenerlo.
- Que `transition-behavior: allow-discrete` con `@starting-style` anima la salida del aviso en la versión de Chrome de la verificación, y que `justify-content: safe flex-end` se admite en los navegadores de destino.
- Que Tailwind 4.3.3 aplica `@layer components` en ficheros importados desde `index.css` y que `:has()` va bien en sus selectores. Se consulta con Context7 antes de la tarea 1.
- Precarga de la fuente (mejora opcional, no está en la spec): se hace solo si en la T1 se comprueba, con un `npm run build`, que la ruta del fichero de la fuente en `dist` es estable y coincide con la que genera el CSS, y se aplica en la T8. Si no hay ruta estable, no se hace y se anota en `validation.md`.
- Que `#202124` y `#35363A` son los grises de las pestañas de Chrome en tema oscuro; se miden en la validación.
- Que vitest puede importar con `?raw` el icono desde `public/` y `index.html`; se prueba en las tareas 6 y 8.
- Que un `MutationObserver` con subárbol en la zona basta para seguir los cambios de la atribución de MapLibre sin coste apreciable al arrastrar; se mide en el navegador.

## Skills que aplican
`sdd`, `frontend-design` (valores de la variante B y sistema de piezas) y `web-design-guidelines` (hallazgos asignados). El backend no se toca, así que `django-drf` no aplica.
