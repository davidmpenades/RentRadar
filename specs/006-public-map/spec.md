# Spec 006 — Mapa público
Estado: aprobada
Depende de: spec 001 (entornos; la depuración nunca está activa en producción), spec 004 (usuarios, alta con contraseña obligatoria y semilla de categorías) y spec 005 (bienes, servicio de escritura de bienes y "Reglas para specs posteriores").

## Contexto y objetivo
RentRadar ya guarda bienes con una ubicación exacta privada y una ubicación pública aproximada, pero nadie puede verlos. Esta spec entrega la primera funcionalidad visible, de la base de datos a la pantalla. Un visitante sin cuenta abre RentRadar y explora en un mapa los bienes activos. De cada bien ve solo la zona aproximada, dibujada como un círculo.

Incluye:
- la primera lectura pública de la API y las reglas comunes de toda la API pública (formato de errores, descripción legible por máquina, mismo origen);
- un identificador público para cada bien, con la migración que se lo asigna a los bienes ya creados en la spec 005;
- la creación de la interfaz web en `frontend/`, con Vite, vitest y eslint, y su identidad visual;
- un comando de desarrollo que crea bienes de demostración.

La portada y la búsqueda llegan en la spec 007.

## Usuarios
- **Visitante**: cualquier persona que abre RentRadar. En esta spec no hay inicio de sesión, así que todos los visitantes son anónimos.
- **Anunciante**: propietario de bienes. Aquí solo le afecta la privacidad de lo que se publica.
- **Desarrollador del equipo**: llena la base de datos de desarrollo con bienes de demostración y ejecuta los tests.

## Historias de usuario
- HU-1. Como visitante, quiero abrir RentRadar y ver en un mapa los bienes en alquiler de la zona, para saber qué hay sin registrarme.
- HU-2. Como visitante, quiero mover y acercar el mapa y que la lista se actualice con lo que veo, para explorar otras zonas.
- HU-3. Como visitante, quiero pulsar un bien de la lista y ver su zona en el mapa, o tocar una zona del mapa y ver sus bienes en la lista, para relacionar ambas cosas.
- HU-4. Como visitante en el móvil, quiero plegar o desplegar la lista, para elegir entre ver más mapa o más bienes.
- HU-5. Como anunciante, quiero que el mapa público muestre solo la zona aproximada de mis bienes activos y ningún dato mío, para proteger mi privacidad.
- HU-6. Como desarrollador, quiero un comando que cree bienes de demostración, para probar el mapa en el navegador con datos realistas.

## Definiciones
- **Zona**: rectángulo definido por cuatro límites en grados decimales WGS84: sur, oeste, norte y este. Un punto está **dentro** si sur ≤ latitud ≤ norte y oeste ≤ longitud ≤ este. Se comparan coordenadas, no distancias geodésicas, y los bordes cuentan como dentro.
- **Área de la zona**: (este − oeste) × (norte − sur), en grados cuadrados. El servidor la calcula con aritmética decimal exacta.
- **Bien visible**: bien en estado `active`, cuyo propietario tiene la cuenta activa y cuya ubicación pública está dentro de la zona.
- **Zona visible**: la zona que ocupa el mapa en pantalla, incluida la parte que tapa el panel.
- **Cuadro pedido**: la zona visible ampliada 2 km por cada lado (el radio de privacidad máximo) y redondeada hacia fuera a una cuadrícula fija de latitud y longitud cuyo paso fija el plan. Los 2 km se pasan a grados de longitud con la latitud de la zona más alejada del ecuador, para que la ampliación cubra al menos 2 km en todo el cuadro. Ni la latitud ni la longitud se recortan: si el cuadro sale de −85…85 de latitud o de −180…180 de longitud, el cliente no pide (RF-14). El servidor sigue aceptando latitudes de −90 a 90. Mientras el mapa se mueve dentro del mismo cuadro, las peticiones son idénticas y pueden servirse desde la caché.
- **Lista incompleta**: respuesta que no incluye todos los bienes visibles del cuadro pedido porque se ha alcanzado el tope.
- **Círculo de un bien**: círculo centrado en la ubicación pública con un radio igual al radio de privacidad, medido sobre el terreno.
- **Grupo**: burbuja con el número de bienes que sustituye a varios círculos cercanos cuando el zoom es bajo.
- **Página del mapa**: página propia de RentRadar, con la dirección definitiva `/map`. Desde la 006 vive en esa dirección; la raíz redirige a ella sin añadir una entrada al historial.
- **Vista inicial**: centro en 39,4699 N y 0,3763 O (Valencia) con zoom 11. En esa zona crea sus bienes el comando de demostración.
- **Mapa base**: el estilo "positron" de OpenFreeMap, con su estilo, sus teselas, sus glifos y sus sprites, sin recolorear.
- **Panel de resultados**: lista de bienes que acompaña al mapa.
  - Por debajo de 900 px de ancho ocupa la parte inferior y tiene tres alturas: plegado (muestra solo la cabecera y el aviso), medio y desplegado.
  - Desde 900 px es una columna fija a la izquierda, con todo el alto disponible y sin alturas.
