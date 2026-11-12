# Spec 017 — Imágenes de categoría y categoría «Esquí»
Estado: aprobada
Depende de: spec 004 (reglas de las categorías y semilla de once; las categorías solo cambian por migración), spec 005 (RF-22: no se borra una categoría con bienes, tampoco al revertir una migración; test de fugas), spec 006 (tarjeta del panel, imagen de «Otros» como respaldo, RF-6 del comando de demostración y decisión de entregar las imágenes como ficheros del propio sitio) y spec 016 (panel de cristal y superficie sólida, y reglas de la lista blanca de SVG que usa el icono de RentRadar).

## Contexto y objetivo
Hoy cada tarjeta del panel muestra una imagen genérica de su categoría. Son once dibujos vectoriales sencillos que la 006 admitió con una lista blanca de etiquetas y atributos. A 72 px se reconocen mal y no tienen la calidad visual que pide el producto. Además, falta una categoría que se pide mucho en un alquiler entre particulares: el material de esquí.

Esta spec:
- sustituye las once imágenes vectoriales por doce imágenes WebP con fondo transparente, una por categoría del catálogo. Están generadas con IA (Gemini) y ya vienen sin fondo. Fuera del producto se reducen a 144 × 144 px, se les quitan los metadatos y cada fichero recibe el nombre de su clave;
- añade al catálogo la categoría Esquí, con clave `ski`, en una migración de datos propia que no toca la semilla de la 004;
- incluye un bien de Esquí en los datos de demostración, sin cambiar sus cifras ni sus condiciones;
- fija criterios comprobables para aceptar cada fichero (estructura, peso, bloques, dimensiones y transparencia) y una aprobación humana, imagen por imagen, de lo que no se puede medir (sin sombra, sin texto ni marcas, se reconoce a su tamaño real);
- mantiene la decisión de seguridad de la 006: cada imagen llega al navegador como fichero del propio sitio y nunca incrustada como datos. Así la 011 puede limitar el origen de las imágenes al propio sitio. A partir de ahora lo vigila un test. Reducidas a 144 px con pérdida, varias imágenes pueden pesar menos que el umbral de incrustación por defecto (por ejemplo, 4 KiB), así que la guarda es necesaria;
- deja la lista blanca de SVG solo para el icono de RentRadar (016), porque ya no quedan imágenes de categoría vectoriales.

Por qué WebP y 2×: un render no se puede expresar como SVG con lista blanca. WebP admite transparencia, pesa poco y lo leen todos los navegadores. Al doble del tamaño de presentación se ve nítido en las pantallas de densidad 2, que son la mayoría de portátiles y móviles. Con doce imágenes pequeñas no compensa servir una versión por densidad.

Parte del trabajo no necesita las imágenes: el catálogo, la demostración, la guarda contra la incrustación y la validación de los ficheros, que se prueba con casos fabricados. La comprobación de que hay exactamente una imagen por categoría solo puede pasar cuando están las doce, así que llega con ellas. La spec no se cierra sin las doce aprobadas.

## Usuarios
- **Visitante**: ve en el panel la imagen de la categoría de cada bien, también la de Esquí.
- **Anunciante**: podrá clasificar su material de esquí en su propia categoría cuando pueda publicar (spec 010). En esta spec no publica.
- **Desarrollador del equipo**: aprueba las imágenes una a una en la hoja de revisión, anota su procedencia y da la orden expresa de recrear la base de datos de desarrollo para comprobar la tarjeta de Esquí con los datos de demostración.

## Historias de usuario
- HU-1. Como visitante, quiero reconocer de un vistazo la categoría de cada bien por una imagen nítida y clara, en el móvil y en el escritorio, para recorrer el panel más deprisa.
- HU-2. Como anunciante, quiero una categoría Esquí para que mi material no quede perdido en «Otros».
- HU-3. Como desarrollador, quiero que las imágenes lleguen siempre como ficheros del propio sitio, para poder cerrar en la 011 el origen de las imágenes al propio sitio sin excepciones.
- HU-4. Como desarrollador, quiero que cada fichero cumpla criterios comprobables y no lleve metadatos, para que una imagen generada fuera no entre con un peso, unos datos o un formato inesperados.
- HU-5. Como desarrollador, quiero saber de dónde sale cada imagen sin cargar el repositorio con los originales ni los prompts.

