# Spec 001 — Esqueleto del backend
Estado: aprobada

## Contexto y objetivo
RentRadar no tiene código todavía. Antes de construir cualquier funcionalidad de negocio (bienes, búsqueda por radio, usuarios), hace falta una base de backend que:
- se arranque igual en cualquier máquina copiando una plantilla de variables y ejecutando una sola orden, e incluya una base de datos con capacidad geoespacial, porque la búsqueda por radio es el núcleo del producto;
- separe la configuración de desarrollo, test y producción, de modo que un despliegue mal configurado no arranque en vez de exponer secretos o trazas;
- fije desde el principio la zona horaria de referencia y el idioma por defecto, para que ningún modelo futuro nazca con fechas ambiguas;
- permita ejecutar con una orden la suite de tests y el análisis estático, que son la base del punto 4 de la constitución ("los tests son la puerta").

Orden de implementación: 001 (esta spec), 002 (comprobación previa al commit e integración continua) y 003 (comprobaciones de salud). El objetivo es que las specs siguientes solo tengan que añadir dominio, sin volver a decidir la infraestructura.

## Usuarios
- **Desarrollador del equipo**: arranca el entorno y ejecuta los tests y el análisis estático.
- **Operador del despliegue**: configura las variables de producción y necesita que una configuración insegura impida arrancar.

## Historias de usuario
- HU-1. Como desarrollador, quiero copiar la plantilla de variables y levantar el backend y su base de datos geoespacial con una sola orden, para empezar a trabajar sin configurar nada más a mano.
- HU-2. Como desarrollador, quiero que cada entorno tenga su configuración, para trabajar con depuración en local sin que llegue nunca a test ni a producción.
- HU-3. Como operador del despliegue, quiero que producción se niegue a arrancar si su configuración falta, está mal formada o es insegura, y que me diga qué variable revisar sin mostrar su valor, para no exponer secretos ni trazas por un descuido.
- HU-4. Como desarrollador, quiero ejecutar los tests y el análisis estático sin indicar el entorno ni arriesgar la base de datos de desarrollo, para comprobar mi trabajo antes de cada commit.

## Definiciones
- **Entorno**: el modo de ejecución. Sus valores son los identificadores `development`, `test` y `production`, escritos exactamente así. Decide qué configuración se aplica. Un entorno de preproducción es producción con otras variables, no un cuarto entorno.
- **Arrancar**: levantar el servidor de la aplicación o ejecutar cualquier orden de gestión de la aplicación. Las validaciones de configuración se aplican en ambos casos.
- **Variables obligatorias de producción**: la clave secreta, la lista de hosts permitidos y los cinco datos de conexión a la base de datos (host, puerto, nombre, usuario y contraseña).
- **Variable vacía**: una variable definida pero sin contenido, o solo con espacios. Cuenta como ausente.
- **Valor booleano**: `true`, `false`, `1` o `0`, sin distinguir mayúsculas. Cualquier otro valor es no booleano.
- **Host válido**: un nombre de dominio (`example.com`), un dominio con punto inicial que cubre sus subdominios (`.example.com`) o una dirección IP.
- **Plantilla de variables**: el fichero versionado que documenta las variables de entorno con valores de ejemplo no secretos.
- **Fichero de variables local**: cualquier fichero con valores reales de variables de entorno, sea cual sea la variante de su nombre. Nunca se versiona.

## Requisitos funcionales

### Entorno local
- RF-1: CUANDO el desarrollador copia la plantilla de variables como fichero de variables local y arranca el entorno local con una sola orden, EL SISTEMA levanta la aplicación y una base de datos con capacidad geoespacial, y la aplicación queda lista para recibir peticiones.
- RF-2: CUANDO se detiene y se vuelve a arrancar el entorno local, EL SISTEMA conserva los datos de la base de datos.
- RF-3: SI la base de datos tarda más que la aplicación en estar lista al arrancar, ENTONCES EL SISTEMA no da el arranque por fallido y la aplicación espera a que la base de datos esté disponible.
- RF-4: SI la base de datos no está disponible 60 segundos después de que la aplicación empiece a arrancar, ENTONCES EL SISTEMA da el arranque por fallido e indica que la causa es la base de datos, sin mostrar credenciales.
- RF-5: MIENTRAS el entorno sea `development` o `test`, EL SISTEMA dispone de una base de datos capaz de calcular, en metros, la distancia geodésica entre dos coordenadas (latitud y longitud).
- RF-6: EL SISTEMA ejecuta el proceso de la aplicación sin privilegios de administrador dentro de su contenedor.
- RF-7: MIENTRAS el entorno local esté en marcha, EL SISTEMA expone los puertos de la aplicación y de la base de datos solo en la interfaz local de la máquina.
- RF-8: EL SISTEMA excluye del control de versiones cualquier fichero de variables local, salvo la plantilla de variables.

