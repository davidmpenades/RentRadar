# Spec 016 — Sistema visual
Estado: aprobada
Depende de: spec 006 (identidad visual, mapa base, panel de resultados, atribución, movimiento reducido y lista blanca de SVG de las imágenes de categoría) y spec 009 (barra superior, formulario de registro, «Mostrar contraseña» y aviso de fallo de salida, RF-9 a RF-13).

## Contexto y objetivo
Cada pantalla de RentRadar resuelve hoy su aspecto por su cuenta: los botones son planos, «Mostrar contraseña» es un botón de texto bajo el campo, el panel es una caja opaca y el aviso de fallo de salida se superpone arriba de la zona de contenido con el limón que la 006 reserva para la selección de la 007, tapando el zoom y la atribución del mapa, que la 006 exige visible en todo momento. La entrada (spec 015) y las specs siguientes necesitan las mismas piezas.

Esta spec fija un sistema visual común y lo aplica a lo que ya existe, para poder verificarlo en el navegador:
- botones con relieve y sombra;
- campos de formulario con etiqueta fija y, en la contraseña, un control con icono de ojo al final del campo;
- un aviso flotante persistente que sustituye al aviso de fallo de salida;
- superficies de cristal para lo que flota sobre el mapa, con respaldo sólido;
- el icono de RentRadar, dibujado con estilo de ilustración y dentro de la lista blanca de SVG de la 006, en la barra superior (junto al nombre desde 900 px y solo por debajo) y en la pestaña del navegador.

Se aplica a la barra superior, al panel de resultados, al aviso de fallo de salida, al formulario de registro, al error del mapa base y a «Página no encontrada». Ningún comportamiento de la 006 ni de la 009 cambia: solo la presentación, la posición del aviso y la posibilidad de cerrarlo.

El estilo de referencia es un cristal translúcido sobre el mapa, como inspiración y no como copia. Cuatro condiciones son obligatorias: contraste AA medido contra el peor fondo del mapa, superficie sólida si el navegador no admite desenfocar lo que hay detrás, transiciones desactivadas con movimiento reducido y rendimiento medido arrastrando el mapa a 375 px con la CPU ralentizada.

Antes del plan se preparan dos o tres variantes visuales en `prototypes/016-visual-system/` y el usuario elige una. Cada variante incluye una imagen de categoría con el estilo de ilustración, como referencia para la spec 008. La variante elegida y sus valores (tinte, opacidad, desenfoque, sombras, radios, colores nuevos e icono) se registran en el plan, no en esta spec. La 016 se implementa antes que la 015.

## Usuarios
- **Visitante** y **usuario** (los de la 009): ven la interfaz nueva; lo que pueden hacer no cambia, salvo cerrar el aviso de fallo de salida.
- **Desarrollador del equipo**: reutiliza las piezas en la 015 y siguientes, usa la imagen de referencia en la 008 y mide el contraste y el rendimiento.

## Historias de usuario
- HU-1. Como visitante, quiero que los botones y los campos se reconozcan como tales y respondan al pulsarlos, para saber qué puedo hacer y que mi acción se ha registrado.
- HU-2. Como visitante que escribe una contraseña, quiero verla con un control dentro del propio campo, para comprobarla sin perder de vista el formulario.
- HU-3. Como usuario cuya salida ha fallado, quiero un aviso que no tape los controles del mapa ni la barra, que no desaparezca antes de que pueda reintentar y que pueda cerrar, para resolverlo cuando quiera.
- HU-4. Como visitante que explora el mapa, quiero que el panel deje intuir el mapa que hay detrás sin perder legibilidad ni fluidez al moverlo, con una superficie sólida si mi navegador no puede desenfocar, y respetando mis preferencias de movimiento, transparencia y contraste.
- HU-5. Como visitante, quiero reconocer RentRadar por su icono en la barra y en la pestaña del navegador.

## Definiciones
- **Botón**: control que ejecuta una acción, o enlace con forma de botón. Hay dos tipos:
  - **principal** (fondo azul y texto blanco): «Registrarse», «Crear cuenta», «Reintentar» del aviso, «Reintentar» y «Volver a la zona inicial» del panel, «Reintentar» del error del mapa base y el enlace «Ir al mapa» de «Página no encontrada»;
  - **secundario** (cristal claro): «Salir» y «Cerrar aviso». Sobre el mapa o sobre una superficie de cristal, relleno translúcido con desenfoque y borde claro de 1 px. Sobre una superficie blanca (la barra superior y la tarjeta del formulario de registro), su relleno lleva un tinte cielo suave que lo separa del fondo, con el mismo borde claro y la misma sombra. El color, la opacidad, el tono exacto del tinte y la sombra los fija el plan. Lo identifica su texto, no el contraste de su borde.

  El control del ojo no es un botón con relieve: es un control del campo.
