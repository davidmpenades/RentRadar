# Spec 008 — Búsqueda y filtros por categoría en el mapa
Estado: aprobada
Depende de: spec 006 (lista pública, mapa y panel), spec 016 (identidad visual: el limón está reservado) y spec 017 (nombres e imágenes de categoría). Recoge la nota de rendimiento de la spec 018 sobre la consulta de la lista pública.

## Contexto y objetivo
Hoy el visitante ve en el mapa todos los bienes de la zona y no puede acotarlos. La lista pública de la spec 006 ignora cualquier parámetro de categoría o de texto. Esta spec entrega la primera búsqueda, de la base de datos a la pantalla: el visitante elige una categoría con un chip o escribe en el buscador «Qué», y el panel y los círculos muestran solo los bienes que coinciden.

Incluye:
- el filtro por categoría y el filtro por texto en la lista pública, con su validación y sus errores;
- la medición del rendimiento de la consulta de la lista antes de cambiarla;
- los chips de categoría sobre el mapa y el buscador «Qué»;
- los estados de la interfaz con filtros: filtro activo, sin resultados y error;
- la estructura de encabezados de la pantalla del mapa.

La portada, las teselas de categorías y la barra inferior con «Publicar» no entran aquí: pasan a la spec de fotos (ver Fuera de alcance). La interacción entre la lista y el mapa sigue siendo de la spec 007, y el campo «Dónde» y la búsqueda por municipio, de la spec 012.

## Usuarios
- **Visitante**: cualquier persona que abre RentRadar, con o sin sesión. Todos reciben los mismos resultados.
- **Anunciante**: propietario de bienes. Aquí solo le afecta que ningún filtro revele datos que la lista pública no muestra.
- **Desarrollador del equipo**: comprueba el rendimiento de la consulta y los tests de privacidad.

## Historias de usuario
- HU-1. Como visitante, quiero elegir una categoría sobre el mapa, para ver solo los bienes de ese tipo.
- HU-2. Como visitante, quiero escribir qué busco, para encontrar un bien por su título sin recorrer toda la lista.
- HU-3. Como visitante, quiero ver qué filtros están activos y quitarlos con un gesto, para no quedarme en una pantalla vacía sin saber por qué.
- HU-4. Como anunciante, quiero que buscar por texto o por categoría nunca revele mi ubicación exacta ni mis bienes pausados, para proteger mi privacidad.
- HU-5. Como desarrollador, quiero medir la consulta de la lista antes de cambiarla, para que añadir filtros no degrade la respuesta cuando haya volumen.
- HU-6. Como visitante que usa un lector de pantalla, quiero que la pantalla del mapa tenga encabezados, para orientarme y saltar entre sus partes.

## Definiciones
- **Filtro de categoría**: restricción de la lista a los bienes de una sola categoría, identificada por el mismo identificador de categoría que la lista ya devuelve en cada bien.
- **Filtro de texto**: restricción de la lista a los bienes cuyo título contiene el texto como fragmento, sin distinguir mayúsculas ni tildes. Solo cuenta el título: nunca el nombre de la categoría.
- **Texto buscado**: el que escribe el visitante, recortado por los extremos. Cómo se consigue la comparación sin mayúsculas ni tildes en la base de datos lo decide el plan.
- **Filtro activo**: filtro de categoría o de texto que el visitante ha aplicado y que sigue en vigor.
- **Chip de categoría**: control del mapa que representa una categoría y activa o quita su filtro.
- **Buscador «Qué»**: campo de texto del mapa donde el visitante escribe el filtro de texto.
- **Datos que la lista ya muestra**: los campos que la spec 006 permite devolver de cada bien (RF-2 de esa spec). Ningún filtro mira nada fuera de ellos.
- **Formato del identificador de categoría**: una o más secuencias de letras minúsculas ASCII o dígitos separadas por un guion simple, sin guion al principio ni al final y sin guiones dobles.
- Los términos **bien visible**, **zona**, **cuadro pedido**, **lista incompleta**, **panel de resultados**, **tarjeta**, **zona de contenido** y **vista inicial** son los de la spec 006.