## Definiciones
- **Clave de una categoría**: su slug (004, RF-13).
- **Catálogo de categorías**: las categorías que existen tras aplicar las migraciones: las once de la semilla de la 004 y Esquí, doce en total. El visitante ve el nombre que viene de este catálogo, a través de la lista pública (006, RF-2). La interfaz no guarda ninguna copia de los nombres de categoría.
- **Migración de Esquí**: migración de datos propia, posterior a la semilla de la 004. Solo crea la categoría `ski` o le deja su nombre. No modifica la semilla ni cambia la clave ni el nombre de ninguna otra categoría.
- **Esquí** (criterio de clasificación):
  - material para deslizarse sobre la nieve, de cualquier modalidad (pista, travesía o fondo), con su equipo específico: botas, fijaciones, bastones y pieles;
  - incluye el snowboard: tabla, botas y fijaciones;
  - el casco, las gafas y la ropa técnica de esquí o de snowboard entran en Esquí aunque se alquilen sueltos;
  - las raquetas de nieve, los trineos y las motos de nieve van a «Otros».
- **Imagen de categoría**: imagen genérica y decorativa que identifica la categoría de un bien en su tarjeta (006, definición de tarjeta). Hoy no tiene ningún otro uso en la interfaz.
- **Tamaño de presentación**: 72 × 72 px CSS, el de la tarjeta de la 006. **Tamaño de la imagen**: 144 × 144 px, el doble.
- **Rechazar un fichero**: un test automático falla. Con ese test en rojo no se puede hacer commit (constitución, punto 4).
- **WebP bien formado**:
  - empieza por la firma del contenedor RIFF con el tipo `WEBP`; no basta con la extensión;
  - el tamaño que declara el contenedor, más 8, coincide exactamente con la longitud del fichero: no hay datos detrás del contenedor y el fichero no está truncado;
  - cada bloque termina dentro del fichero, contado su byte de relleno cuando el tamaño es impar, y el recorrido de los bloques termina exactamente al final del fichero;
  - un fichero de 0 bytes no está bien formado.
- **Bloques admitidos**: VP8X (cabecera ampliada), ALPH (transparencia de una imagen con pérdida), VP8 (imagen con pérdida) y VP8L (imagen sin pérdida). Se comprueban por su nombre. Cualquier otro bloque no se admite: EXIF, XMP, perfil de color, animación o uno desconocido. Un fichero lleva un único bloque de imagen (VP8 o VP8L). Su estructura es una de estas dos:
  - sin VP8X: un único bloque, VP8L, con su indicador de alfa activo;
  - con VP8X: este es el primer bloque, y detrás va o ALPH seguido de VP8, o VP8L solo.

  ALPH solo se admite con VP8X y justo delante de un VP8. Junto a VP8L los decodificadores lo ignoran, así que serviría para esconder datos; detrás de un VP8 no se lee.
- **Declara transparencia**: si el fichero lleva VP8X, su bandera de alfa vale 1 y, cuando la imagen es con pérdida (VP8), hay además un bloque ALPH con datos. Si no lleva VP8X, la imagen es sin pérdida (VP8L) y tiene activo su indicador de alfa. Un VP8 simple, sin VP8X, no tiene transparencia.
- **Fondo transparente**: todo lo que no es el objeto representado tiene opacidad cero. No hay sombra proyectada, halo ni restos del fondo original. Los bordes suavizados del objeto sí se admiten. Se comprueba de dos formas:
  - objetiva, en el navegador: un cuadrado de 8 × 8 px en cada esquina de la imagen, con opacidad cero;
  - a ojo, en la hoja de revisión: no se ve recuadro, sombra, halo ni restos del fondo.
- **Incrustación**: la compilación de la interfaz convierte en datos dentro del código (`data:`) los ficheros que pesan menos que un umbral, en vez de servirlos como ficheros. **Guarda contra la incrustación**: lo que obliga a servir cada imagen de categoría como fichero, pese lo que pese.
- **Pareja confundible**: categorías que a 72 px pueden tomarse una por otra: kayak y piragua; caravana, autocaravana y furgoneta.
- **Comparten estilo**: las doce tienen la misma perspectiva, la misma iluminación y una paleta común.
- **Hoja de revisión**:
  - composición con las doce imágenes a 72 y a 144 px CSS, sobre el color de la superficie sólida del panel (016); cada imagen va rotulada con su clave;
  - se genera fuera del repositorio, en `~/RentRadar-recursos/`, y no se versiona;
  - el desarrollador aprueba cada imagen por separado, incluida su asignación a la clave (por ejemplo, que no haya un kayak con la clave de la piragua). La aprobación de cada imagen, con su fecha, queda registrada en la validación;
  - una imagen que no se aprueba no entra: se vuelve a preparar o a generar fuera del producto y pasa de nuevo por la hoja. Si conserva sombra o halo, se regenera; no se retoca a mano.