- **Relieve**: sombra que proyecta un botón en reposo y lo separa del fondo. Al pulsarlo (con puntero o con teclado), la sombra se reduce: su desplazamiento o su desenfoque son menores que en reposo. Se verifica por el estilo calculado en el navegador. Los valores los fija la variante elegida.
- **Deshabilitado**: control marcado como deshabilitado de forma accesible, como «Crear cuenta» durante el envío y «Salir» durante la salida en la 009. Sigue en el orden de tabulación y anuncia que está deshabilitado. No tiene relieve, pulsarlo no tiene efecto y no responde al pasar el puntero.
- **Campo**: entrada de texto con una etiqueta visible fija encima, que no está dentro del campo ni hace de marcador de posición, con borde, estado de error y foco visible.
- **Indicador**: icono de error dibujado en el color de error, junto al texto, para que el error no se distinga solo por el color.
- **Anillo de foco**: contorno continuo de 2 px en el azul #1647B8, separado 2 px del control y dibujado fuera de él, para que su sombra y su relleno no lo oculten. Es el mismo en los botones, los campos, el ojo y los enlaces de esta spec. Se mide contra los tres fondos sobre los que puede quedar: la página, el cristal sobre su peor fondo y el blanco (Contraste). No se usa sobre el mapa sin superficie, donde la línea azul de los círculos lo anularía.
- **Aviso flotante**: mensaje breve que flota sobre la zona de contenido sin desplazarla, con una acción y un botón «Cerrar aviso». En esta spec solo existe uno, el fallo de salida de la 009 (RF-12), y su acción es «Reintentar». No hay avisos sin acción ni avisos que se cierren solos.
- **Superficie de cristal**: superficie translúcida que deja ver, desenfocado, lo que hay detrás. Su tinte tiene una opacidad de al menos el 80 % (Valores). El color del tinte, el desenfoque, el borde y la sombra los fija la variante elegida.
- **Superficie sólida**: la misma superficie, opaca, con el color base de la variante y la misma forma, borde y sombra.
- **Zona libre del mapa**: la parte de la zona de contenido que no ocupan el panel ni los controles del mapa (zoom y atribución).
- **Color de error**: el rojo #B3261E, que ya usa la interfaz desde la 009 sin que ninguna spec lo recogiera. Esta spec lo recoge en la paleta del sistema y lo reutiliza; no es un color nuevo.
- **Transición de estado**: el cambio animado entre dos estados de una pieza (relieve de un botón, aparición y salida del aviso, estado de un campo). Con movimiento normal dura un tiempo corto que fija el plan; con movimiento reducido no existe (RF-10).
- **Estilo de ilustración**: dibujo de formas simples con capas de color planas (al menos un tono base, una sombra dura y un brillo), sin degradados, filtros ni desenfoques. La sombra dura es una forma en un tono más oscuro, desplazada respecto a la forma base. El brillo es una forma en un tono más claro, opaca o con opacidad uniforme.
- **Silueta del icono**: el contorno exterior del icono, formado por las capas que tocan el borde del dibujo. Su contraste se mide con el color de cada una de esas capas contra el fondo.
- **Lista blanca de SVG de la 006**: la que fija la 006 para las imágenes de categoría: las etiquetas, los atributos con la forma exacta de su valor, los colores de seis cifras y las transformaciones (giro y desplazamiento) que admite. Esta spec la cumple en el icono, no la copia y no la cambia.
- **Imagen de categoría de referencia**: imagen de una sola categoría dibujada con el estilo de ilustración en los prototipos. Sirve de referencia a la 008 y no entra en la aplicación.
- **Fondos de referencia del mapa**: los colores que pueden quedar detrás de una superficie de cristal a cualquier zoom:
  - los del mapa base: fondo, agua, parques, calles, edificios y textos de las etiquetas con su halo;
  - como cota de las etiquetas, el negro puro;
  - los de los círculos: el relleno compuesto sobre esos colores y la línea azul #1647B8.

  El plan extrae los valores del estilo «positron» vigente. El **peor fondo** de un elemento es el fondo de referencia que le da el contraste más bajo.
- **Contraste medido**: la razón de contraste de WCAG 2.x entre el color del elemento y el color que resulta de la superficie sobre el peor fondo. Cuenta todo lo que la superficie aplica al fondo (tinte, opacidad, brillo y saturación) salvo el desenfoque.
  - Con un tinte claro, ignorar el desenfoque es seguro: el desenfoque solo acerca el fondo a su media, y con eso el resultado nunca empeora.
  - Con un tinte oscuro, se mide contra el fondo de referencia más claro y contra el más oscuro.

  Umbrales AA:
  - 4,5:1 para el texto normal;
  - 3:1 para el texto grande (24 px, o 18,66 px en negrita) y para los componentes no textuales que informan: borde de campo, anillo de foco, indicador e iconos.
  - El borde del botón secundario no se mide: es claro por diseño y lo identifica su texto, que sí cumple 4,5:1 sobre su relleno. Los demás componentes no textuales que informan mantienen el 3:1.

### Valores de esta spec
| Valor | Fijado |
|---|---|
| Anchos de diseño y de verificación | 375 px, ampliado a 1280 px; además, 667 × 375 en apaisado para el aviso |
| Tamaño mínimo de un control | 44 × 44 px |
| Contraste | AA (Definiciones) contra el peor fondo, en cristal y en sólido |
| Opacidad mínima del tinte de una superficie de cristal | 80 %, en el panel y en el aviso flotante |
| Colores de relleno distintos en el icono de RentRadar | al menos 3 (tono base, sombra dura y brillo) |
| Diferencia entre las capas del icono a 16 px | razón de contraste de al menos 1,5:1 entre el tono base y la sombra, y entre el tono base y el brillo |
| Contraste de la silueta del icono en la pestaña | al menos 3:1 con un fondo blanco y con el gris oscuro de las pestañas de Chrome en modo oscuro (el plan fija su valor, medido en la versión de Chrome de la verificación) |
| Ralentización de la CPU en la medición | 4× |
| Umbral de rendimiento | fotogramas por segundo ≥ 90 % de la línea base; fotogramas perdidos ≤ línea base + 5 puntos porcentuales |