- **Tarjeta**: botón con los datos de un bien: imagen genérica de su categoría (decorativa, la de «Otros» si la categoría es desconocida), título, nombre de la categoría, «Zona de unos 500 m», «1 km» o «2 km», y precio por unidad en formato español («12,50 € / día», «30 € / semana»).
- **Selección**: conjunto de bienes resaltados a la vez en el mapa (su círculo) y en el panel (su tarjeta).
- **Aviso de ubicación aproximada**: «Ubicación aproximada: cada bien está en algún punto dentro de su círculo, de 500 m a 2 km de radio según el anuncio. Nunca se muestra la dirección.»
- **Identidad visual**: la del diseño de referencia de la portada.
  - Tipografía Bricolage Grotesque, alojada en el propio sitio.
  - Paleta: azul #1647B8 (acento, círculos y grupos), cielo #E8EEFF (fondo), tinta #14181F (texto), gris #424B5A (texto secundario) y limón #F5D547 (selección).
- **Comando de demostración**: orden de administración que llena la base de datos de desarrollo. Crea un **propietario de demostración** con un email del dominio `example.com`, reservado para ejemplos. Solo se ejecuta en los entornos `development` y `test` (RF-7).

### Valores de esta spec
| Valor | Fijado |
|---|---|
| Área máxima de la zona | 6 grados cuadrados, validados en el servidor; el cliente deja un margen por debajo |
| Tope de resultados | 200 bienes; la consulta pide como máximo 201 y no cuenta |
| Límite de peticiones por IP | 60 por minuto, contando todas las peticiones a la lista, también las rechazadas |
| Duración de la caché de una respuesta correcta | 60 s, pública |
| Ampliación de la zona visible antes de redondear | 2 km por cada lado |
| Agrupación | solo con zoom menor que 13 |
| Longitud máxima de cada límite de la zona | 32 caracteres |

Los demás números los fija el plan: el paso de la cuadrícula del cuadro pedido, el margen del área en el cliente, el tiempo de espera tras dejar de mover el mapa, el tiempo máximo de espera de una respuesta, el criterio de cercanía de la agrupación, el zoom máximo al enfocar una tarjeta y las medidas del panel (alturas y ancho de la columna).

## Requisitos funcionales

### Lista pública de bienes
- RF-1: CUANDO cualquier visitante pide los bienes de una zona válida, EL SISTEMA devuelve los bienes visibles de esa zona. Un bien `paused` no aparece nunca, ni siquiera para su propietario. Tampoco aparece un bien `active` cuyo propietario tiene la cuenta desactivada. La única salvedad es la excepción de caché aceptada (Caché).
- RF-2: EL SISTEMA devuelve cada bien solo con estos campos: identificador público, título, slug y nombre de su categoría (el bien no tiene slug propio), importe y moneda del precio, unidad de precio, radio de privacidad y latitud y longitud de la ubicación pública. Nunca incluye la ubicación exacta, la descripción, las fechas, el estado, ningún dato del propietario ni la clave primaria. El identificador público es un UUID versión 4 aleatorio que genera el servidor al crear el bien, nunca un formato con marca de tiempo. Es único, opaco y distinto de la clave primaria. El campo no es editable en el modelo (queda fuera del admin y de los formularios) y ningún servicio lo cambia durante la vida del bien, tampoco al pausarlo, reactivarlo o cambiar su ubicación.
- RF-3: SI se da alguna de estas condiciones, ENTONCES EL SISTEMA responde con un error de entrada, sin consultar los bienes:
  - falta alguno de los cuatro límites, llega más de una vez o tiene más de 32 caracteres;
  - algún límite no es un número decimal finito en notación ASCII estricta, que fija el plan (se rechazan texto, vacío, `NaN`, `Infinity`, exponente, coma decimal, espacios y dígitos no ASCII);
  - una latitud está fuera del intervalo de −90 a 90, o una longitud fuera del de −180 a 180;
  - el sur es mayor que el norte, o el oeste mayor que el este (zona invertida, también cuando cruza el antimeridiano);
  - el área supera el máximo (zona demasiado grande).

  El error lleva a la vez un código estable por cada límite que falla. Las comprobaciones de la zona entera (invertida y demasiado grande) solo se hacen cuando los cuatro límites son válidos, y tienen su propio código. Si la zona está invertida no se comprueba el área: el error trae solo el código de zona invertida.
