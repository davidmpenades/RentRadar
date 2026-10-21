# Spec 005 — Bienes y privacidad de la ubicación
Estado: borrador
Depende de: spec 001 (RF-5: base de datos capaz de calcular distancias geodésicas en metros; RF-29 y RF-30: fechas con zona horaria y UTC como referencia), spec 002 (RF-7: los cambios de modelos sin migración hacen fallar los tests) y spec 004 (usuarios, categorías y semilla; RF-22 se cierra aquí).

## Contexto y objetivo
Con usuarios y categorías ya fijados (spec 004), falta el dato central de RentRadar: el **bien** (producto o espacio) que se alquila, con su precio, su estado y su ubicación.

La ubicación es lo delicado. El anunciante introduce su ubicación exacta, que es privada. Lo que ve el público es siempre una ubicación aproximada, igual para particulares y profesionales, derivada de la exacta con una cuadrícula fija y anidada. Así cruzar varias búsquedas no permite deducir la dirección.

Esta spec define los datos del bien, la función que calcula la ubicación aproximada, el único servicio que escribe bienes y las reglas de privacidad que respetarán las specs de API, búsqueda, mapa y reservas. No hay endpoints, pantallas, fotos ni campos propios de cada tipo de bien.

## Usuarios
- **Anunciante (propietario de bienes)**: crea y modifica sus bienes; en esta spec solo existe como dato.
- **Arrendatario**: persona que alquila; solo aparece en las reglas de privacidad.
- **Anónimo**: no tiene cuenta; solo aparece en las reglas de privacidad.
- **Desarrollador del equipo**: ejecuta los tests.

## Historias de usuario
- HU-1. Como anunciante, quiero clasificar mi bien en una categoría de la lista cerrada para que lo encuentren quienes buscan ese tipo de bien.
- HU-2. Como anunciante, quiero fijar el precio por hora o por día en euros para que el arrendatario sepa cuánto cuesta.
- HU-3. Como anunciante, quiero guardar mi dirección exacta y elegir cuánto se aproxima en público (500, 1000 o 2000 m) para proteger mi privacidad.
- HU-4. Como anunciante, quiero que mi bien nazca pausado y activarlo cuando haya revisado su radio, para no publicar mi zona por descuido.
- HU-5. Como anunciante, quiero pausar y reactivar un bien sin borrarlo para dejar de recibir interés temporalmente.
- HU-6. Como desarrollador, quiero que la ubicación pública sea estable, verificable y se calcule en un único sitio para que ninguna escritura filtre ni desincronice la ubicación.

## Definiciones
- **Ubicación exacta**: la coordenada (latitud y longitud) que introduce el anunciante. Es privada.
- **Ubicación pública**: la ubicación aproximada derivada de la exacta y del radio de privacidad. Es la única que se muestra o se usa para buscar.
- **Radio de privacidad**: uno de 500, 1000 o 2000 metros. Es el lado, en metros, de la celda de la cuadrícula, y el radio del círculo que el mapa dibuja alrededor de la ubicación pública.
- **Cuadrícula**: división del plano de la proyección ETRS89-LAEA Europe (EPSG:3035) en celdas cuadradas de lado igual al radio de privacidad, con origen en el origen de esa proyección. Es fija y anidada: todas las celdas comparten origen, cada celda de 1000 m contiene exactamente 4 de 500 m y cada una de 2000 m contiene exactamente 4 de 1000 m. Una celda incluye sus bordes inferior e izquierdo y excluye los superior y derecho, de modo que un punto pertenece a una sola celda. La proyección y el origen no cambian: cambiarlos movería todas las celdas públicas.
- **Función de aproximación**: función que, dada una coordenada y un radio de privacidad, devuelve el centro de la celda que contiene esa coordenada, expresado en latitud y longitud y redondeado a 6 decimales.
- **Caja de coherencia**: rectángulo con latitud entre 27,5 y 44,0 grados y longitud entre -18,5 y 5,0 grados, ambos límites incluidos. Es un control de coherencia que detecta coordenadas intercambiadas y valores absurdos, no una frontera: incluye toda España, pero también Portugal continental, Andorra, Madeira, el sur de Francia y el norte de Marruecos y Argelia.
- **Servicio de escritura de bienes**: la única función de escritura de bienes que expone el dominio.
- **Arrendatario con reserva confirmada**: usuario cuya solicitud de reserva sobre un bien ha aceptado el propietario (se define en la spec de reservas).
- **Texto recortado**, **longitud**, **carácter de control** y **rechazar**: como en la spec 004. En validación, el error lleva un código y el campo, nunca el valor; en la base de datos, un error de integridad.