### Valores de esta spec
| Valor | Fijado |
|---|---|
| Longitud máxima del texto | 64 caracteres, contados después de recortarlo |
| Longitud máxima del identificador de categoría | 50 caracteres |
| Duración de la caché de una respuesta correcta | la de la spec 006 (60 s, pública), también con filtros |
| Límite de peticiones por IP | el de la spec 006, compartido con las peticiones con filtros |

Los demás números los fija el plan: el tiempo de espera del buscador tras dejar de escribir, el umbral de rendimiento de la consulta y el volumen sintético de la medición.

## Requisitos funcionales

### Filtros de la lista pública
- RF-1: CUANDO un visitante pide la lista pública con un identificador de categoría válido, EL SISTEMA devuelve solo los bienes que la lista devolvería sin filtro y que pertenecen a esa categoría.
- RF-2: CUANDO un visitante pide la lista pública con un texto válido, EL SISTEMA devuelve solo los bienes que la lista devolvería sin filtro y cuyo título contiene el texto buscado como fragmento, sin distinguir mayúsculas ni tildes. La coincidencia se calcula solo con el título: nunca con el nombre de la categoría, con la descripción, con datos del propietario ni con la ubicación, exacta o pública. Los caracteres comodín de la base de datos y los de las expresiones regulares valen como texto literal.
- RF-3: SI el identificador de categoría o el texto no es válido, ENTONCES EL SISTEMA responde con un error de entrada, sin consultar los bienes. El texto se recorta por los extremos antes de validarlo. Son inválidos:
  - un parámetro que llega más de una vez o vacío; que un parámetro vacío sea un error es una regla propia de esta spec;
  - un texto que queda vacío al recortarlo, por ejemplo uno de solo espacios, que da el mismo error que un parámetro vacío;
  - un identificador de categoría de más de 50 caracteres o que no tiene el formato del identificador de categoría;
  - un texto recortado de más de 64 caracteres o con caracteres de control.

  El error usa el formato único de la spec 006, con un código estable por cada parámetro que falla, en inglés, y sin incluir nunca el valor recibido. Si fallan a la vez un límite de la zona y un filtro, el error trae los códigos de todos.
- RF-4: SI el identificador de categoría es válido pero no corresponde a ninguna categoría, ENTONCES EL SISTEMA devuelve una lista vacía y no un error, para que un chip antiguo no rompa la pantalla.
- RF-5: EL SISTEMA aplica los filtros sin cambiar nada más de la respuesta de la spec 006: los mismos campos por bien, el mismo orden, el tope de 200 bienes (que se aplica ya con el filtro puesto, y la lista es incompleta si hay más de 200 bienes que cumplen), la ausencia de totales, la caché pública de 60 s en la respuesta correcta, `no-store` en los errores, la respuesta idéntica para cualquier visitante y el límite de peticiones por IP.
- RF-6: CUANDO llegan a la vez un identificador de categoría válido y un texto válido, EL SISTEMA devuelve solo los bienes que cumplen los dos filtros (Y). Los filtros siempre actúan dentro del cuadro pedido: ni el texto ni la categoría buscan nunca fuera de la zona.