- RF-4: EL SISTEMA ordena los bienes del más reciente al más antiguo por fecha de creación; a igual fecha va primero el de mayor identificador interno, que no se expone. Lee como máximo el tope más uno y nunca cuenta el total. SI hay más bienes visibles que el tope, ENTONCES devuelve los primeros hasta el tope e indica solo que la lista está incompleta, sin ningún total.
- RF-5: SI una misma dirección IP supera el límite de peticiones a la lista pública, ENTONCES EL SISTEMA responde con un error de límite superado, sin validar la zona ni consultar los bienes. El error lleva el código `throttled` y los segundos que hay que esperar, en el cuerpo y en la cabecera `Retry-After`. El límite se aplica antes de comprobar el método y de validar la entrada, y cuenta todas las peticiones a la lista, también las rechazadas por entrada inválida o por método no admitido. Con el límite superado, cualquier método recibe el error de límite superado. La IP es la de la conexión; `X-Forwarded-For` no se usa hasta la spec 010.

### Bienes de demostración
- RF-6: CUANDO un desarrollador ejecuta el comando de demostración y el propietario de demostración no existe, EL SISTEMA hace lo siguiente en una sola transacción:
  - crea el propietario de demostración con una contraseña aleatoria que no se muestra;
  - crea 25 bienes en el entorno de Valencia mediante el servicio de escritura de bienes, con al menos uno por categoría de la semilla, los tres radios de privacidad y al menos dos bienes con la misma ubicación pública y el mismo radio;
  - activa 24 de ellos con el mismo servicio y deja uno pausado.

  SI el propietario de demostración ya existe, ENTONCES no crea nada e informa de ello.
- RF-7: SI el comando de demostración se ejecuta en un entorno distinto de `development` o `test`, o sin entorno definido, ENTONCES EL SISTEMA termina con un error y un mensaje fijo, sin escribir nada en la base de datos.

### Mapa
- RF-8: CUANDO un visitante abre la raíz de RentRadar o la página del mapa, EL SISTEMA lo lleva a la página del mapa (la raíz redirige a ella) y muestra el mapa a pantalla completa en la vista inicial, con el mapa base, el panel de resultados, el aviso de ubicación aproximada y la atribución del mapa base. El aviso y la atribución quedan visibles en todo momento, sin que el panel los tape en ninguna de sus alturas.
- RF-9: CUANDO el mapa lleva quieto el tiempo de espera, EL SISTEMA calcula el cuadro pedido. Si su latitud está dentro de −85…85, su longitud dentro de −180…180 y su área no supera el máximo menos el margen del cliente, pide sus bienes; si no, aplica RF-14. Cancela cualquier petición anterior sin terminar y nunca muestra su respuesta. El mapa queda quieto tras abrirlo, desplazarlo, acercarlo o alejarlo y tras redimensionar la ventana.
- RF-10: EL SISTEMA dibuja cada bien de la última respuesta como su círculo, a cualquier zoom, sin marcador ni punto central. Los bienes con la misma ubicación pública y el mismo radio comparten un solo círculo.
- RF-11: MIENTRAS el zoom es menor que 13, EL SISTEMA sustituye por un grupo, situado en el punto medio de sus ubicaciones públicas (la media de sus latitudes y de sus longitudes) y con el número de bienes que reúne, los círculos que cumplen el criterio de cercanía de la agrupación. Un círculo seleccionado nunca se agrupa. CUANDO se pulsa un grupo, EL SISTEMA acerca el mapa sobre él hasta el primer zoom entero en que se separa, como máximo 13. MIENTRAS la lista está incompleta, cada grupo indica, de forma visible y accesible, que su número puede no ser el total de su zona.
- RF-12: CUANDO llega una respuesta válida, EL SISTEMA hace lo siguiente:
  - Lista en el panel, en el orden de la respuesta, una tarjeta por cada bien cuyo círculo se ve, aunque sea en parte, en la zona visible.
  - Muestra en la cabecera del panel el número de tarjetas:
    - «1 bien en esta zona» o «N bienes en esta zona» si la lista es completa;
    - «Mostrando N bienes. Puede haber más: acerca el mapa para verlos todos» si la lista está incompleta.

    La cabecera se ve con cualquier altura del panel.
  - Por debajo de 900 px, el panel cambia de altura de dos maneras:
    - pulsando su asa, que pasa de plegado a medio, de medio a desplegado y de desplegado a plegado;
    - con el foco en el asa, con las flechas arriba y abajo.

    Plegado, el panel no deja enfocar las tarjetas.