### Configuración por entorno
- RF-9: EL SISTEMA elige su configuración entre `development`, `test` y `production` a partir de una variable de entorno, sin cambiar código.
- RF-10: SI al arrancar no se indica el entorno o su valor no es uno de los tres admitidos, ENTONCES EL SISTEMA no arranca e indica cuáles son los valores válidos.
- RF-11: SI en `production` faltan o están vacías una o varias variables obligatorias, ENTONCES EL SISTEMA no arranca y su mensaje nombra todas las que faltan, sin mostrar el valor de ninguna variable.
- RF-12: SI en `production` una variable obligatoria tiene un valor mal formado (por ejemplo, un puerto no numérico o fuera del rango 1-65535), ENTONCES EL SISTEMA no arranca y nombra la variable sin mostrar su valor.
- RF-13: SI en `production` la clave secreta tiene menos de 50 caracteres, ENTONCES EL SISTEMA no arranca y lo indica sin mostrar la clave.
- RF-14: SI en `production` la clave secreta o la contraseña de la base de datos contiene `insecure-`, ENTONCES EL SISTEMA no arranca y nombra la variable sin mostrar su valor.
- RF-15: SI en `production` la lista de hosts permitidos contiene `*` o un valor que no sea un host válido, ENTONCES EL SISTEMA no arranca y nombra la variable sin mostrar su valor.
- RF-16: MIENTRAS el entorno sea `production`, SI llega una petición dirigida a un host que no está en la lista de hosts permitidos, ENTONCES EL SISTEMA la rechaza como petición incorrecta.
- RF-17: MIENTRAS el entorno sea `test`, EL SISTEMA usa una base de datos propia, distinta de la de desarrollo, que se crea al empezar la ejecución de los tests y se descarta al terminar.

### Modo de depuración
- RF-18: MIENTRAS el entorno sea `development`, EL SISTEMA activa o desactiva el modo de depuración según una variable de entorno, que la plantilla de variables trae activada.
- RF-19: MIENTRAS el entorno sea `test` o `production`, EL SISTEMA mantiene desactivado el modo de depuración, aunque la variable de entorno intente activarlo.
- RF-20: SI la variable del modo de depuración tiene un valor no booleano, ENTONCES EL SISTEMA no arranca y nombra la variable.

### Errores y cookies en producción
- RF-21: MIENTRAS el entorno sea `production`, SI una petición termina en una respuesta de error (petición incorrecta, no encontrado, método no permitido o error del servidor), ENTONCES EL SISTEMA responde con un mensaje genérico sin trazas, rutas de ficheros, consultas ni valores de configuración.
- RF-22: MIENTRAS el entorno sea `production`, SI se produce un error no controlado, ENTONCES EL SISTEMA lo registra en el log del servidor sin incluir la clave secreta ni la contraseña de la base de datos.
- RF-23: MIENTRAS el entorno sea `production`, EL SISTEMA envía las cookies de sesión y de protección contra falsificación de peticiones (CSRF) solo por conexiones cifradas.
- RF-24: EL SISTEMA marca la cookie de sesión como no accesible desde scripts del navegador.
- RF-25: EL SISTEMA aplica a las cookies de sesión y de protección contra falsificación de peticiones una política que no las envía en peticiones de otros sitios salvo en la navegación de nivel superior.

### Plantilla de variables
- RF-26: EL SISTEMA incluye en el repositorio una plantilla de variables con todas las variables de entorno que lee el backend, cada una con su descripción.
- RF-27: EL SISTEMA trae en la plantilla de variables valores de ejemplo legibles y no aleatorios; los de la clave secreta y la contraseña de la base de datos contienen `insecure-` (por ejemplo, `insecure-dev-only-not-a-secret`).
- RF-28: EL SISTEMA separa en la plantilla de variables, en un bloque comentado como ajeno al backend, las variables que usan otras herramientas del proyecto.

### Hora e idioma
- RF-29: EL SISTEMA guarda y maneja todas las fechas y horas con zona horaria explícita.
- RF-30: EL SISTEMA usa UTC como zona horaria de referencia en todos los entornos.
- RF-31: EL SISTEMA usa el castellano como idioma por defecto.
- RF-32: EL SISTEMA tiene activada la capacidad de traducir textos a otros idiomas.

### Tests y análisis estático
- RF-33: CUANDO el desarrollador ejecuta la suite de tests sin indicar el entorno, EL SISTEMA selecciona el entorno `test`, la ejecuta contra la base de datos geoespacial de test y termina con un código de salida distinto de cero si algún test falla.
- RF-34: MIENTRAS se ejecuta la suite de tests, EL SISTEMA no usa la base de datos de desarrollo, aunque el fichero de variables local o la variable de entorno indiquen otro entorno.
- RF-35: CUANDO el desarrollador ejecuta el análisis estático, EL SISTEMA revisa el estilo, los errores comunes y el formato del código del backend sin necesidad de indicar el entorno ni de cargar la aplicación, y termina con un código distinto de cero si encuentra alguna infracción.