**Por qué el 80 %, y por qué no basta**. Con un tinte del 70 %, el precio azul sobre la línea de un círculo da 4,75:1, sin margen; con el 80 %, 5,70:1. Pero el peor fondo no es esa línea, sino una etiqueta oscura. Contra el negro puro (WCAG 2.x):

| Tinte | Precio azul #1647B8 | Gris #424B5A | Color de error #B3261E |
|---|---|---|---|
| Blanco al 80 % | 4,98:1 | 5,48:1 | 4,07:1 |
| Blanco al 70 % | 3,79:1 | — | — |
| Cielo #E8EEFF al 80 % | 4,32:1 (no llega a AA) | 4,76:1 | 3,53:1 |

El 80 % es un suelo, no una garantía: manda la medición contra el peor fondo. El texto en color de error sobre un cristal blanco al 80 % no llega a AA como texto normal; como indicador (3:1), sí.

Los demás valores visuales (color del tinte, desenfoque, sombras, radios, colores nuevos, anchura máxima del aviso y duración de las transiciones) los fija el plan a partir de la variante elegida.

## Requisitos funcionales

### Botones y campos
- RF-1: EL SISTEMA muestra cada botón con el aspecto de su tipo y con relieve en reposo. MIENTRAS el botón está pulsado, su relieve se reduce; MIENTRAS está deshabilitado, no tiene relieve ni responde al pasar el puntero.
- RF-2: EL SISTEMA muestra cada campo con su etiqueta visible fija encima, que no se mueve ni desaparece al enfocarlo o escribir. MIENTRAS el campo tiene un error, su borde lleva el color de error y sus mensajes siguen asociados al campo, como en la 009.
- RF-3: CUANDO el visitante pulsa el control del ojo, situado al final del campo de contraseña, EL SISTEMA alterna entre ocultar y mostrar la contraseña y cambia el icono (ojo abierto con la contraseña oculta, ojo tachado con la contraseña visible) y el estado pulsado accesible del control. No cambia su nombre accesible, «Mostrar contraseña», no mueve el foco y no altera el valor del campo.
- RF-4: MIENTRAS la región de estado del formulario de registro muestra un error general, EL SISTEMA lo presenta con el indicador y el texto en tinta, sin limón.
- RF-5: MIENTRAS la región de estado del formulario de registro muestra el envío en curso («Creando la cuenta…»), EL SISTEMA lo presenta sin indicador, sin fondo de color y con el texto en el gris secundario.

### Aviso flotante
- RF-6: CUANDO falla la salida (009, RF-12), EL SISTEMA muestra el aviso flotante, con el indicador, el texto en tinta, «Reintentar» y «Cerrar aviso», pegado al borde inferior de la zona libre:
  - por debajo de 900 px, justo encima del panel;
  - desde 900 px, centrado en la parte del mapa a la derecha de la columna;
  - en una página sin mapa ni panel, abajo y centrado en la zona de contenido.

  SI la zona libre es más baja que el aviso, ENTONCES el aviso sube sobre el panel y tapa parte de él. Nunca tapa el zoom, la atribución ni la barra superior.
- RF-7: MIENTRAS el aviso flotante está visible, EL SISTEMA lo mantiene sin límite de tiempo, también al navegar entre páginas, hasta que el usuario pulsa «Reintentar» o «Cerrar aviso». «Reintentar» lo retira al empezar y lo vuelve a mostrar si falla, como en la 009. CUANDO el usuario pulsa «Cerrar aviso», el aviso desaparece y el foco pasa a «Salir».

### Superficies y movimiento
- RF-8: EL SISTEMA muestra el panel de resultados y el aviso flotante como superficies de cristal: el panel es una sola superficie, y sus tarjetas no tienen superficie translúcida propia. La barra superior y la tarjeta del formulario de registro son sólidas.
- RF-9: SI el navegador no admite desenfocar lo que hay detrás de una superficie, o el usuario ha pedido en su sistema reducir la transparencia o aumentar el contraste, ENTONCES EL SISTEMA muestra el panel y el aviso flotante como superficies sólidas.
- RF-10: MIENTRAS el usuario ha pedido reducir el movimiento, EL SISTEMA no anima ninguna transición de estado de esta spec: cada cambio es inmediato.