- **Originales**: los doce ficheros de `~/RentRadar-recursos/categorias/`, ya sin fondo. Las versiones con fondo no se conservaron. Sus nombres no tienen por qué coincidir con las claves; el nombre `<clave>.webp` se pone al copiar cada imagen preparada al repositorio. La carpeta `~/RentRadar-recursos/categorias/` no se renombra ni se modifica; la hoja de revisión se genera en `~/RentRadar-recursos/`, fuera de ella, y eso no cuenta como modificarla. Su ficha de fuentes (`fuentes.md`, con la herramienta, el mes y el método, sin el prompt) ya existe allí, fuera del repositorio.
- **Procedencia**: una línea de la validación que dice:
  - que las imágenes son generadas con IA, con qué herramienta, en qué fecha o fechas y, si la herramienta la muestra, con qué versión del modelo;
  - qué retoques se les han hecho: reducidas a 144 × 144 px, sin metadatos y con el nombre de su clave; el fondo ya venía quitado en los originales;
  - que se ha comprobado que los términos de uso de la herramienta permiten el uso comercial.

  No incluye el prompt ni rutas absolutas; las rutas se escriben con `~`.

### Valores de esta spec
| Valor | Fijado |
|---|---|
| Categorías del catálogo e imágenes | 12 (las 11 de la semilla y `ski`) |
| Nombre de la categoría nueva | «Esquí» (NFC, 5 caracteres) |
| Tamaño de presentación en la tarjeta | 72 × 72 px CSS (el de la 006) |
| Tamaño de cada imagen | 144 × 144 px exactos, lienzo e imagen codificada |
| Peso máximo de cada imagen | 16 KiB (16 384 bytes) |
| Esquinas transparentes | 8 × 8 px en cada esquina, opacidad cero |
| Nombre de cada fichero | `<clave>.webp`, en minúsculas y exactamente igual a la clave |
| Bienes de demostración | 25 (24 activos y 1 pausado, el último); el de Esquí sustituye a la furgoneta de la posición 23, contando desde 0 |

## Requisitos funcionales

### Categoría Esquí
- RF-1: CUANDO se aplican las migraciones, EL SISTEMA deja creada la categoría con clave `ski` y nombre «Esquí», que cumple las reglas de las categorías de la 004 (RF-14 a RF-17 y RF-23).
- RF-2: CUANDO la migración de Esquí se aplica sobre una base de datos que ya tiene la clave `ski`, EL SISTEMA no la duplica y le deja el nombre «Esquí». Si se aplica dos veces, queda una sola categoría `ski`.
- RF-3: SI al aplicar la migración de Esquí otra categoría, con otra clave, ya tiene un nombre que coincide con «Esquí» sin distinguir mayúsculas (004, RF-17), ENTONCES EL SISTEMA hace fallar la migración entera, sin crear ni cambiar ninguna categoría.
- RF-4: CUANDO se revierte la migración de Esquí, EL SISTEMA borra solo la categoría `ski` y conserva las once de la semilla y cualquier otra. SI hay bienes en Esquí, ENTONCES rechaza la reversión del mismo modo que la 005 (RF-22): no borra ninguna categoría ni ningún bien, y la migración sigue aplicada.

### Datos de demostración
- RF-5: CUANDO el comando de demostración crea los bienes (006, RF-6), EL SISTEMA crea:
  - 25 bienes, 24 activos y uno pausado, que es el último;
  - todos con la ubicación pública a menos de 4 km del centro de la vista inicial;
  - con los tres radios de privacidad, al menos un bien de cada categoría de la semilla y al menos dos bienes con la misma ubicación pública y el mismo radio;
  - y al menos un bien activo de Esquí. Es el de la posición 23, contando desde 0, que hasta ahora era la tercera furgoneta. Conserva su ubicación y su radio, y pasa a tener la categoría, el título y la descripción de un bien de esquí.

  No cambian el bien de la posición 11, que comparte ubicación pública y radio con el de la posición 0, ni el pausado (posición 24).