## Requisitos funcionales

### Datos del bien
- RF-1: CUANDO el servicio de escritura crea un bien válido, EL SISTEMA lo guarda con propietario, categoría, título, descripción, precio, moneda, unidad de precio, ubicación exacta, ubicación pública, radio de privacidad, estado, fecha de creación y fecha de modificación.
- RF-2: SI falta el propietario o la categoría, o no corresponde a un usuario o una categoría existente, ENTONCES EL SISTEMA rechaza el bien.
- RF-3: SI el título recortado tiene menos de 3 o más de 100 caracteres, o contiene caracteres de control, ENTONCES EL SISTEMA rechaza el bien.
- RF-4: SI la descripción recortada tiene menos de 20 o más de 2000 caracteres, o contiene el carácter nulo, ENTONCES EL SISTEMA rechaza el bien.
- RF-5: SI el precio no es un número decimal finito, es menor que 0,01, es mayor que 99999,99 o tiene más de 2 decimales, ENTONCES EL SISTEMA rechaza el bien sin redondearlo.
- RF-6: CUANDO no se indica moneda, EL SISTEMA asigna EUR.
- RF-7: SI se indica una moneda distinta de EUR, ENTONCES EL SISTEMA rechaza el bien.
- RF-8: SI la unidad de precio falta o no es `hour` ni `day`, ENTONCES EL SISTEMA rechaza el bien.
- RF-9: CUANDO no se indica radio de privacidad, EL SISTEMA asigna 1000.
- RF-10: SI el radio de privacidad no es exactamente 500, 1000 o 2000 (incluidos 0, negativos, decimales y valores intermedios como 1500), ENTONCES EL SISTEMA rechaza el bien.
- RF-11: CUANDO se crea un bien sin indicar estado, EL SISTEMA le asigna `paused`, para que no publique su ubicación aproximada hasta que el anunciante haya revisado su radio y lo active a propósito.
- RF-12: SI se indica un estado distinto de `active` o `paused`, ENTONCES EL SISTEMA rechaza el bien.
- RF-13: SI la ubicación exacta falta, o su latitud está fuera de -90 a 90, o su longitud fuera de -180 a 180, o alguna no es un número finito, ENTONCES EL SISTEMA rechaza el bien.
- RF-14: SI la ubicación exacta está fuera de la caja de coherencia, ENTONCES EL SISTEMA rechaza el bien.
- RF-15: CUANDO se crea un bien, EL SISTEMA registra la fecha de creación y la de modificación con zona horaria.
- RF-16: CUANDO se modifica un bien, EL SISTEMA actualiza la fecha de modificación y conserva la de creación.
- RF-17: EL SISTEMA representa un bien como texto solo con su título y su identificador, y nunca incluye coordenadas (ni exactas ni públicas).

### Modificación, estado y borrado
- RF-18: CUANDO el servicio de escritura modifica un bien, EL SISTEMA aplica las mismas validaciones de RF-2 a RF-14.
- RF-19: CUANDO el propietario activa un bien pausado, EL SISTEMA lo deja en estado `active`; CUANDO pausa un bien activo, lo deja en estado `paused`.
- RF-20: SI se intenta cambiar el propietario de un bien ya creado, ENTONCES EL SISTEMA rechaza el cambio. La categoría sí puede cambiarse.
- RF-21: SI se intenta borrar un usuario que tiene bienes, ENTONCES EL SISTEMA rechaza el borrado.
- RF-22: SI se intenta borrar una categoría que tiene bienes, incluido al revertir la migración de la semilla de la spec 004, ENTONCES EL SISTEMA rechaza el borrado sin borrar ninguna categoría.