### Marca
- RF-11: EL SISTEMA muestra el icono de RentRadar dentro del enlace de la marca de la barra superior, como imagen decorativa: desde 900 px, a la izquierda del nombre; por debajo de 900 px, solo el icono. El nombre «RentRadar» está siempre en la página y es el nombre accesible del enlace en todos los anchos: por debajo de 900 px se oculta a la vista, no se quita. El enlace mide al menos 44 × 44 px también solo con el icono.
- RF-12: EL SISTEMA usa el icono de RentRadar como icono de la pestaña del navegador, en lugar del icono vacío que hay hoy. La silueta del icono contrasta al menos 3:1 con un fondo blanco y con el gris oscuro de las pestañas de Chrome en modo oscuro (Valores), porque la barra del navegador puede ser clara u oscura según el tema del sistema.
- RF-13: EL SISTEMA dibuja el icono de RentRadar con el estilo de ilustración: formas de color sólido en al menos tres colores de relleno distintos. Uno es el tono base, otro la sombra (con menor luminancia que el base) y otro el brillo (con mayor luminancia que el base). Ninguno es el limón.
- RF-14: EL SISTEMA dibuja el icono de RentRadar solo con lo que admite la lista blanca de SVG de la 006: sus etiquetas, sus atributos con la forma exacta de su valor, colores de seis cifras y las transformaciones permitidas.

### Foco
- RF-15: MIENTRAS un botón, un campo, el ojo o un enlace de esta spec tiene el foco del teclado, EL SISTEMA muestra el anillo de foco (Definiciones) alrededor del control, sin que la sombra ni el relleno del control lo oculten y con al menos 3:1 contra la página, contra el cristal sobre su peor fondo y contra el blanco.

## Requisitos no funcionales
- **Entradas y errores**: esta spec no añade entradas del usuario, peticiones a la API ni servicios externos. Las entradas y los errores del formulario y de la salida siguen la 009. La única condición no deseada nueva es un navegador que no puede desenfocar lo que hay detrás (RF-9).
- **Permisos (constitución, punto 5)**: no hay operaciones de la API nuevas ni cambiadas. El visitante, el usuario y el propietario ven y pueden hacer lo mismo que antes. No hay recursos por identificador, así que no hay casos nuevos de 404 ni de 403.
- **Comportamiento conservado**:
  - El comportamiento de la 006 y de la 009 no cambia. Sus tests de comportamiento siguen comprobando lo mismo; solo pueden cambiar los selectores que dependan de la presentación.
  - Del aviso de fallo de salida se conservan los de la 009 (RF-12):
    - el texto «No se ha podido salir. Inténtalo de nuevo.» y «Reintentar»;
    - el anuncio en cada fallo, que es solo ese mensaje, sin los nombres de los botones;
    - el foco en «Salir» tras el fallo;
    - el reintento ante `csrf_failed`;
    - la retirada del aviso al empezar «Reintentar».
  - «Cerrar aviso» es la única acción nueva sobre el estado de sesión de la 009: retira el aviso y no cambia la sesión, la barra superior ni lo que se anuncia.
- **Transiciones**: con movimiento normal, el relieve de los botones, la aparición y salida del aviso y los cambios de estado de los campos se animan en un tiempo corto que fija el plan. Con movimiento reducido no se animan (RF-10). Las dos situaciones se comparan para verificar RF-10.
- **Contraste (constitución, punto 7)**:
  - Sobre una superficie de cristal, todo texto y todo componente no textual que informa cumple AA medido contra el peor fondo, y también sobre la superficie sólida. Fuera del mapa, cumple AA contra su fondo.
  - El tinte del cristal nunca baja del 80 % de opacidad, aunque la medición diera AA con menos. Llegar al 80 % tampoco basta: cada par tiene que dar AA en la medición.
  - Como mínimo se miden estos pares: texto principal, texto secundario, texto del botón secundario sobre su relleno translúcido, precio, mensaje del aviso, cualquier texto en color de error sobre cristal, icono de radio de la tarjeta, anillo de foco (contra la página, el cristal sobre su peor fondo y el blanco), borde del campo, icono del ojo, indicador y texto blanco sobre el botón principal. El anillo usa el mismo azul #1647B8 que el precio: contra el negro puro da 4,98:1 con un tinte blanco al 80 % (tabla de Valores) y 7,99:1 contra blanco.
- **Identidad visual**:
  - Se conservan la tipografía y la paleta de la 006, y el color de error que ya usa la interfaz pasa a la paleta del sistema.
  - Ningún elemento de la interfaz de esta spec usa el limón, reservado para la selección de la 007. Tampoco el icono de RentRadar (RF-13).
  - La imagen de categoría de referencia no es interfaz y no se le aplica esta regla. La gama de las imágenes de categoría, y si un amarillo parecido al limón choca con la reserva de la 007, lo decide la 008.
  - Los colores nuevos (los tintes del cristal y los del icono) se listan en el plan con su contraste.
- **Rendimiento (excepción pedida por el usuario para esta spec, no regla general)**:
  - **Condiciones**: interfaz compilada para producción y servida en local, 375 px de ancho con emulación de móvil, CPU ralentizada 4× en las herramientas del navegador y vista inicial con los bienes de demostración y el panel mostrando sus tarjetas.
  - **Gesto**: un arrastre continuo del mapa de unos 5 s, el mismo en todas las pasadas.
  - **Versiones**: A es la línea base, la interfaz justo antes de la primera tarea de esta spec; B es la interfaz con la spec terminada. Las dos se miden en la misma sesión, con la misma máquina, el mismo ancho, la misma ralentización, los mismos datos y el mismo gesto.
  - **Orden**: primero una pasada de calentamiento de cada versión, que se descarta. Después, seis pasadas alternadas: A, B, A, B, A, B. En cada pasada se registra el tráfico de red, para detectar que una versión aproveche teselas que la otra tuvo que descargar.
  - **Métrica**: fotogramas por segundo durante el arrastre y porcentaje de fotogramas perdidos o presentados a medias, según la pista de fotogramas del navegador. Se toma la mediana de las tres pasadas de cada versión.
  - **Aprobado**: la mediana de fotogramas por segundo de B es al menos el 90 % de la de A, y los fotogramas perdidos de B no superan los de A en más de 5 puntos porcentuales. Si no se aprueba, la spec no se cierra: se ajusta la superficie con el usuario, sin bajar del 80 % de opacidad, y se repite la medición.