### Imágenes de categoría
- RF-6: EL SISTEMA tiene exactamente una imagen de categoría por cada categoría del catálogo: doce ficheros WebP, cada uno con el nombre de su clave (`ebike.webp`, `sports-area.webp`, `ski.webp`…). SI falta la imagen de alguna categoría o sobra algún fichero, ENTONCES un test automático falla. Cuentan como sobrantes los que no corresponden a ninguna clave, los de otro formato, los ocultos y los de subcarpetas.
- RF-7: CUANDO el panel muestra la tarjeta de un bien, EL SISTEMA muestra la imagen de su categoría a 72 × 72 px, sin deformarla y como imagen decorativa, como en la 006. SI la clave no tiene imagen (desconocida para el cliente, vacía, con otras mayúsculas o con un nombre heredado como `__proto__`), ENTONCES muestra la imagen de «Otros» junto al nombre de categoría que trae el bien.
- RF-8: EL SISTEMA entrega cada imagen de categoría al navegador como un fichero del propio sitio, con su propia petición, y nunca incrustada como datos (`data:`) en el código ni en los estilos. Vale en la compilación para producción y en desarrollo, también cuando la imagen pesa menos que el umbral de incrustación.

### Validación de los ficheros
- RF-9: SI un fichero de imagen de categoría no es un WebP bien formado (Definiciones) o pesa más de 16 KiB (16 384 bytes), ENTONCES EL SISTEMA lo rechaza.
- RF-10: SI un fichero de imagen de categoría contiene algo más que una única imagen fija, ENTONCES EL SISTEMA lo rechaza. Cuenta como algo más:
  - un bloque fuera de los admitidos: EXIF, XMP, perfil de color, animación o un bloque desconocido;
  - un segundo bloque de imagen;
  - un orden o una combinación de bloques no admitidos (Definiciones): VP8X que no es el primer bloque, ALPH sin VP8X, ALPH junto a VP8L o ALPH detrás de un VP8;
  - un bloque VP8X con alguna de las banderas de perfil de color, EXIF, XMP o animación activa.
- RF-11: SI la imagen codificada de un fichero de imagen de categoría no mide exactamente 144 × 144 px, ENTONCES EL SISTEMA lo rechaza. También lo rechaza si el fichero lleva VP8X y el lienzo que declara no mide 144 × 144 px o no coincide con la imagen codificada.
- RF-12: SI un fichero de imagen de categoría no declara transparencia (Definiciones), ENTONCES EL SISTEMA lo rechaza.

### Aprobación de las imágenes
- RF-13: EL SISTEMA solo incluye imágenes de categoría con fondo transparente (Definiciones): opacidad cero en los cuadrados de 8 × 8 px de las cuatro esquinas, y sin sombra proyectada, halo ni restos del fondo. Los bordes suavizados del objeto se admiten.
- RF-14: EL SISTEMA solo incluye imágenes de categoría que no contienen:
  - texto, letras, cifras, logos ni marcas reconocibles;
  - una marca de agua visible del generador;
  - personas ni rostros;
  - la forma reconocible de un modelo comercial de un fabricante concreto.
- RF-15: EL SISTEMA solo incluye imágenes de categoría que muestran la categoría de su clave y, a 72 px y sin el nombre al lado, se reconocen como esa categoría. Además, se distinguen de su pareja confundible y comparten estilo con las otras once (Definiciones).

## Requisitos no funcionales
- **Seguridad (constitución, punto 6)**:
  - Las imágenes vienen de un servicio externo, así que se tratan como entrada no fiable. La estructura, el peso, los bloques, las dimensiones y la transparencia se comprueban con tests (RF-9 a RF-12).
  - Comprobar la firma y la estructura impide que entre con la extensión `.webp` un fichero de otro tipo, por ejemplo un SVG con scripts, o un fichero con datos escondidos detrás del contenedor.
  - Una imagen WebP no puede llevar scripts ni referencias externas, así que la lista blanca de SVG ya no se aplica a las imágenes de categoría.
  - La guarda contra la incrustación (RF-8) tiene un test que falla si se pierde la guarda, aunque todas las imágenes pesen más que el umbral por defecto. El test compila la interfaz con un umbral de incrustación muy por encima del peso de las imágenes. Después comprueba que ninguna imagen de categoría sale como `data:`, ni en el código ni en los estilos, y que las doce salen como ficheros.
  - En el mismo test, un control positivo demuestra que el test puede fallar: una imagen real importada sin la guarda sí sale como `data:`.
- **Privacidad**:
  - Sin metadatos (RF-10), las imágenes no llevan datos de generación, de cuenta ni de equipo. La validación de bloques y estructura impide que esos datos lleguen al repositorio.
  - En el repositorio no entran el prompt, los originales, la ficha de fuentes ni la hoja de revisión (Definiciones).
  - Ni la spec, ni la validación, ni los commits contienen rutas absolutas ni nombres de usuario; las rutas se escriben con `~`.