### Interfaz del mapa
- RF-7: EL SISTEMA muestra sobre el mapa una fila de chips de categoría, uno por cada categoría, y el buscador «Qué». La fila se puede recorrer entera con teclado y con lector de pantalla a 375 px, aunque no quepan todos los chips en el ancho. Los controles no tapan la atribución del mapa base ni los controles de zoom.
- RF-8: CUANDO el visitante activa un chip, EL SISTEMA marca el chip como activo, pide la lista con esa categoría y limita el panel y los círculos a los bienes de la respuesta. CUANDO activa el chip que ya está activo, quita el filtro y vuelve a pedir la lista sin él. Solo puede haber una categoría activa a la vez: activar otro chip sustituye al anterior. Cada cambio cancela la petición anterior sin terminar y nunca se muestra su respuesta.
- RF-9: CUANDO el visitante escribe en el buscador «Qué» y el campo lleva quieto el tiempo de espera, o pulsa Intro, EL SISTEMA pide la lista con ese texto, con las mismas reglas de cancelación que RF-8. Borrar el texto quita el filtro de texto. El campo no admite más de 64 caracteres.
- RF-10: MIENTRAS haya algún filtro activo, EL SISTEMA lo muestra de forma visible (el chip activo y el texto escrito) y ofrece un control «Quitar filtros» que los quita todos a la vez y vuelve a pedir la lista.
- RF-11: CUANDO una respuesta válida con algún filtro activo no deja ninguna tarjeta, EL SISTEMA muestra en el panel «No hay bienes en esta zona con estos filtros» y el botón «Quitar filtros», y lo anuncia. El estado vacío sin filtros y el botón «Volver a la zona inicial» siguen siendo los de la spec 006.
- RF-12: SI falla la petición de bienes con algún filtro activo, ENTONCES EL SISTEMA muestra el mensaje de error de la spec 006 con «Reintentar», y «Reintentar» repite la petición con los mismos filtros. Los filtros activos no se pierden por un error.
- RF-13: EL SISTEMA da a la pantalla del mapa un único encabezado principal (nivel 1), oculto visualmente pero disponible para el lector de pantalla, y muestra el título del panel como encabezado de segundo nivel.

## Requisitos no funcionales
- **Permisos (constitución, punto 5)**:
  - Los filtros no cambian los permisos de la lista pública: el anónimo, el usuario con sesión, el propietario y el staff reciben los mismos resultados.
  - Ningún filtro hace aparecer un bien pausado ni de una cuenta desactivada, ni siquiera para su propietario, ni una ubicación exacta.
  - No hay vista de detalle, así que no hay caso de 404 ni de 403 por objeto.
- **Privacidad**:
  - El filtro de texto solo mira el título, uno de los datos que la lista ya muestra. Buscar un texto no puede servir para averiguar la descripción, el propietario ni la ubicación exacta de un bien.
  - Los tests de fugas de la ubicación pública de las specs 005 y 006 siguen pasando sin modificarse y se repiten con cada filtro activo. La lectura pública con filtros tampoco carga la ubicación exacta.
  - El texto y la categoría que elige el visitante no van a la dirección de la página ni al almacenamiento del navegador: recargar la página los quita. Sí viajan en la petición a la API.
  - Ni los logs de la aplicación ni los errores incluyen el texto escrito. En desarrollo se acepta que el log de accesos lo guarde junto con la IP del visitante; su retención se decide en la spec 011.
- **Rendimiento**:
  - Antes de cambiar la consulta de la lista, se mide su plan de ejecución en la base de datos de test con decenas de miles de filas sintéticas. La consulta de la zona compara coordenadas calculadas a partir de la ubicación pública y hoy no aprovecha el índice espacial; la medición dice si los filtros agravan ese problema.
  - Se mide sin filtro, con filtro de categoría y con filtro de texto, antes y después de cambiar la consulta. Las tres mediciones quedan registradas en validation.md.
  - La consulta sin filtro no empeora respecto a la medición inicial. El umbral para las consultas con filtro lo fija el plan a partir de esa medición.
- **Caché**: una respuesta correcta con filtros se cachea 60 s como la de la spec 006. Variar el texto o la categoría produce peticiones distintas que cuentan para el límite por IP.
- **Desconfianza de la entrada (constitución, punto 6)**:
  - El backend valida tipo, rango y tamaño de ambos parámetros (RF-3). Los parámetros desconocidos se ignoran, como en la spec 006.
  - El texto nunca se interpreta: ni como fragmento de consulta, ni como patrón, ni como marcado.
  - El cliente sigue validando la forma de toda respuesta antes de usarla; los filtros no añaden campos a la respuesta.