- RF-13: La selección funciona en las dos direcciones.
  - CUANDO se activa una tarjeta (con ratón, toque, Enter o Espacio), aunque ya esté seleccionada, EL SISTEMA:
    - selecciona todos los bienes que comparten su círculo y resalta ese círculo y sus tarjetas;
    - mueve el mapa hasta que el círculo se ve entero en la parte que no tapa el panel, sin pasar del zoom máximo al enfocar una tarjeta y sin animación si el visitante ha pedido reducir el movimiento;
    - por debajo de 900 px, si el panel estaba desplegado, lo baja a medio, y el foco sigue en la tarjeta.
  - CUANDO se toca un círculo, EL SISTEMA:
    - selecciona todos los bienes cuyo círculo contiene el punto tocado, con el mismo resaltado en el mapa y en sus tarjetas;
    - si el panel estaba plegado, lo sube a medio;
    - desplaza la lista hasta la primera tarjeta seleccionada, sin mover el foco.
  - CUANDO se toca el mapa fuera de cualquier círculo, EL SISTEMA quita la selección. CUANDO se pulsa Escape con el foco en una tarjeta o en el mapa, EL SISTEMA quita la selección y el foco no se mueve.
  - Un bien seleccionado que deja de tener tarjeta tras una respuesta nueva sale de la selección.
- RF-14: CUANDO una respuesta válida no deja ninguna tarjeta, EL SISTEMA muestra en el panel «No hay bienes en esta zona» y el botón «Volver a la zona inicial», que devuelve el mapa a la vista inicial. MIENTRAS el área del cuadro pedido supera el máximo menos el margen del cliente, o su latitud sale de −85…85 o su longitud de −180…180 (también cuando cruza el antimeridiano), EL SISTEMA no pide bienes y muestra «Acerca el mapa para ver los bienes» con el mismo botón. Cuando el mapa ya está en la vista inicial, el botón no aparece.
- RF-15: SI falla la petición de bienes o la carga del mapa base, ENTONCES EL SISTEMA muestra y anuncia un mensaje en castellano para cada caso, sin datos técnicos, con un botón «Reintentar». Se cubren estos casos:
  - la petición de bienes falla por falta de red, porque no hay respuesta en el tiempo máximo de espera, por un error del servidor, por un límite superado o porque la forma de la respuesta no es la esperada;
  - falla el estilo del mapa base, que no se descarga o no es válido.

  Según lo que falle:
  - si falla el estilo, el mensaje sustituye al mapa;
  - si falla la petición de bienes, el panel sustituye la lista por el mensaje y el mapa deja de mostrar círculos.

## Requisitos no funcionales
- **Permisos (constitución, punto 5)**:
  - La lista pública es de solo lectura. El anónimo, el usuario con sesión (desde la spec 008), el propietario y el staff reciben los mismos resultados.
  - Ninguno recibe bienes pausados ni ubicaciones exactas por esta vía, ni siquiera de sus propios bienes.
  - Cualquier método de escritura recibe un error de método no admitido, salvo que el límite de peticiones ya esté superado (RF-5).
  - No hay caso de 404 ni de 403 por objeto, porque esta spec no tiene vista de detalle. Cuando llegue el detalle de un bien, un bien pausado responderá 404 al público.
- **Privacidad**:
  - Solo se usa la ubicación pública, para buscar y para dibujar. La lectura pública no carga la ubicación exacta de la base de datos.
  - Los datos del propietario se minimizan a ninguno.
  - La dirección de la página no cambia al mover el mapa (ni fragmento ni parámetros), el historial no gana entradas y la vista no se guarda en el almacenamiento del navegador.
- **Caché**:
  - Una respuesta correcta de la lista pública puede guardarse en cachés públicas, también la del navegador, durante 60 s.
  - Ningún error bajo la API se guarda en ninguna caché: todos llevan `Cache-Control: no-store`, también los de ruta inexistente y método no admitido.
  - **Excepción aceptada a la regla de la spec 005 sobre bienes pausados**: un bien que deja de ser visible (pausado o, cuando exista, eliminado) o cuya cuenta se desactiva puede seguir apareciendo hasta 60 s en este listado. Ninguna otra respuesta futura con datos de un bien hereda esta caché si su spec no lo decide expresamente.
- **Respuesta idéntica para cualquier visitante**:
  - La lista pública no autentica al visitante: no lee ni modifica la sesión. Su respuesta no depende de cookies, sesión ni cabeceras del visitante, salvo la compresión. Solo se declara variable por la codificación aceptada (`Vary: Accept-Encoding`), nunca por `Cookie` ni por `Authorization`.
  - El backend acepta cualquier zona válida. No exige que esté alineada a la cuadrícula: el redondeo lo hace el cliente para acertar en la caché.
- **Terceros**:
  - La página solo hace peticiones a su propio origen y al proveedor del mapa base (OpenFreeMap). De él vienen el estilo, las teselas, los glifos y los sprites del mapa.
  - Las fuentes y las imágenes de la interfaz se alojan en el propio sitio; no se usa ningún servicio de fuentes externo. La tipografía tiene una licencia que permite alojarla.
  - La política de seguridad de contenido y la de referente, con la lista de hosts permitidos, llegan en la spec 010.