- **Permisos (constitución, punto 5)**:
  - No hay operaciones de la API nuevas ni cambiadas, y el contrato publicado no cambia porque la clave de la categoría no está enumerada.
  - Esquí es una categoría más de la lista pública, con los mismos permisos para el anónimo, el usuario y el propietario.
  - No hay recursos nuevos por identificador, así que no hay casos nuevos de 404 ni de 403.
- **Accesibilidad y móvil (constitución, punto 7)**:
  - La imagen sigue siendo decorativa, sin texto alternativo, y la categoría se lee en el nombre de la tarjeta.
  - No hay controles nuevos y el recorrido con teclado del panel no cambia.
  - La tarjeta se comprueba a 375 y a 1280 px, sin desbordamiento horizontal ni errores en la consola.
- **Rendimiento**:
  - Cada imagen pesa 16 KiB como máximo y se sigue cargando solo cuando su tarjeta se acerca a la vista, como en la 006.
  - La tarjeta reserva el hueco de 72 px antes de que llegue la imagen, así que la imagen no desplaza el contenido.
- **Identidad visual**:
  - Las imágenes de categoría son contenido, no interfaz. La reserva del limón para la selección de la 007 no se les aplica, y pueden tener amarillos.
  - Su fondo es transparente y ninguna lleva sombra proyectada.
- **Dependencias (constitución, punto 1)**:
  - Ninguna nueva.
  - Las imágenes se preparan fuera del producto: se reducen a 144 × 144 px, se les quitan los metadatos y se les pone el nombre de su clave. El fondo ya viene quitado.
  - En el repositorio no entra ninguna herramienta de preparación, y los manifiestos de dependencias no cambian.
- **Idioma (constitución, punto 8)**:
  - Los nombres de fichero de las imágenes van en inglés y son iguales a la clave.
  - El nombre «Esquí» va en castellano, en NFC, en el catálogo de categorías.
  - La interfaz no añade textos.

## Casos límite
- La base de datos ya tiene `ski` con otro nombre (por ejemplo, «Nieve» o «esquí»): la migración no la duplica y le deja «Esquí» (RF-2).
- Otra categoría, con otra clave, se llama «esquí», «ESQUÍ» o «Esquí» en NFD (solo es posible saltándose las migraciones): la migración de Esquí falla entera, sin crear ni cambiar nada (RF-3). Si además existe `ski` con otro nombre, `ski` lo conserva.
- Se revierte la migración de Esquí sin bienes en ella: desaparece solo `ski`, y al volver a aplicarla se crea de nuevo (RF-1, RF-4).
- Se revierte la migración de Esquí con un bien de Esquí: falla, no se borra nada y la migración sigue aplicada. Ni el error ni el log contienen las coordenadas del bien (RF-4; 005, test de fugas).
- Se revierten las categorías hasta antes de la semilla, con un bien en Kayak y ninguno en Esquí:
  - la reversión de Esquí se completa y se confirma antes que la de la semilla: `ski` desaparece;
  - la de la semilla falla sin borrar ninguna de las once (005, RF-22): su migración sigue aplicada y el bien sigue existiendo;
  - quien vuelva a migrar recupera Esquí (RF-1).
- Se revierten las categorías hasta antes de la semilla con un bien en Esquí: falla ya la reversión de Esquí y no se borra nada (RF-4).
- La base de datos de desarrollo todavía no tiene aplicada la migración de Esquí: la lista pública de desarrollo no devuelve `ski` hasta que se aplica la migración, con la orden expresa del desarrollador.
- El comando de demostración se ejecuta cuando el propietario de demostración ya existe: no crea nada (006, RF-6), así que una demostración anterior no incluye el bien de Esquí hasta que se recrea la base de datos.
- Un cliente con una versión anterior de la interfaz recibe un bien `ski`: muestra la imagen de «Otros» y el nombre «Esquí» hasta que se recarga (RF-7).
- La lista pública trae una clave que el cliente no conoce (`snow`), vacía, `SKI`, `ski ` o `__proto__`: imagen de «Otros» (RF-7).
- Falla la descarga de una imagen en el navegador:
  - el hueco de 72 px queda vacío y la tarjeta no se descoloca;
  - al ser decorativa, no se muestra el icono de imagen rota;
  - la categoría sigue leyéndose en su nombre.

  No hay reintento ni respaldo (Fuera de alcance).