## Requisitos no funcionales
- **Permisos**: esta spec no expone endpoints propios, así que no hay accesos de anónimo, usuario ni propietario que declarar. Las comprobaciones de salud están en la spec 003.
- **Seguridad**: los secretos solo llegan por variables de entorno (constitución, punto 6). Ningún mensaje de arranque, de error ni del log muestra el valor de una variable obligatoria.
- **Reproducibilidad**: las dependencias quedan fijadas en versiones exactas con hashes de integridad, y dos instalaciones desde cero producen el mismo conjunto.
- **Aislamiento de los tests**: ningún test accede a la red externa.
- **Idioma**: código, identificadores y commits en inglés; mensajes al desarrollador, comentarios y documentación en castellano (constitución, punto 8).

## Casos límite
- Una variable obligatoria está definida pero vacía o solo con espacios: cuenta como ausente (RF-11).
- Faltan varias variables obligatorias a la vez: el mensaje las nombra todas, no solo la primera (RF-11).
- El puerto de la base de datos es `abc`, `0` o `70000`: no arranca (RF-12).
- La clave secreta de producción tiene 50 o más caracteres pero contiene `insecure-`: no arranca (RF-14).
- La contraseña de la base de datos de producción es la de la plantilla: contiene `insecure-` y no arranca (RF-14).
- La lista de hosts permitidos tiene espacios o elementos vacíos: se ignoran los vacíos, y si no queda ninguno, cuenta como ausente (RF-11).
- La lista de hosts permitidos contiene `.example.com`: se acepta. Si contiene `*` o `http://example.com`: no arranca (RF-15).
- El entorno vale `Production` o `prod`: no es un valor admitido y no arranca (RF-10).
- La variable de depuración vale `yes` o `on`: no arranca en ningún entorno (RF-20).
- La variable de depuración falta o está vacía: cuenta como ausente y el modo de depuración queda desactivado, también en `development` (RF-18).
- La suite de tests se lanza con el fichero de variables local en `development`: se ejecuta en `test` y no toca la base de datos de desarrollo (RF-33, RF-34).
- Queda una base de datos de test de una ejecución abortada: la siguiente ejecución la sustituye sin intervención del desarrollador (RF-17).
- Los datos de la base de datos local solo se pierden con un borrado explícito de sus datos persistentes por parte del desarrollador, nunca al detener o reiniciar el entorno (RF-2).
- Hay un fichero de variables local con otra variante de nombre (por ejemplo, con sufijo de entorno): tampoco entra en git (RF-8).
- La plantilla de variables contiene variables de otras herramientas del proyecto: el test que compara las variables leídas con las de la plantilla las ignora (RF-26, RF-28).
- La detección de secretos de la spec 002 no marca la plantilla, porque sus valores son legibles y no aleatorios (RF-27).

## Fuera de alcance
- Frontend (irá en su propia spec).
- Modelos de dominio, autenticación, usuarios y permisos por objeto.
- **Spec 002**: la comprobación automática antes de cada commit (análisis estático, formato y detección de secretos), la integración continua y el criterio de no ejecutar los tests antes del commit.
- **Spec 003**: las comprobaciones de salud (vida y preparación).
- Despliegue real y alojamiento. **Van como requisitos de la spec de despliegue**: la imagen y el servidor de aplicación de producción, los ficheros estáticos, aplicar las migraciones al arrancar o antes de enviar tráfico, la redirección a HTTPS, HSTS, la cabecera de confianza del proxy que termina TLS y que la comprobación de seguridad de despliegue del framework pase sin avisos en integración continua. Si TLS termina en un proxy, esa spec debe garantizar que la aplicación reconozca la conexión como cifrada, para que RF-23 funcione de punta a punta.
- La conversión de fechas y horas a la hora local, que le corresponde al cliente, y la negociación del idioma por cabecera de la petición.
- Textos traducidos en las respuestas de la API. Solo se activa la capacidad (RF-32).
- Límites de tasa: necesitan una caché compartida, que es una dependencia nueva.
- Métricas, trazas distribuidas y alertas.
- Panel de administración expuesto.
- Documentación generada de la API y CORS.
- Comprobación de tipos estática.
- Almacenamiento de imágenes, geocodificación y colas de tareas.

## Criterios de finalización
- Cada RF tiene un test automático o una comprobación registrada en la validación:
  - Comprobación registrada: RF-1 (clon nuevo, copiar la plantilla y una orden), RF-2 (reiniciar el entorno y los datos siguen), RF-3 (la aplicación arranca antes que la base de datos), RF-6 (usuario del proceso en el contenedor), RF-7 (puertos publicados solo en la interfaz local) y RF-8 (comprobación de ficheros ignorados por git sobre varias variantes de nombre y sobre la plantilla).
  - Test automático: el resto. RF-26 se cubre con un test que compara las variables que lee el backend con las de la plantilla. RF-22, con un test que provoca un error no controlado con una contraseña conocida y comprueba que no aparece en el log.
- La suite de tests (RF-33) y el análisis estático (RF-35) están en verde en local.
- Con la configuración de producción sin variables obligatorias, la aplicación no arranca y nombra todas las que faltan.
- El plan cabe en 10 tareas como máximo.

## Dudas abiertas
- [NECESITA ACLARACIÓN] (pendiente para la primera spec con formularios, no bloquea esta) ¿El backend devuelve los mensajes de error ya traducidos o devuelve códigos de error que traduce el cliente?