- **Accesibilidad y móvil (constitución, punto 7)**:
  - Se diseña a 375 px y se amplía a 1280 px, sin desbordamiento horizontal.
  - Todos los controles miden al menos 44 × 44 px: botones, campos, el ojo, «Cerrar aviso» y el enlace de la marca.
  - Uso completo con teclado. El ojo va en el orden de tabulación justo después del campo de contraseña.
  - El foco se muestra con el anillo de foco (RF-15), visible sobre la superficie de cristal y sobre la sólida, y la sombra de un botón no lo oculta.
  - En el modo de colores forzados del sistema, los botones (también el secundario, aunque su borde sea claro), los campos y las superficies de cristal conservan un contorno visible, y el icono del ojo y el anillo de foco se ven con los colores del sistema.
  - Si el navegador añade su propio botón para ver la contraseña, no se muestra: solo se ve el ojo de RentRadar.
- **Dependencias (constitución, punto 1)**:
  - Ninguna dependencia nueva. Los iconos (marca, ojo, indicador y cierre) son gráficos vectoriales propios, sin librerías de iconos, de animación ni de componentes.
  - Los prototipos cargan la librería del mapa desde una red de distribución de contenidos, con la misma versión fijada que el producto. Eso no es una dependencia del producto: no entra en la aplicación ni en su build, como en los prototipos de la 006.
- **Idioma (constitución, punto 8)**: los textos nuevos («Cerrar aviso») van en castellano en el catálogo de mensajes.

## Casos límite
- El panel queda sobre la línea azul de un círculo o sobre una etiqueta oscura del mapa: su texto cumple AA contra el peor fondo, incluido el negro puro (Contraste).
- Una variante con un tinte del 75 % que da AA en la medición: no se acepta, porque el mínimo es el 80 % (Valores).
- Una variante con tinte cielo #E8EEFF al 80 %: el precio azul da 4,32:1 contra el negro y no llega a AA. Se mide, y esa variante necesita más opacidad u otro color de precio (Contraste).
- Un texto en color de error sobre un cristal blanco al 80 %: 4,07:1 contra el negro, no llega a AA como texto normal. El indicador, que pide 3:1, sí llega (Contraste).
- El navegador no puede desenfocar lo que hay detrás: el panel y el aviso son sólidos y cumplen AA (RF-9).
- El usuario pide reducir la transparencia o aumentar el contraste: superficies sólidas (RF-9). Si pide reducir el movimiento: sin transiciones (RF-10).
- La salida falla en «Página no encontrada» o con el error del mapa base (sin mapa ni panel): el aviso aparece abajo y centrado en la zona de contenido (RF-6).
- La ventana cruza los 900 px con el aviso visible: el aviso cambia de sitio sin tapar el zoom, la atribución ni la barra superior (RF-6).
- A 375 px el mensaje ocupa dos líneas o más: el aviso crece hacia arriba y «Reintentar» y «Cerrar aviso» siguen midiendo al menos 44 px. Si no cabe en la zona libre, tapa parte del panel, nunca el zoom ni la atribución (RF-6).
- En apaisado a 667 × 375 px quedan unos 79 px libres sobre el panel, y el zoom y la atribución ocupan más de 88 px arriba. Lo mismo pasa con el texto ampliado al 200 %. En los dos casos el aviso gana espacio sobre el panel y no tapa el zoom, la atribución ni la barra superior (RF-6).
- Se arrastra el mapa con el aviso visible: el aviso no se mueve con el mapa, y fuera de su superficie el arrastre llega al mapa (RF-6).
- Con el aviso visible, el usuario pulsa la marca o abre otra página: el aviso sigue visible en la página nueva (RF-7).
- «Reintentar» vuelve a fallar: el aviso se retira al empezar y vuelve a mostrarse y anunciarse (RF-7; Comportamiento conservado). Si sale bien: el aviso desaparece y «Has salido» se anuncia como en la 009.
- El usuario cierra el aviso y la salida vuelve a fallar: el aviso vuelve a aparecer (RF-7).
- Se pulsa el ojo durante el envío, con el campo en solo lectura: alterna la visibilidad y el valor no cambia (RF-3).
- El botón se mantiene pulsado con Espacio: se ve pulsado igual que con el puntero (RF-1). Un botón deshabilitado («Crear cuenta» durante el envío o «Salir» durante la salida) no tiene relieve ni responde al puntero (RF-1).
- El navegador añade su propio botón de ver contraseña (Edge): no aparece. Chrome no lo muestra, así que se comprueba por la regla que lo oculta (Accesibilidad).
- En colores forzados la sombra desaparece: los botones, los campos y las superficies de cristal se reconocen por su contorno, el borde del secundario y el anillo de foco toman los colores del sistema, y el ojo se ve (Accesibilidad; RF-15).
- Un botón secundario sobre un aviso de cristal sobre su peor fondo: su borde claro da alrededor de 1,5:1 y no se exige. El botón se reconoce por su texto (AA sobre su relleno), su relleno translúcido y su sombra (Definiciones; Contraste).
- Un botón secundario sobre la barra superior blanca o sobre la tarjeta blanca del registro: se distingue del fondo por su relleno teñido de cielo, no solo por su sombra (Definiciones).
- El foco llega a un botón con sombra azul o a un campo de un formulario: el anillo de 2 px queda separado 2 px del control y su sombra no lo tapa (RF-15).
- El foco llega a un control del mapa (zoom, atribución): conserva el anillo de la 006, porque el azul #1647B8 no se distinguiría de la línea azul de los círculos (Fuera de alcance).
- A 375 px el enlace de la marca muestra solo el icono, y este y «Registrarse» o «Salir» caben en la barra sin desbordarla. El enlace mide al menos 44 × 44 px, el nombre no se ve y su nombre accesible sigue siendo «RentRadar» (RF-11).
- La ventana cruza los 900 px: el nombre de la marca aparece o se oculta a la vista y el nombre accesible del enlace no cambia (RF-11).
- En la captura de la pestaña a 16 px, la sombra y el brillo se distinguen del tono base con al menos 1,5:1 de razón de contraste (Valores; RF-12, RF-13).
- La barra del navegador es clara (fondo blanco) u oscura (gris oscuro de las pestañas de Chrome en modo oscuro): la silueta del icono contrasta al menos 3:1 con los dos. Una silueta en el azul #1647B8 llega a 7,99:1 con el blanco, pero solo a unos 2:1 con el gris oscuro, así que no se acepta: el contorno necesita capas más claras (RF-12; Valores).
- Un dibujo del icono con un degradado, una transformación de escala, un color de tres cifras o una etiqueta de grupo: no cumple la lista blanca (RF-14).