- Una imagen pesa menos que el umbral de incrustación: se sirve igualmente como fichero, no como `data:` (RF-8).
- Todas las imágenes pesan más que el umbral por defecto: el test de la guarda sigue fallando si se quita la guarda (RF-8, Seguridad).
- Una imagen pesa exactamente 16 384 bytes: se acepta. Con 16 385: se rechaza (RF-9).
- Un fichero `ski.webp` que en realidad es PNG, JPEG o SVG: se rechaza por la firma (RF-9).
- Un fichero de 0 bytes o truncado, con datos detrás del contenedor, con un tamaño de contenedor incorrecto o con un bloque que declara un tamaño de 0xFFFFFFFF: se rechaza (RF-9).
- Un WebP animado, aunque tenga un solo fotograma: se rechaza (RF-10).
- Un WebP con perfil de color, EXIF o XMP (por ejemplo, con las credenciales de contenido que puede añadir el generador), con un bloque desconocido o con dos bloques de imagen: se rechaza (RF-10). La marca de agua invisible en los píxeles no es un metadato y no se exige quitarla.
- Un WebP con ALPH junto a VP8L (con VP8X o sin él), con ALPH detrás de un VP8, con ALPH sin VP8X o con VP8X que no es el primer bloque: se rechaza (RF-10). Los decodificadores ignoran ese ALPH, así que serviría para esconder datos.
- Un WebP de 144 × 143, de 145 × 145, de 288 × 288 o de 1024 × 1024, o cuyo lienzo no coincide con la imagen codificada: se rechaza (RF-11).
- Un WebP sin transparencia (por ejemplo, opaco con fondo blanco, o un VP8 simple), o con la bandera de alfa activa pero sin bloque ALPH: se rechaza (RF-12).
- Un WebP con transparencia pero con las esquinas opacas: no cumple RF-13.
- Una imagen que conserva sombra o halo: no se aprueba y se regenera, sin retocarla a mano (RF-13).
- Sobra un fichero (`snow.webp`, `ski.png`, uno oculto o uno en una subcarpeta), falta uno o queda alguna imagen vectorial antigua: falla el test de RF-6.
- Un fichero se llama `Ski.webp` o `sports_area.webp`: no coincide con la clave y falla el test de RF-6.
- Un kayak guardado con la clave de la piragua: no se aprueba (RF-15).
- Kayak frente a piragua, y caravana frente a autocaravana y furgoneta: a 72 px y sin el nombre, cada imagen se distingue de su pareja; si no, no se aprueba (RF-15).
- Una imagen de pádel con el logo de una marca en la pala, un barco con un nombre pintado, una marca de agua visible o una persona esquiando: no se aprueba (RF-14).
- Pantalla de densidad 3 (muchos móviles): la imagen de 144 px se amplía a 216 píxeles físicos y pierde algo de nitidez. Se acepta (Fuera de alcance: varias densidades).
- El panel es de cristal sobre el mapa o es sólido (016, RF-9): el fondo transparente deja ver la superficie en los dos casos, sin recuadro (RF-13).

## Fuera de alcance
- Fotos reales de los bienes (spec 010).
- Portada, teselas y chips de categoría (spec 008), y cualquier otro uso de las imágenes de categoría fuera de la tarjeta del panel.
- Versiones por densidad (1×, 3×), elegir la versión según la pantalla, AVIF y otros formatos y tamaños.
- Reintentar la descarga o mostrar una imagen de respaldo si falla, y texto alternativo: la imagen sigue siendo decorativa.
- Relieve o sombra de las imágenes. Si se quiere más adelante, se hará con estilos e igual para las doce.
- Retocar las imágenes a mano.
- Traducir los nombres de categoría.
- Crear, editar o borrar categorías en ejecución. Elegir categoría al publicar y mostrar al anunciante el criterio de Esquí (spec 010).
- Otras categorías nuevas (raquetas, trineos, motos de nieve, una categoría «Nieve» genérica).
- Herramientas o scripts de preparación de imágenes dentro del repositorio.
- Renombrar o modificar `~/RentRadar-recursos/categorias/`, sus originales o su ficha de fuentes.
- Cambiar las reglas de la lista blanca de SVG o el test del icono de la 016.
- Que el comando de demostración rehaga o complete una demostración que ya existe.
- Recrear la base de datos de desarrollo o aplicarle migraciones sin la orden expresa del desarrollador en ese momento, o cambiar sus datos por SQL o por consola.
- La política de seguridad de contenido en sí (spec 011).
- Conservar o volver a firmar las credenciales de contenido de las imágenes.