### Función de aproximación
- RF-23: EL SISTEMA dispone de una función de aproximación que, dadas una coordenada válida (latitud de -90 a 90 y longitud de -180 a 180) y un radio de privacidad admitido, devuelve el centro de la celda de la cuadrícula que contiene la coordenada. La función no comprueba la caja de coherencia; eso lo hace la validación del bien (RF-14).
- RF-24: EL SISTEMA garantiza que la función de aproximación es determinista: la misma coordenada y el mismo radio dan siempre el mismo resultado, sin depender de la hora, del azar ni de datos guardados.
- RF-25: EL SISTEMA garantiza que, medida en la proyección de la cuadrícula, la distancia entre la coordenada original y el resultado no supera 0,71 × radio (la mitad de la diagonal de la celda).
- RF-26: EL SISTEMA garantiza que la distancia geodésica entre la coordenada original y el resultado no supera el radio de privacidad, de modo que la ubicación exacta queda siempre dentro del círculo de ese radio centrado en la ubicación pública.
- RF-27: EL SISTEMA garantiza que el lado de una celda medido en el terreno (distancia geodésica) está entre el 95 % y el 105 % del radio nominal en cualquier punto de la caja de coherencia, para los tres radios.
- RF-28: EL SISTEMA garantiza que dos coordenadas de la misma celda dan el mismo resultado.
- RF-29: EL SISTEMA garantiza que aplicar la función a su propio resultado con el mismo radio devuelve ese mismo resultado.
- RF-30: EL SISTEMA garantiza que la cuadrícula es anidada: el resultado con radio 500 pertenece a la misma celda de 1000 y de 2000 que la coordenada original, y el resultado con radio 1000 pertenece a la misma celda de 2000.
- RF-31: SI el radio no es 500, 1000 o 2000, o la coordenada no es válida, ENTONCES la función de aproximación falla con un error y no devuelve ningún valor.

### Ubicación pública y servicio de escritura
- RF-32: EL SISTEMA expone el servicio de escritura de bienes como la única función de escritura de bienes del dominio; es el único que calcula la ubicación pública.
- RF-33: CUANDO el servicio de escritura guarda un bien, EL SISTEMA fija su ubicación pública como el resultado de la función de aproximación aplicada a la ubicación exacta y al radio guardados, y sustituye cualquier ubicación pública recibida por la derivada.
- RF-34: SI una modificación no cambia la ubicación exacta ni el radio, ENTONCES EL SISTEMA no cambia la ubicación pública.
- RF-35: CUANDO el servicio de escritura modifica un bien, EL SISTEMA lo hace en una única transacción atómica que bloquea la fila del bien, de modo que dos modificaciones simultáneas no dejan una ubicación pública derivada de valores obsoletos.
- RF-36: EL SISTEMA guarda la ubicación exacta y la pública en campos separados, y la pública nunca queda vacía.

### Errores y logs
- RF-37: EL SISTEMA no incluye coordenadas (exactas ni públicas) en ningún error de validación que devuelve ni en ningún registro de log que emite la aplicación.
- RF-38: CUANDO la base de datos rechaza un bien por una restricción, la capa que guarda bienes captura el error de integridad dentro de una transacción atómica y lo traduce a un código de error sin valores, sin propagarlo crudo ni registrarlo (el detalle de PostgreSQL contiene la fila completa).

## Requisitos no funcionales
- **Permisos**: esta spec no expone endpoints, así que no hay accesos de anónimo, usuario ni propietario que declarar aquí. Las specs de API los declaran según las "Reglas para specs posteriores".
- **Arquitectura (constitución, punto 3)**: el cálculo de la ubicación pública vive en la función de aproximación (pura) y en el servicio de escritura de bienes. No vive en el guardado del modelo, porque `QuerySet.update()` y `bulk_create()` se lo saltan.
- **Desconfianza de la entrada (constitución, punto 6)**: reparto del rechazo entre la validación y la base de datos:
  - En validación y en la base de datos: rango del precio, radio en {500, 1000, 2000}, moneda EUR, unidad, estado, longitudes de título y descripción contadas en caracteres, rangos de latitud y longitud, y ubicación pública no vacía.
  - Solo en validación: caja de coherencia, recorte, caracteres de control, precisión del precio y propietario inmutable.
- **Errores**: cada rechazo en validación lleva un código de error estable en inglés y el campo afectado, no un mensaje en castellano; el cliente traduce los códigos.
- **Rendimiento**: la función de aproximación no consulta la base de datos ni la red.
- **Dependencias**: la proyección se calcula con lo que ya trae el stack geoespacial (GDAL de `django.contrib.gis`), sin dependencias nuevas.
- **Fechas**: todas con zona horaria, en UTC como referencia (RF-29 y RF-30 de la 001).
- **Idioma**: identificadores y valores almacenados en inglés (constitución, punto 8).