- **Mismo origen**: en desarrollo y en producción, el navegador llama a la API desde el mismo origen que la página, y la API no concede permisos entre orígenes.
- **Desconfianza de la entrada (constitución, punto 6)**: el backend valida el tipo, el rango y el tamaño de cada límite de la zona (RF-3). Los parámetros desconocidos se ignoran. El cliente valida la forma de cada respuesta antes de usarla (tipos, radio entre 500, 1000 y 2000, coordenadas finitas y en rango, unidad conocida, moneda EUR, precio decimal, indicador de lista incompleta booleano). Si un solo bien no cumple, la respuesta entera se trata como inválida (RF-15).
- **Errores de la API**:
  - Todos los errores bajo la API tienen un formato único, también los que se generan fuera de la capa de la API: entrada inválida, ruta inexistente, método no admitido, límite superado y error interno. El formato se garantiza con la depuración desactivada; con la depuración activa en desarrollo se acepta la página técnica de Django.
  - Contienen solo códigos estables en inglés: uno general y, si procede, uno por parámetro. Nunca incluyen el valor recibido, coordenadas ni trazas. El cliente traduce los códigos.
  - La lista de códigos y el formato se fijan en el plan.
- **Depuración y logs**:
  - Con la depuración activa en desarrollo, la página de error no muestra las coordenadas de las variables locales del servicio de escritura de bienes ni del comando de demostración. La lectura pública no necesita esta protección porque no carga la ubicación exacta. En producción la depuración nunca está activa (spec 001).
  - Ni los logs de la aplicación ni la salida del comando contienen coordenadas de un bien, ni exactas ni públicas, ni la contraseña del propietario de demostración.
  - En desarrollo se acepta que el log de accesos guarde la zona pedida y la IP del visitante. Su retención se decide en la spec 010.
- **Contrato**:
  - La API pública está versionada desde su primera versión y publica una descripción legible por máquina, de la que se generan los tipos del cliente. Un control automático falla si los tipos generados no corresponden a la descripción actual.
  - Los tipos generados no validan en ejecución; esa validación la hace el cliente (Desconfianza de la entrada).
- **Dependencias (constitución, punto 1)**: las dependencias nuevas de esta spec se listan en el plan con su versión exacta y no se instalan sin aprobación expresa. La agrupación de círculos es propia, sin librería.
- **Accesibilidad y móvil (constitución, punto 7)**:
  - Se diseña a 375 px y se amplía a 1280 px. Los controles miden al menos 44 px: asa, tarjetas, zoom, «Reintentar» y «Volver a la zona inicial».
  - El foco es visible. El mapa tiene una etiqueta accesible y se mueve y acerca con teclado. El texto tiene un contraste AA.
  - Una región de estado anuncia la carga («Buscando bienes…»), el número de resultados, la lista incompleta, el vacío y los errores, una vez por petición.
  - El asa expone si el panel está ampliado. Las tarjetas seleccionadas exponen su estado.
  - Si el visitante pide reducir el movimiento, no hay animaciones.
  - Los grupos y los círculos no son enfocables con teclado. La vía accesible es el panel, junto con los controles de zoom.
- **Configuración**: la dirección del estilo del mapa base es configurable por entorno, sin cambiar el código, y tiene que usar https. Por defecto es la de "positron" de OpenFreeMap.
- **Idioma (constitución, punto 8)**: los textos de la interfaz están en castellano y salen de un catálogo de mensajes, para poder traducirlos. Los códigos y los identificadores van en inglés.