- **Errores de la lista pública**: los códigos nuevos usan el formato único de la spec 006, son estables y están en inglés. El cliente los traduce.
- **Contrato**: el contrato de la API cambia al añadir los dos parámetros opcionales. La descripción legible por máquina y los tipos del cliente se regeneran, y el control de desfase de la spec 006 sigue en verde.
- **Dependencias (constitución, punto 1)**: esta spec no añade ninguna. Si el plan necesita alguna, también una extensión de la base de datos, requiere aprobación expresa.
- **Accesibilidad y móvil (constitución, punto 7)**:
  - Se diseña a 375 px y se amplía a 1280 px. Los chips, el buscador, su control para borrar y «Quitar filtros» miden al menos 44 px.
  - El chip activo se distingue sin depender solo del color y lo anuncia el lector de pantalla como activado. El estado activo usa el azul de la identidad visual y nunca el limón, que está reservado para la selección de la spec 007. El contraste es AA.
  - El buscador tiene una etiqueta accesible «Qué». Todo se usa con teclado y el foco es visible.
  - La región de estado de la spec 006 anuncia, una vez por petición, el número de resultados con filtros, el vacío con filtros y los errores.
  - Si el visitante pide reducir el movimiento, no hay animaciones.
- **Idioma (constitución, punto 8)**: los textos nuevos están en castellano y salen del catálogo de mensajes. Los códigos y los identificadores van en inglés.