## Reglas para specs posteriores
- **Privacidad de la ubicación (API, búsqueda, mapa y reservas)**:
  - La ubicación pública es la única que se muestra o se usa para buscar, filtrar, ordenar o calcular distancias, para todos los anunciantes (particulares o profesionales).
  - La ubicación exacta solo la reciben el propietario del bien, que la ve y la edita en sus propios bienes, y el arrendatario con reserva confirmada. Nadie más la recibe (ni el anónimo ni otros usuarios), ni en detalle, ni en listados, ni en mensajes de error.
  - El acceso del arrendatario a la exacta caduca: la spec de reservas debe definir obligatoriamente hasta cuándo dura y quién lo revoca.
- **Serialización (API)**: los bienes se serializan con una lista blanca de campos; nunca con todos los campos ni por exclusión.
- **Autorización por objeto (API)**: 404 si el usuario no puede ver el bien; 403 si puede verlo pero no modificarlo (constitución, punto 5).
- **Bienes pausados (búsqueda y API)**: un bien `paused` no aparece en búsquedas ni listados públicos, y su detalle da 404 a todos salvo a su propietario, igual que un bien inexistente.
- **Mapa (búsqueda y frontend)**: la ubicación pública se dibuja como un círculo de radio igual al radio de privacidad alrededor de la ubicación pública, sin marcador central. Por RF-26 la exacta queda siempre dentro.
- **Cambios de la pública (frontend)**: cuando cambia la ubicación pública de un bien activo (por mover la exacta a otra celda, ampliar o reducir el radio), la interfaz avisa al anunciante de que quien vio el anuncio antes ya conoce la zona anterior.
- **Escrituras de bienes (todas)**: cualquier funcionalidad que cree o modifique bienes usa el servicio de escritura de bienes. Ninguna escribe la ubicación exacta, el radio ni la pública por otra vía.

## Casos límite
- Título formado solo por espacios: tras recortar queda vacío y se rechaza (RF-3).
- Título de 2 o de 101 caracteres: se rechaza; de 3 y de 100: se acepta (RF-3).
- Descripción de 19 o de 2001 caracteres recortados: se rechaza; de 20 y de 2000: se acepta (RF-4). El texto se guarda tal cual, recortado: escapar HTML es cosa del cliente.
- Precio `0`, `0.00`, `-5`, `100000` o `12.345`: se rechaza; `0.01` y `99999.99`: se acepta. `NaN`, `Infinity` y `12,50` con coma: se rechaza (RF-5).
- Moneda `usd` o `eur` en minúsculas: se rechaza; solo vale `EUR` (RF-7).
- Radio `0`, `-500`, `1500` o `500.5`: se rechaza (RF-10).
- Bien creado sin estado: nace `paused` (RF-11).
- Latitud y longitud intercambiadas (por ejemplo, latitud -3,7 y longitud 40,4): queda fuera de la caja de coherencia y se rechaza (RF-14).
- Latitud 91, longitud 181 o coordenadas no finitas: se rechaza (RF-13).
- Coordenada en Lisboa, Andorra o Toulouse: está dentro de la caja y se acepta (RF-14).
- Coordenada exactamente en un límite de la caja: se acepta, porque los límites están incluidos (RF-14).
- Coordenada en una esquina de la caja cuyo centro de celda cae fuera de ella: la función devuelve ese centro igualmente, porque solo la validación del bien comprueba la caja (RF-23, RF-29).
- Bien en Canarias o Baleares: se acepta (RF-14), y el lado real de la celda allí está entre el 95 % y el 105 % del nominal (RF-27).
- Punto exactamente en el borde entre dos celdas: pertenece a una sola por la convención de bordes, y el resultado es siempre el mismo (RF-23, RF-24).
- Punto en la esquina de su celda: queda a 0,71 × radio de la pública en la proyección, dentro del círculo del mapa (RF-25, RF-26).
- Dos bienes con la misma celda y el mismo radio: comparten ubicación pública; agruparlos es cosa del mapa (RF-28).
- El anunciante mueve la exacta dentro de la misma celda: la pública no cambia y no se revela nada nuevo (RF-34).
- El anunciante mueve la exacta a otra celda o cambia el radio: la pública cambia en el mismo guardado (RF-33) y la interfaz debe avisar (Reglas para specs posteriores).
- Se pide al servicio guardar un bien con una pública manipulada: se sustituye por la derivada (RF-33).
- Dos modificaciones simultáneas del mismo bien, una de la exacta y otra del radio: la segunda espera al bloqueo y la pública final deriva de los valores finales (RF-35).
- Se intenta cambiar el propietario de un bien: se rechaza (RF-20).
- Borrar una categoría o un usuario con bienes, o revertir la semilla con bienes: se rechaza (RF-21, RF-22).
- Un CHECK de la base de datos rechaza un bien: el error devuelto y el log no contienen la fila ni las coordenadas (RF-37, RF-38).