## Casos límite
- La zona tiene sur 39,4 y norte 39,4 (sin altura): es válida y devuelve los bienes con latitud exactamente 39,4 (RF-1, RF-3).
- Un bien está exactamente sobre un borde de la zona: aparece (RF-1).
- La zona está invertida (el sur es mayor que el norte) o el oeste es mayor que el este, por ejemplo de 179 a −179 cruzando el antimeridiano: se rechaza con el código de zona invertida (RF-3). Si el cuadro pedido cruza el antimeridiano, su longitud sale de −180…180 y el cliente no pide (RF-14).
- Un límite vale `abc`, está vacío, es `NaN`, `Infinity`, `-inf`, `1e1` o `39,4`, es `39.4` precedido de un espacio, usa dígitos no ASCII o está repetido: se rechaza (RF-3).
- Fallan a la vez el sur y el este: el error trae los códigos de los dos y ninguno de zona. Con los cuatro límites válidos y la zona invertida, el error trae el código de zona invertida (RF-3).
- La zona está invertida y su área calculada supera el máximo: el error trae solo el código de zona invertida, porque el área de una zona invertida no se comprueba (RF-3).
- Un límite tiene 33 caracteres: se rechaza. Uno de 32 con muchos decimales: se acepta (RF-3).
- La latitud es 90,000001 o la longitud −180,5: se rechaza (RF-3).
- El área es exactamente 6: se acepta, porque el servidor la calcula sin errores de redondeo. Si es 6,0001: se rechaza con el código de zona demasiado grande (RF-3).
- En el cliente, la zona visible mide 5,8 grados cuadrados pero el cuadro pedido mide 6,3: no se pide y se muestra «Acerca el mapa para ver los bienes» (RF-9, RF-14).
- El cuadro pedido mide justo 6 grados cuadrados: el cliente tampoco pide, por su margen bajo el máximo (RF-9, RF-14).
- El cuadro pedido sale de ±85 de latitud o de ±180 de longitud: no se recorta, el cliente no pide y muestra «Acerca el mapa para ver los bienes» (Definiciones: cuadro pedido, RF-14). El servidor sigue aceptando latitudes de −90 a 90 (RF-3).
- La zona visible va de 59 a 61 de latitud: los 2 km de ampliación se pasan a grados de longitud con la latitud 61, la más alejada del ecuador (Definiciones: cuadro pedido).
- El visitante mueve un poco el mapa dentro del mismo cuadro pedido: la petición es idéntica y la sirve la caché del navegador sin llegar al servidor (RF-9, Caché).
- Un bien de 2 km de radio tiene el centro fuera de la zona visible, pero su círculo asoma por el borde: está en el cuadro pedido gracias a la ampliación de 2 km, se dibuja y tiene tarjeta (RF-9, RF-12).
- No hay ningún bien en el cuadro pedido: la respuesta es una lista vacía, no un error, y el cliente muestra el estado vacío (RF-1, RF-14).
- Hay 201 bienes visibles en el cuadro pedido: se devuelven 200, los más recientes, la lista es incompleta y no hay total. Con 200 exactos, la lista es completa (RF-4).
- La lista está incompleta pero solo 40 de sus bienes se ven en pantalla: la cabecera dice «Mostrando 40 bienes. Puede haber más…», que sigue siendo verdad, y los grupos se marcan como parciales (RF-11, RF-12).
- Llega un parámetro de categoría o de texto (spec 007): se ignora (Desconfianza de la entrada).
- Un bien pausado está dentro de la zona: no aparece. Si se pausa después de una petición, puede seguir apareciendo hasta 60 s por la excepción de caché (RF-1, Caché).
- Un bien activo pertenece a una cuenta desactivada: no aparece (RF-1).
- Llegan la misma petición con cookie de sesión y sin ella: la respuesta y su cabecera de caché son las mismas, la sesión no se toca y la respuesta solo se declara variable por la compresión (Respuesta idéntica).
- Llega la petición 61 en un minuto desde la misma IP, aunque las anteriores fueran inválidas: recibe el error de límite superado con `Retry-After`, sin caché y sin que se valide su zona. El cliente muestra su mensaje con «Reintentar» (RF-5, RF-15).
- Llegan peticiones desde la misma IP con cabeceras `X-Forwarded-For` distintas: cuentan todas para esa IP (RF-5).
- Llega un método de escritura a la lista pública: error de método no admitido con el formato único y sin caché (Permisos, Errores de la API, Caché).
- Llega un método de escritura con el límite de peticiones superado: error de límite superado y no de método no admitido, y la petición cuenta para el límite (RF-5).
- Con la depuración desactivada, se pide una ruta inexistente bajo la API o se produce un error interno: error con el formato único y sin caché, nunca la página de Django. Con la depuración activa en desarrollo se acepta la página técnica (Errores de la API).
- Varios bienes caen en la misma celda con el mismo radio: se dibuja un solo círculo. Al tocarlo se resaltan todas sus tarjetas y la lista se desplaza hasta la primera (RF-10, RF-13).
- Se activa la tarjeta de un bien que comparte círculo con otros: se seleccionan todos los bienes de ese círculo y se resaltan todas sus tarjetas (RF-13).
- Se activa una tarjeta ya seleccionada después de mover el mapa: el mapa vuelve a enfocar su círculo. Escape, con el foco en una tarjeta o en el mapa, quita la selección sin mover el foco (RF-13).
- Dos círculos distintos se solapan y se toca su intersección: se seleccionan los bienes de ambos (RF-13).
- Dos bienes tienen la misma ubicación pública y radios distintos: se dibujan dos círculos concéntricos (RF-10).
- Un grupo sigue sin separarse con zoom 13: el mapa se queda en 13 y a partir de ahí se ven los círculos, solapados (RF-11).
- Se selecciona una tarjeta y después se aleja el mapa por debajo de zoom 13: su círculo no se agrupa (RF-11).
- El visitante toca un círculo con el panel plegado: el panel sube a medio y muestra la tarjeta resaltada (RF-13).
- La tarjeta seleccionada sigue en pantalla tras la nueva petición: sigue marcada. Si el bien ya no tiene tarjeta, sale de la selección (RF-13).
- El visitante mueve el mapa varias veces seguidas: solo se pide el cuadro en el que el mapa queda quieto el tiempo de espera, y la respuesta de una petición anterior nunca se pinta (RF-9).
- El visitante redimensiona la ventana: se recalculan las alturas del panel y el cuadro pedido, y se pide de nuevo (RF-9, RF-12). Si la ventana cruza los 900 px, el panel cambia de disposición y conserva la selección (RF-12, RF-13).
- Falla la red, el servidor tarda más del tiempo máximo de espera o el servidor devuelve un error 500: se muestra el mensaje correspondiente con «Reintentar» (RF-15).
- La respuesta trae un bien con radio 1500, latitud `null`, precio no decimal o un campo de más: la respuesta entera se trata como inválida (RF-15, Desconfianza de la entrada).
- La respuesta trae una categoría que el cliente no conoce: se muestra su nombre y la imagen de «Otros» (Definiciones: tarjeta).
- El servidor del estilo no responde o devuelve algo que no es un estilo: se muestra el mensaje en lugar del mapa (RF-15). Si fallan teselas sueltas, el mapa base queda incompleto sin aviso (Fuera de alcance).
- El visitante abre la raíz: llega a la página del mapa, y el botón Atrás no le devuelve a la raíz (RF-8).
- El comando de demostración se ejecuta dos veces: la segunda no crea nada (RF-6). Si falla a mitad, no queda nada creado (RF-6, una transacción). Fuera de `development` y `test`, o sin entorno definido, se niega sin escribir nada (RF-7).
- La base de datos está vacía y el visitante está en la vista inicial: ve «No hay bienes en esta zona», sin el botón (RF-14).