## Cambios en otras specs
- **004, RF-19 a RF-22**: no requieren `/sdd-change`. La semilla sigue siendo de once y no se modifica, y su test no cambia. Esquí llega en una migración de datos propia (RF-1 a RF-4). Se sigue cumpliendo que las categorías solo cambian por migración.
- **005, RF-22**: no requiere `/sdd-change`, y su texto no cambia. Su protección se aplica también a la reversión de Esquí (RF-4). En una reversión hasta antes de la semilla, la de Esquí se completa antes y `ski` desaparece; la de la semilla sigue fallando sin borrar ninguna de sus once (Casos límite). Los tests afectados se recogen en los Criterios de finalización.
- **006, definición de tarjeta**: no requiere `/sdd-change` (imagen genérica y decorativa; la de «Otros» si la categoría es desconocida). RF-7 la conserva.
- **006, RF-6**: no requiere `/sdd-change` y su texto no cambia: 25 bienes, 24 activos, 1 pausado y al menos uno por categoría de la semilla. La comprobación de punta a punta de la 006 sigue esperando 24 tarjetas. Esta spec solo sustituye una furgoneta por el bien de Esquí y fija los invariantes en RF-5.
- **006, plan y validación**:
  - la decisión de imágenes de categoría vectoriales con lista blanca queda sustituida por esta spec;
  - se conserva la decisión de servirlas como ficheros, que aquí pasa a ser RF-8 con su test;
  - la validación de la 006 es un registro histórico y no se edita.
- **016 (implementada), «Fuera de alcance»**:
  - dice que la lista blanca de las imágenes de categoría y lo que comprueba su test «se mantienen tal cual», y deja a la 008 rehacer las imágenes;
  - al cerrar esta spec, la 016 recibe en ese punto una nota de una línea, «sustituido por la 017», sin `/sdd-change`.
- **016, lista blanca de SVG y RF-14**:
  - sus reglas no cambian;
  - desde esta spec solo las usa el test del icono de RentRadar, y desaparece el test que las aplicaba a las imágenes de categoría;
  - RF-14 de la 016 se sigue cumpliendo igual.
- **016, identidad visual**:
  - la decisión sobre los amarillos de las imágenes, que la 016 dejaba a la 008, la toma esta spec (Identidad visual);
  - la imagen de categoría de referencia de los prototipos de la 016 deja de ser el punto de partida.

## Criterios de finalización
- **Tests y verificaciones**: cada RF tiene un test automático o una verificación registrada en la validación.
  - pytest:
    - RF-1: `ski` existe tras migrar, con el nombre «Esquí», pasa el servicio de validación de categorías, y la clave y el nombre de las once de la semilla no cambian;
    - RF-2: reaplicar con `ski` borrada y con `ski` con otro nombre, y aplicar dos veces;
    - RF-3: con otra categoría que ya se llama «esquí», la migración falla y no se crea ni se cambia ninguna categoría;
    - RF-4, sin bienes: revertir con una categoría ajena, que se conserva;
    - RF-4, con un bien de Esquí: revertir solo la migración de Esquí falla sin borrar nada y la migración sigue aplicada. El rechazo lo da la protección de la 005. Este caso se añade al test de fugas de la 005: ni el error ni el log contienen las coordenadas;
    - RF-5: datos y comando de demostración, con todos sus invariantes. Las categorías de la demostración pasan de «las de la semilla» a «las de la semilla y `ski`».
  - Tests existentes que cambian:
    - los que cuentan todas las categorías esperan doce: el del borrado de una categoría con bienes, el de la reversión de las categorías dentro de una transacción revertida y el de fugas de la 005;
    - los que revierten hasta antes de la semilla con un bien ya no pueden afirmar que no se borra nada. Se reescriben para afirmar que `ski` desaparece, que las once siguen, que la migración de la semilla sigue aplicada y que el bien sigue existiendo;
    - el test de la semilla de la 004 no cambia.
  - vitest:
    - RF-6: la lista de doce claves, escrita a mano en el test, coincide en los dos sentidos con el contenido real de las imágenes de categoría, incluidos los ficheros ocultos, los de otro formato y las subcarpetas;
    - RF-7: cada una de las doce claves da su propia imagen, y las claves desconocidas y hostiles dan la de «Otros»;
    - RF-8: el test de la guarda contra la incrustación, con su control positivo (Seguridad);
    - RF-9 a RF-12: las doce imágenes reales pasan. Los casos negativos se fabrican en el propio test; no se versionan ficheros hostiles. Son estos:
      - otro formato con extensión `.webp` (PNG, JPEG y SVG);
      - animado;
      - 144 × 143, 145 × 145, 288 × 288 y 1024 × 1024;
      - sin alfa, y con la bandera de alfa pero sin ALPH;
      - con EXIF, con XMP, con perfil de color y con un bloque desconocido;
      - 16 385 bytes;
      - datos detrás del contenedor y tamaño de contenedor incorrecto;
      - lienzo distinto de la imagen codificada;
      - dos bloques de imagen;
      - VP8L con ALPH (con VP8X y sin él), ALPH detrás de un VP8, ALPH sin VP8X y VP8X que no es el primer bloque;
      - fichero truncado y fichero de 0 bytes;
      - un bloque con tamaño 0xFFFFFFFF.
  - Compilación: ninguna imagen de categoría sale como `data:` en el código ni en los estilos, y las doce salen como ficheros WebP del propio sitio (RF-8).
  - Navegador, para RF-13: en cada una de las doce imágenes se lee la opacidad de los cuadrados de 8 × 8 px de las cuatro esquinas, y el resultado queda registrado en la validación. Riesgo aceptado: no hay test automático de las esquinas, porque necesitaría un decodificador de WebP, que es una dependencia nueva.
  - Hoja de revisión: RF-13 (sin sombra, halo ni restos), RF-14 y RF-15, incluida la asignación de cada imagen a su clave. Se aprueban imagen por imagen, con una línea por imagen y su fecha en la validación.