## Casos límite
- Categoría válida sin ningún bien en la zona: lista vacía y estado vacío con filtros (RF-1, RF-11).
- Identificador de categoría con el formato correcto que no existe: lista vacía, no error (RF-4).
- Identificador de categoría con mayúsculas, de 51 caracteres, vacío o repetido: error (RF-3).
- Identificador `-ski`, `ski-` o `sports--area`: error, por guion al principio, al final o doble (RF-3). `sports-area` es válido.
- Texto de 64 caracteres: se acepta. De 65: error. Con espacios por los extremos, cuenta el texto recortado: 64 caracteres rodeados de espacios se aceptan (RF-3).
- Texto con un carácter de control: error (RF-3).
- Texto vacío o de solo espacios: error, igual que un parámetro vacío (RF-3).
- Texto con espacios por los extremos: se recorta y se busca el texto recortado (RF-2).
- Texto con `%`, `_`, `\`, `.*` o comillas: se busca como texto literal y solo coincide con títulos que los contengan (RF-2).
- El texto es una coordenada o parte de una descripción: no coincide con nada por esa vía, porque solo se compara el título (RF-2, Privacidad).
- El texto es el nombre de una categoría, por ejemplo «Kayak»: solo coincide con los bienes cuyo título lo contiene, no con los de esa categoría (RF-2).
- «esqui» encuentra un bien titulado «Esquí»; «BICI» encuentra uno titulado «bicicleta»; «ESQUÍ» también encuentra «esqui» (RF-2).
- El texto coincide con el título de un bien pausado o de una cuenta desactivada: no aparece (Permisos).
- Hay más de 200 bienes que cumplen el filtro en el cuadro pedido: se devuelven los 200 más recientes y la lista es incompleta (RF-5).
- Hay un bien que coincide con el texto pero está fuera del cuadro pedido: no aparece, y el texto nunca amplía la zona (RF-6).
- Hay filtro activo y el cuadro pedido es demasiado grande: no se pide nada y se mantiene «Acerca el mapa para ver los bienes» (spec 006); los filtros siguen activos.
- El visitante mueve o acerca el mapa con un filtro activo: el filtro se mantiene y se pide el nuevo cuadro con él.
- El visitante activa varios chips seguidos o escribe deprisa: solo se muestra la respuesta de la última petición (RF-8, RF-9).
- El visitante activa un chip y escribe un texto: se piden los dos filtros a la vez y el panel muestra solo los bienes de esa categoría cuyo título contiene el texto, dentro del cuadro pedido (RF-6).
- El visitante pulsa «Volver a la zona inicial» con un filtro activo: el mapa vuelve a la vista inicial y los filtros se mantienen (RF-10).
- El visitante recarga la página o vuelve con «Atrás» desde otra página: no hay filtros activos (Privacidad).
- Falla la red o el servidor con un filtro activo: mensaje de error, «Reintentar» con los mismos filtros (RF-12). Si la respuesta es inválida, se trata como en la spec 006.
- Llega un HEAD, un OPTIONS o un método de escritura con parámetros de filtro: mismo comportamiento que sin ellos (spec 006, Permisos).
- Llegan la misma petición con filtros con y sin cookie de sesión: la respuesta es la misma y no se declara variable por `Cookie` (RF-5).
- Llega la petición 61 en un minuto con filtros: error de límite superado, sin validar los filtros (RF-5).
- Una categoría nueva se añade en la base de datos y el cliente no la conoce: [NECESITA ACLARACIÓN] para el plan, según de dónde salgan los chips (Dudas abiertas, plan).

## Fuera de alcance
- Portada, teselas de categorías y barra inferior de navegación en móvil con el botón «Publicar»: pasan a la spec de fotos, que también necesita la portada y las fotos de registro y de entrada.
- Interacción entre la lista y el mapa: agrupación, selección en las dos direcciones, filtrar el panel por círculo y alturas del panel (spec 007). La selección usa el limón; los chips no.
- Campo «Dónde», búsqueda por municipio (spec 012), «Cerca de mí» y geolocalización.
- Buscar fuera de la zona del mapa.
- Elegir varias categorías a la vez.
- Buscar en el nombre de la categoría, en la descripción, en el propietario o en cualquier dato que no sea el título.
- Autocompletado, sugerencias, corrección de erratas, relevancia, resaltado de coincidencias y ordenación distinta de la de la spec 006.
- Filtros por precio, por unidad de precio, por radio, por fechas o por disponibilidad.
- Compartir o recordar los filtros con un enlace, con el historial o con el almacenamiento del navegador.
- Paginación más allá del tope y recuentos por categoría.
- Detalle de un bien, contacto y reservas.
- Índices, motores de búsqueda externos y cualquier otra solución de infraestructura: si la medición lo pide, lo decide el plan y, si añade una dependencia, necesita aprobación expresa.

## Riesgos propuestos para aceptar
- El texto que escribe el visitante viaja en la dirección de la petición y puede quedar en el log de accesos del servidor, con su IP. En desarrollo se acepta; la retención se decide en la spec 011 y la política de privacidad deberá mencionarlo antes de abrir a usuarios reales.
- Probando textos distintos dentro del límite de peticiones se pueden averiguar los títulos de los bienes activos. Los títulos son públicos por diseño.
- Cada variante del texto es una petición distinta que no aprovecha la caché y gasta el límite por IP. Quien comparta IP (NAT) lo notará antes.
- Un filtro sin resultados en una zona con lista incompleta puede ocultar bienes que sí existen fuera del cuadro pedido; el visitante lo resuelve moviendo el mapa o quitando filtros.

## Criterios de finalización
- Cada RF tiene un test automático o una verificación en navegador registrada en validation.md:
  - pytest para RF-1 a RF-6;
  - vitest para las funciones puras de RF-7 a RF-12: estado de los filtros, conversión del estado a parámetros, elección del estado vacío con o sin filtros y textos de la cabecera y de los avisos;
  - RF-7 a RF-13 se verifican en el navegador.
- Tests de privacidad y seguridad, con prueba de mecanismo:
  - los tests de fugas de las specs 005 y 006 pasan sin cambios y se repiten con cada filtro activo, también con el texto igual al de una descripción, al de un propietario, al de una coordenada o al del nombre de una categoría;
  - un bien pausado y un bien de una cuenta desactivada no aparecen con ningún filtro, tampoco para su propietario;
  - la lectura con filtros no carga la ubicación exacta;
  - los errores no contienen el texto ni el identificador recibidos, y los logs de la aplicación no incluyen el texto;
  - el límite de peticiones se aplica antes de validar los filtros.
- Tests de validación de entrada:
  - parámetro repetido, vacío, texto de solo espacios (mismo error que el vacío), texto de más de 64 caracteres tras recortarlo, de 64 rodeados de espacios (válido), con caracteres de control, e identificador de más de 50 caracteres o con mayúsculas;
  - identificadores `-ski`, `ski-` y `sports--area` rechazados, y `sports-area` y `ski` aceptados;
  - texto con caracteres comodín tratado como literal (RF-2, RF-3).
- Tests de comparación del texto (RF-2):
  - «esqui» encuentra un bien titulado «Esquí» y «BICI» uno titulado «bicicleta»;
  - mayúsculas y tildes distintas en los dos sentidos, y fragmento al principio, en medio y al final del título;
  - un texto que solo coincide con el nombre de la categoría, con la descripción o con el propietario no encuentra nada.
- Tests de combinación (RF-6):
  - categoría y texto a la vez devuelven solo los bienes que cumplen los dos;
  - un bien que coincide con el texto pero está fuera del cuadro pedido no aparece, con y sin filtro de categoría.
- Un test comprueba que la respuesta con filtros mantiene los mismos campos, el mismo orden, el tope, la marca de lista incompleta, la caché pública de 60 s y `no-store` en los errores (RF-5).
- Medición del rendimiento de la consulta, antes y después, sin filtro, con categoría y con texto, registrada en validation.md antes de dar la funcionalidad por cerrada (Rendimiento).
- El control de desfase entre la descripción de la API y los tipos generados está en verde (Contrato).
- Comprobación de punta a punta con el comando de demostración: en la vista inicial, activar el chip de una categoría deja en el panel solo sus tarjetas y en el mapa solo sus círculos; escribir parte del título de un bien lo encuentra; «Quitar filtros» devuelve las 24 tarjetas (RF-1, RF-2, RF-8 a RF-10).
- Verificación en navegador con Chrome DevTools a 375 y 1280 px, registrada en validation.md:
  - chips visibles y recorribles, estado activo distinguible sin depender del color, buscador, filtro activo visible, «Quitar filtros», vacío con filtros y error con filtros y «Reintentar» (simulado);
  - estructura de encabezados en el árbol de accesibilidad: un solo encabezado de nivel 1, oculto visualmente pero presente para el lector de pantalla, y el título del panel como encabezado de nivel 2 (RF-13);
  - recorrido solo con teclado de chips, buscador y botones, anuncios de la región de estado y consola sin errores;
  - controles de al menos 44 px y ningún uso del limón;
  - la dirección de la página no cambia al filtrar y nada se guarda en el almacenamiento del navegador;
  - la red sigue yendo solo al propio origen y al proveedor del mapa base.
- pytest, ruff, vitest, build y eslint en verde.

## Aclaraciones
Clarify del 24-11-2026:
- El encabezado principal oculto de la pantalla del mapa y el título del panel como encabezado de segundo nivel entran en esta spec (RF-13).
- El texto se compara por fragmento del título, sin distinguir mayúsculas ni tildes; cómo se consigue en la base de datos lo decide el plan (RF-2, Definiciones, Casos límite).
- Categoría y texto se combinan con Y y siempre dentro del cuadro pedido; el texto nunca busca fuera de la zona (RF-6).
- El texto busca solo en el título, nunca en el nombre de la categoría (RF-2, Fuera de alcance).

## Dudas abiertas
Las resuelve el plan:
- Nombre de los parámetros de la API y códigos de error nuevos.
- Qué caracteres cuentan como espacio en blanco al recortar el texto, y cómo se compara sin tildes (por ejemplo, si la ñ cuenta como una letra distinta de la n).
- De dónde salen los chips (lista fija en el cliente o consulta a la API) y qué hace el cliente con una categoría que no conoce.
- Si el chip lleva la imagen de la categoría o solo su nombre.
- Tiempo de espera del buscador, umbral de rendimiento y volumen sintético de la medición.
- Qué cambia en la consulta si la medición lo exige.
- Disposición de los chips y del buscador a 375 px sin tapar la atribución ni el zoom.
- Qué texto llevan el encabezado principal oculto y el título del panel, y qué encabezados quedan cuando falla el estilo del mapa base.