## Fuera de alcance
- Portada, teselas de categorías, buscador «Qué», chips de categoría en el mapa y filtros por categoría y texto en la API (spec 007). En la 007 la portada ocupará la raíz y solo se quitará la redirección; la página del mapa no cambia de dirección.
- Arrastrar el asa del panel para cambiar su altura: en la 006 solo se pulsa o se usan las flechas (RF-12).
- Aviso de fallo de teselas sueltas del mapa base: en la 006 solo se avisa del fallo del estilo y de la petición de bienes (RF-15).
- Filtrar el panel por círculo, con un botón «Ver todos» (spec 007). En la 006, tocar un círculo solo lo selecciona (RF-13).
- Recuentos por celda en lugar de bienes sueltos, por encima del tope o con zoom bajo, cuando haya volumen real.
- Autenticación, sesiones y protección CSRF de las escrituras (spec 008).
- Publicar bienes y fotos reales; las imágenes son genéricas por categoría (spec 009).
- Despliegue (spec 010):
  - HTTPS y proxy inverso;
  - obtención de la IP real del cliente para el límite de peticiones (hasta entonces no se usa `X-Forwarded-For`) y almacenamiento compartido del contador entre procesos;
  - CDN y su tiempo de caché;
  - política de seguridad de contenido (CSP) y `Referrer-Policy`, con la lista de hosts permitidos;
  - retención del log de accesos.
- Búsqueda por municipio y campo «Dónde» (spec 011). «Cerca de mí» y geolocalización, sin spec asignada.
- Detalle de un bien, contacto y reservas. Paginación más allá del tope. Distancia mostrada y ordenación por distancia.
- Recolorear el estilo del mapa base, alojar el mapa base en el propio sitio y modo oscuro.
- Recordar la vista del mapa entre visitas o compartirla por enlace.
- Ubicación exacta pública de los profesionales.

## Riesgos propuestos para aceptar
- El servidor del mapa base (OpenFreeMap) es un tercero sin acuerdo de servicio. Recibe la IP del visitante y la zona que mira a través de las peticiones de teselas. La política de privacidad deberá mencionarlo antes de abrir a usuarios reales.
- Recorriendo zonas dentro del límite de peticiones se pueden recopilar todas las ubicaciones públicas activas. Son públicas por diseño.
- El límite por IP penaliza a quienes comparten IP (NAT), y en desarrollo cada proceso cuenta por separado.
- Con la lista incompleta, en zonas densas y con zoom bajo, se ven antes los bienes recientes que los antiguos.
- Un cliente que no redondea la zona, que la varía a propósito o que añade parámetros desconocidos no aprovecha la caché, pero cada petición consume su límite por IP.
- Una zona de un solo punto (sur igual a norte y oeste igual a este) confirma si hay un bien en una ubicación pública concreta. Las ubicaciones públicas son públicas por diseño.
- Una CDN o una caché intermedia que guarde las respuestas más de 60 s alargaría la excepción de caché. Se revisa en la spec 010.
- Si un bien pausado se reactiva con otra ubicación, conserva su identificador público. Quien guardó respuestas anteriores puede relacionar la ubicación pública antigua con la nueva y acotar la exacta. Se acepta en la 006 porque solo hay datos de demostración.