## Fuera de alcance
- Barra de navegación inferior en móvil (spec 008).
- Rehacer las once imágenes de categoría de la aplicación: llega en la 008. La 016 solo aporta la imagen de categoría de referencia de los prototipos, que no entra en la aplicación.
- Cambiar la lista blanca de SVG de las imágenes de categoría de la 006 o lo que comprueba su test: se mantienen tal cual. Mover las reglas a un módulo que compartan los dos tests no es un cambio.
- Avatar y su menú (spec 014).
- Filtro y colapso del panel, y la selección que usa el limón (spec 007).
- Formulario de entrada (spec 015), que reutilizará estas piezas.
- Avisos flotantes sin acción o con cierre automático, y avisos visibles para otros mensajes (como «Has salido» o los errores del panel).
- Cerrar el aviso con Escape.
- La barra superior como superficie de cristal sobre el mapa: sigue sólida y encima de la zona de contenido.
- Cambiar el aspecto de los controles del mapa (zoom y atribución) más allá de lo que fijó la 006. En particular, su anillo de foco sigue el de la 006.
- Exigir un contraste de 3:1 al borde del botón secundario: lo identifica su texto.
- Modo oscuro y recolorear el mapa base (como en la 006).
- Medir el rendimiento en navegadores distintos de Chromium.
- Un icono de pestaña de respaldo en formato de mapa de bits.
- Catálogo visual o documentación interactiva de los componentes, y animaciones que no sean transiciones de estado.

## Cambios en otras specs
No hace falta `/sdd-change`:
- **009, RF-12**: fija el texto, el botón «Reintentar», el anuncio y el foco, no la posición ni el color; se conserva entero. «Cerrar aviso» se añade sin contradecirlo (RF-6, RF-7; Comportamiento conservado).
- **009, no funcionales**: el control «Mostrar contraseña» que alterna ver y ocultar y sus 44 px se cumplen con el ojo y su nombre fijo (RF-3).
- **006, RF-8 e identidad visual**: la atribución vuelve a quedar siempre visible (RF-6) y el limón vuelve a quedar sin uso en la interfaz.
- **006, lista blanca de SVG de las imágenes de categoría**: no cambia la lista ni lo que comprueba su test. El plan puede mover sus reglas a un módulo que usen ese test y el del icono.
- **006, controles del mapa**: conservan su anillo de foco; el de esta spec solo se usa en sus superficies (RF-15).
- **009, RF-9**: la marca sigue siendo un enlace a la página del mapa; por debajo de 900 px solo se ve el icono, con el mismo nombre accesible (RF-11).

Ajustes de texto al cerrar la spec:
- MEMORY.md:
  - la 016 entra en la hoja de ruta antes de la 015;
  - desaparece el punto «Spec visual nueva»;
  - la línea de la 015 pasa de «rediseñar el formulario de registro…» a «el formulario de entrada usa los campos, el ojo y los botones de la 016»;
  - la línea de la 008 cita la imagen de categoría de referencia de la 016 como punto de partida para rehacer las once imágenes, dentro de la lista blanca de la 006 sin cambiarla;
  - la línea de la 007 recoge que, al cambiar la altura del panel, el aviso flotante tiene que seguir anclado a él.