## Fuera de alcance
- Endpoints, serializers, autenticación y sesiones (specs de autenticación y de API).
- Fotos y almacenamiento de imágenes.
- Campos propios de cada tipo de bien (plazas, eslora, capacidad…).
- Otras monedas y otras unidades de precio (semana, mes, noche).
- Disponibilidad, calendario, reservas, fianzas y precios por temporada (spec de reservas).
- Búsqueda por radio, filtros, ordenación, distancia redondeada, radio mínimo de búsqueda y agrupación de marcadores (spec de búsqueda).
- Geocodificación de direcciones: el sistema recibe coordenadas ya resueltas.
- Restringir las ubicaciones por país o por frontera administrativa: la caja de coherencia no lo hace y no está en el MVP.
- Radio de privacidad personalizado, ubicación exacta pública para profesionales y cualquier otra excepción a la regla de privacidad.
- Panel de administración.

## Riesgos aceptados por el usuario
- La incertidumbre real es el cuadrado de la celda, no el círculo: quien conoce la cuadrícula sabe que la exacta está en ese cuadrado. En zonas rurales una celda puede contener una sola vivienda.
- Pausar no es retroactivo: quien vio la zona antes la sigue conociendo.
- La ubicación exacta queda en claro en la base de datos, en los backups y para los superusuarios hasta que llegue el borrado RGPD.
- Varios bienes en la misma dirección con radios distintos: las celdas anidadas se intersecan y la privacidad efectiva es la del radio menor.
- Formatos poco comunes del precio (`1e2`, `+5`, ceros a la izquierda) quedan a la validación de tipo, sin RF propio.
- Las fechas de creación y modificación no entran como parámetro.

## Restricciones de implementación pedidas por el usuario
- El usuario escribe los modelos y la función de aproximación; Claude escribe las migraciones y los tests, y revisa línea a línea el código del usuario.
- El precio se guarda como DecimalField; las ubicaciones, como geography de PostGIS.
- El recálculo de la ubicación pública vive en el servicio de escritura de bienes, no en el guardado del modelo.

## Criterios de finalización
- Cada RF tiene un test automático. Esta spec no tiene interfaz, así que no hay comprobaciones en navegador.
- RF-23 a RF-31 se cubren con tests de propiedades sobre un conjunto de coordenadas que incluye las cuatro esquinas de la caja de coherencia, Canarias, Baleares, puntos en bordes y esquinas de celda y puntos aleatorios con semilla fija, para los tres radios.
- RF-27 se verifica midiendo en el terreno (distancia geodésica) el lado real de la celda en varios puntos de la caja, incluidos Canarias y Baleares, para los tres radios, y exigiendo entre el 95 % y el 105 % del radio nominal. Así se demuestra que EPSG:3035 sirve.
- Un test comprueba, tras crear y modificar bienes con el servicio de escritura, que la ubicación pública guardada coincide con la derivada de la exacta y el radio guardados (RF-33, RF-34).
- Un test comprueba que la representación textual de un bien contiene su título y su identificador y ninguna coordenada (RF-17).
- Un test provoca el fallo de un CHECK de la base de datos y comprueba que ni el error devuelto ni el log capturado contienen coordenadas (RF-37, RF-38).
- Las restricciones de base de datos se verifican con tests que guardan saltándose la validación y esperan un error de integridad.
- Un test revierte la semilla de la spec 004 con un bien que usa una de sus categorías y comprueba que falla sin borrar ninguna (RF-22).
- La suite de tests, el análisis estático y la comprobación de migraciones (RF-7 de la 002) están en verde.

## Dudas abiertas
- Pendiente de clarificación con los revisores (/sdd-clarify) antes de aprobarla. Recoge las decisiones tomadas durante la clarificación de la 004, antes de partirla.