## Criterios de finalización
- Cada RF tiene un test automático o una verificación en navegador:
  - pytest para RF-1 a RF-7;
  - vitest solo para funciones puras de RF-9 a RF-15:
    - cuadro pedido: ampliación con la latitud más alejada del ecuador, redondeo, rechazo fuera de ±85 de latitud y de ±180 de longitud, y área con margen;
    - círculo geodésico y filtro de tarjetas por círculo visible;
    - agrupación: punto medio, zoom entero de separación y marca de grupo parcial;
    - validación de la respuesta, espera y cancelación;
    - máquina de alturas del panel;
    - selección en las dos direcciones, con círculo compartido, reactivación y Escape;
    - textos de la cabecera y elección del estado de vacío y de error;
  - RF-8 y el dibujo de RF-10 se verifican en el navegador y quedan registrados en validation.md.
- RF-4 se verifica con 201 bienes visibles. El test comprueba que se devuelven 200, que la lista se marca como incompleta y que la consulta no ejecuta ningún recuento.
- Tests del identificador público (RF-2): es un UUID versión 4 y es distinto de la clave primaria. Es único entre bienes. El campo no es editable en el modelo y ningún servicio lo cambia al editar, pausar o reactivar el bien.
- Tests de privacidad y seguridad, con prueba de mecanismo:
  - lista blanca de campos (RF-2);
  - exclusión de pausados, incluidos los del propietario, y de los bienes de cuentas desactivadas (RF-1);
  - la lectura pública no carga la ubicación exacta;
  - el límite de peticiones se aplica antes de comprobar el método y de validar, cuenta las peticiones inválidas y las de método no admitido, e ignora `X-Forwarded-For`. Los tests del límite vacían el contador antes de empezar (RF-5);
  - los errores no contienen valores, coordenadas ni trazas;
  - la página de depuración del servicio de escritura de bienes y del comando de demostración no muestra coordenadas;
  - ni los logs ni la salida del comando contienen coordenadas de bienes ni la contraseña;
  - el comando se niega fuera de `development` y `test`, y sin entorno definido, sin escribir nada (RF-7).
- Los tests que actúan como propietario o como staff inician sesión con `force_login`.
- Un test de caché comprueba que la respuesta correcta lleva una caché pública de 60 s. Comprueba también que todos los errores bajo la API (entrada inválida, límite superado, ruta inexistente y método no admitido) llevan `Cache-Control: no-store` (Caché).
- Un test con la depuración desactivada comprueba el formato único en los errores de entrada inválida, ruta inexistente, método no admitido, límite superado y error interno (Errores de la API).
- Un test hace la misma petición con cookie de sesión y sin ella y comprueba que la respuesta es la misma, que la caché sigue siendo pública, que no se crea ni se modifica ninguna cookie de sesión y que la respuesta no se declara variable por `Cookie` ni por `Authorization` (Respuesta idéntica).
- Un test calcula con haversine la distancia del centro a cada vértice del polígono del círculo y comprueba que está entre el 99 % y el 101 % del radio de privacidad (RF-10).
- El control de desfase entre la descripción de la API y los tipos generados está en verde (Contrato).
- Comprobación de punta a punta con el comando de demostración: el mapa muestra los 24 bienes activos y no el pausado (RF-1, RF-6).
- Verificación en navegador con Chrome DevTools a 375 y 1280 px, registrada en validation.md:
  - redirección de la raíz a `/map` sin entrada en el historial, círculos sin marcador, grupos, selección desde la tarjeta y desde el círculo, tres alturas del panel, vacío y su salida, error del mapa base y de la API (simulados), y aviso y atribución visibles con cualquier altura;
  - recorrido completo solo con teclado y consola sin errores;
  - red solo hacia el propio origen y el proveedor del mapa base, este siempre por https, con aciertos de caché al mover el mapa dentro del mismo cuadro;
  - la dirección de la página no cambia al mover el mapa.
- pytest, ruff, vitest, build y eslint en verde.

## Dudas abiertas
Las resuelve el plan:
- Paso de la cuadrícula del cuadro pedido; por ejemplo, 0,05°.
- Margen del área en el cliente, tiempo de espera, tiempo máximo de espera, criterio de cercanía de la agrupación, zoom máximo al enfocar una tarjeta y medidas del panel.
- Gramática ASCII estricta de los límites de la zona.
- Cómo se marca que el número de un grupo es parcial con la lista incompleta; por ejemplo, un «+» en la burbuja con texto accesible, o el aviso también sobre el mapa.
- Formato concreto del error, lista de códigos y versión de la ruta de la API. Cómo se aplica el formato a los errores que se generan fuera de la capa de la API.
- Si la descripción legible por máquina se publica en producción o solo en desarrollo y en build.
- Cómo llama el navegador a la API desde el mismo origen en desarrollo, con la interfaz en el host.
- Cómo se rechaza una dirección del estilo del mapa base que no usa https.
- Almacenamiento del contador del límite de peticiones en desarrollo y su paso a uno compartido en la spec 010.
- Dependencias nuevas, con su versión exacta, para aprobación: librería del mapa, generación de la descripción de la API y de los tipos del cliente, validación de las respuestas en ejecución y tipografía.