- Notas de la 015, punto 8: el formulario de entrada usa los campos, el ojo y los botones de la 016.

## Riesgos aceptados
- **Mapa base de un tercero**: el estilo «positron» se descarga en cada carga. Si cambia sus colores, el contraste medido puede caducar sin que cambie el código, y nada lo detecta automáticamente.
- **Rendimiento medido solo en Chromium**, con la CPU emulada: Safari en iOS y Firefox no quedan medidos.
- **Altura del panel**: la 007 la cambia (plegado, medio y desplegado), y el aviso tendrá que seguir anclado a ella sin tapar el zoom ni la atribución.
- **Icono de la pestaña**: un navegador que no admita un icono vectorial en la pestaña muestra su icono por defecto; no hay respaldo en mapa de bits.
- **Secundario sin contraste de borde**: sobre un cristal claro, el borde del secundario casi desaparece y el botón depende de su texto, su relleno y su sombra. El usuario lo aceptó al elegir el borde claro.
- **Foco durante «Reintentar»**: deuda heredada de la 009 y anotada para la 014. Al empezar el reintento el aviso se retira, y el foco puede quedar sin elemento hasta 10 s. «Cerrar aviso» es otro botón del aviso que sufre lo mismo si el foco estaba en él.

## Criterios de finalización
- **Variantes**: dos o tres en `prototypes/016-visual-system/`, diseñadas con la skill frontend-design en HTML estático. Usan la librería del mapa en la misma versión fijada que el producto, cargada desde una red de distribución de contenidos, el mapa base «positron» y círculos de demostración. Llevan un índice y capturas a 375 y 1280 px, y se commitean con la aprobación del usuario. No cuentan como tareas del plan. Cada variante muestra:
  - el panel de cristal sobre el mapa real, incluido el peor fondo, con un tinte de al menos el 80 %;
  - el aviso flotante, con el mismo mínimo;
  - los botones (principal y secundario) en reposo, pulsados, con foco (con el anillo de foco de RF-15) y deshabilitados;
  - el campo de contraseña con el ojo;
  - la superficie sólida;
  - el icono de RentRadar con el estilo de ilustración y dentro de la lista blanca de la 006, también solo, sin el nombre, como se verá por debajo de 900 px;
  - una imagen de categoría de referencia con el estilo de ilustración, de la misma categoría en todas las variantes. Cumple la lista blanca de SVG de la 006, comprobada con las mismas reglas que su test, sin cambiar la lista blanca ni lo que comprueba ese test.

  Para elegir una variante, el icono tiene que reconocerse sin el nombre al lado, y su sombra tiene que verse desplazada respecto a la forma base. El usuario elige una antes del plan, y el plan la registra.
- **Tests y verificaciones**: cada RF tiene un test automático o una verificación en el navegador registrada en `validation.md`.
  - vitest:
    - en el marcado del ojo: el nombre fijo «Mostrar contraseña» y el estado pulsado en los dos estados (RF-3);
    - en el marcado de la marca: el icono decorativo y el nombre «RentRadar» dentro del enlace, aunque se oculte a la vista (RF-11);
    - la regla que cierra el aviso: el estado del aviso pasa a ninguno (RF-7);
    - el icono tiene al menos tres colores de relleno distintos, la sombra tiene menor luminancia y el brillo mayor que el tono base, y ninguno es el limón (RF-13);
    - un test propio del icono aplica las mismas reglas de la lista blanca de la 006 (etiquetas, atributos con la forma exacta de su valor, colores de seis cifras y transformaciones permitidas), sin cambiar la lista blanca ni lo que comprueba el test de la 006 (RF-14).
  - navegador:
    - alternancia del ojo, foco que no se mueve y valor conservado (RF-3);
    - el aviso sigue visible tras 60 s sin interacción y tras navegar a otra página, y al cerrarlo el foco pasa a «Salir» (RF-7);
    - RF-1 por estilo calculado: hay sombra en reposo, se reduce al pulsar y no hay sombra en un botón deshabilitado;
    - el secundario sobre superficie blanca: captura de «Salir» en la barra superior y de un secundario sobre la tarjeta del formulario de registro, donde el relleno teñido lo separa del fondo;
    - RF-15 por estilo calculado: anillo de 2 px en #1647B8 separado 2 px en el botón principal, el secundario, el campo, el ojo y el enlace de la marca, y su contraste contra la página, el cristal sobre su peor fondo y el blanco (3:1 como mínimo);
    - RF-2, RF-4, RF-5, RF-8 y RF-9;
    - RF-10, comparando la duración de las transiciones con movimiento normal (mayor que cero) y con movimiento reducido (cero);
    - la posición de RF-6;
    - RF-11 a 375 px: el nombre de la marca no se ve, el nombre accesible del enlace sigue siendo «RentRadar» y el enlace mide al menos 44 × 44 px;
    - el icono en la pestaña de RF-12: captura de la pestaña a 16 px con el tema claro y con el oscuro del sistema, con el umbral de 1,5:1 entre capas y el de 3:1 de la silueta contra cada fondo;
    - el desplazamiento de la sombra del icono, en las capturas de las variantes y en la de la pestaña.