- **Pruebas de mecanismo**: solo para lo que toca seguridad o privacidad. Cada mutación se hace sobre una copia y después se restaura.
  - RF-8: quitar la guarda contra la incrustación hace fallar su test, también con todas las imágenes por encima del umbral por defecto;
  - RF-9 y RF-10: sacar EXIF, XMP o el perfil de color de lo que se rechaza, admitir bloques desconocidos, admitir ALPH junto a VP8L e ignorar los datos detrás del contenedor hacen fallar sus tests.
- **Procedencia**: una línea en la validación (Definiciones). Los originales, su ficha de fuentes y la hoja de revisión no están en el repositorio.
- **Sin restos**:
  - no queda ninguna imagen de categoría vectorial ni ningún test que aplique la lista blanca de SVG a las imágenes de categoría;
  - las reglas de la lista blanca solo las usa el test del icono, que sigue en verde;
  - los manifiestos de dependencias no cambian;
  - la documentación de arquitectura deja de describir las imágenes de categoría como ilustraciones SVG.
- **Base de datos de desarrollo**: para que la demostración incluya el bien de Esquí, durante la validación la base de datos de desarrollo se recrea, se le aplican las migraciones y se ejecuta el comando de demostración. Cada uno de esos pasos, y levantar, parar o reiniciar el stack, necesita la orden expresa del desarrollador en ese momento, como fijan los límites del proyecto. Nunca se hace por SQL. Recrearla borra todo lo que contiene, también las cuentas de prueba de otras specs.
- **Punta a punta**: con la interfaz y la API levantadas, la lista pública devuelve, en una petición real vista desde el navegador, un bien con clave `ski` y nombre «Esquí», y su tarjeta muestra la imagen de Esquí.
- **Navegador**, a 375 y a 1280 px, con la consola sin errores propios de la aplicación:
  - el panel muestra tarjetas de las doce categorías, cada una con su imagen: nítida, sin deformar y con el fondo transparente sobre el cristal del panel y sobre la superficie sólida;
  - las imágenes se piden al propio origen como ficheros y ninguna es `data:`;
  - con la petición de una imagen bloqueada, no aparece el icono de imagen rota y la tarjeta no se desplaza;
  - sin desbordamiento horizontal.
- **Cierre**: las doce imágenes están en el producto, aprobadas una a una. Sin las doce aprobadas, la spec no se cierra. Antes del cierre, el desarrollador ha comprobado que los términos de uso de la herramienta permiten el uso comercial (Procedencia).
- pytest, ruff, vitest, build y eslint de los ficheros tocados, en verde.
- Al cerrar: la 016 tiene la nota de una línea de «Cambios en otras specs», y MEMORY.md está actualizado, incluida la línea de la 008 en la hoja de ruta.

## Dudas abiertas
Ninguna.