- **Contraste**: en `validation.md`, una tabla con cada par de la lista mínima, la superficie (cristal y sólida), la opacidad del tinte (al menos el 80 %), el peor fondo (también el negro puro), el valor calculado y el umbral, todos aprobados. Además, una comprobación en el navegador con el panel sobre la zona más oscura del mapa (línea de un círculo y etiquetas).
- **Posición del aviso**, con sus límites en pantalla registrados:
  - a 375 y a 1280 px, no se cruzan con los del zoom, la atribución, la barra superior ni el panel;
  - a 667 × 375 px y con el texto ampliado al 200 %, no se cruzan con los del zoom, la atribución ni la barra superior; puede tapar parte del panel.
- **Respaldo y preferencias**: se comprueban la transparencia reducida, el contraste alto, el movimiento reducido y los colores forzados. Si el navegador no puede emular alguna, se comprueba por el estilo calculado. El caso de un navegador sin desenfoque se comprueba desactivando el desenfoque en el navegador. El botón propio de ver contraseña de otros navegadores se comprueba por la regla que lo oculta, y se anota que Chrome no lo muestra.
- **Accesibilidad**, comprobada en el navegador y registrada:
  - medidas de al menos 44 × 44 px del ojo, «Cerrar aviso», el enlace de la marca, los botones y los campos;
  - orden de tabulación, con el ojo justo después del campo de contraseña;
  - la sombra de los botones no oculta el anillo de foco;
  - sin desbordamiento horizontal a 375 px.
- **Rendimiento**: las dos pasadas de calentamiento descartadas y las seis pasadas alternadas (A, B, A, B, A, B), con su tráfico de red, sus medianas y su veredicto, registradas en `validation.md`.
- **Navegador**, a 1280 y 375 px, con la consola sin errores propios de la aplicación y un recorrido solo con teclado: marca, «Registrarse» y «Salir», el aviso con «Reintentar» y «Cerrar aviso» (la salida fallida se simula cortando la petición desde las herramientas del navegador), el panel con «Reintentar» y «Volver a la zona inicial», el formulario de registro (email, contraseña, ojo y «Crear cuenta»), «Ir al mapa» y el error del mapa base.
  - Para ver «Salir» y el aviso hace falta una sesión: se crea una cuenta `@example.com` en la base de datos de desarrollo con autorización expresa del desarrollador en ese momento, como en la 009.
- **Pruebas de mecanismo**: ninguna, porque la spec no toca privacidad ni seguridad.
- vitest, build y eslint de los ficheros tocados, en verde.
- MEMORY.md y las notas de la 015 actualizadas (Cambios en otras specs).

## Dudas abiertas
- Ninguna sobre el comportamiento.
- **Notas para el plan (no cambian la spec)**:
  - **Secundario y foco**: el plan fija el relleno, el borde claro y la sombra del secundario (los prototipos usan blanco al 70 % con borde blanco al 90 %), cómo se dibuja el anillo separado 2 px sin que lo recorte un contenedor con desbordamiento oculto, y si los controles de la 006 que hoy usan otro anillo se quedan como están.
  - **Medición de rendimiento**: cómo se reproduce el mismo gesto de arrastre en todas las pasadas, cómo se sirven las dos compilaciones (A y B) en la misma sesión y cómo se obtienen de la traza los fotogramas por segundo y los perdidos.
  - **Respaldo**: cómo se desactiva el desenfoque. Qué emulaciones admite la herramienta del navegador (transparencia reducida, contraste alto y colores forzados; la 006 solo documenta el movimiento reducido) y, para cada una que no admita, qué estilo calculado se comprueba en su lugar.
  - **Contraste**: de dónde salen los colores de los fondos de referencia del estilo «positron».
  - **Marcado accesible**: «deshabilitado» es `aria-disabled`, como en la 009. El rol de estado va solo en el mensaje del aviso, en un elemento siempre montado para que cada fallo se anuncie. «Cerrar aviso» y «Reintentar» quedan fuera de ese elemento.
  - **Icono, carpeta**: no puede vivir en la carpeta de las imágenes de categoría. El test de la 006 la recorre entera, comprueba que son las 11 de la semilla, y el código de imágenes lo trataría como una categoría.
  - **Icono, test de capas**: la lista blanca no admite identificadores ni clases, así que el plan fija cómo distingue el test el tono base, la sombra y el brillo (por ejemplo, por su orden en el dibujo).
  - **Icono, pestaña**: tiene que ser un fichero propio del sitio, no datos incrustados en la página, porque la 006 cierra el origen de las imágenes al propio sitio.
  - **Icono, pestaña en dos temas**: el gris oscuro de las pestañas de Chrome en modo oscuro se mide en la versión de Chrome de la verificación. Las capturas de página de las herramientas del navegador no incluyen la barra de pestañas, así que el plan fija cómo se obtiene la captura de la pestaña en los dos temas.
  - **Tests sin entorno de navegador**: vitest corre sin entorno de navegador y añadir uno sería una dependencia nueva. Por eso las comprobaciones de interacción (ojo, foco, persistencia del aviso) van al navegador.
  - **Tope de tareas**: si el plan llega a 11 tareas, la salida natural es sacar la marca (RF-11 a RF-14) a su propia tarea o a su propia spec.
