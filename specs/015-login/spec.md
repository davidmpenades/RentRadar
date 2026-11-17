# Spec 015 — Entrada
Estado: borrador
Depende de: spec 004 (usuarios y normalización del email), spec 009 (registro, sesión, salida, CSRF, límites y formato de errores) y spec 016 (campos, «Mostrar contraseña» y botones).

## Contexto y objetivo
Desde la 009 un visitante puede crear una cuenta y salir, pero quien sale no puede volver a entrar. Esta spec entrega la entrada de punta a punta: la operación de la API, sus dos límites de intentos, el enlace «Entrar» en la barra superior y la página `/login`.

La entrada es la operación más expuesta a la adivinación de contraseñas y a la enumeración de cuentas. Por eso:
- responde igual a todas las causas de fallo;
- calcula el hash de la contraseña el mismo número de veces exista o no la cuenta;
- limita los intentos por IP y por el par IP y email, sin que nadie pueda bloquear la cuenta de otra persona;
- no guarda el email en ningún contador ni en los logs.

## Usuarios
- **Visitante**: sin sesión; entra con su email y su contraseña.
- **Usuario**: con sesión; puede volver a entrar con la misma cuenta o con otra, y la sesión anterior se sustituye.
- **Cuenta desactivada**: no entra; recibe el mismo error que unas credenciales incorrectas.
- **Staff y superusuario**: entran como cualquier usuario, sin capacidades distintas en esta spec.
- **Desarrollador del equipo**: prueba el flujo en el navegador y ejecuta los tests.

## Historias de usuario
- HU-1. Como usuario que ha salido, quiero volver a entrar con mi email y mi contraseña, para seguir usando mi cuenta.
- HU-2. Como titular de una cuenta, quiero que la entrada no revele si mi email está registrado y que nadie pueda probar contraseñas sin límite, para que mi cuenta no sea un blanco fácil.
- HU-3. Como titular de una cuenta, quiero que los intentos fallidos de otra persona no me impidan entrar desde mi conexión, para no quedarme fuera por culpa de otro, mientras no haya un proxy delante; con proxy, lo resuelve la 011.
- HU-4. Como visitante, quiero pasar de la entrada al registro y al revés con un enlace, para no buscar la otra página.

## Definiciones
- **Credenciales**, **email normalizado**, **sesión**, **token CSRF**, **«quién soy»**, **barra superior** e **IP del visitante**: las de la 009. La IP del visitante agrupa las direcciones IPv6 por su prefijo /64.
- **Entrada fallida**: una petición que pasa el límite por IP y email y recibe `credentials_invalid`, haya habido o no búsqueda de la cuenta y cálculo del hash. No lo son las rechazadas antes: por un límite, por método, por CSRF o por la forma del cuerpo.
- **Email no consultable**: ausente, nulo, vacío tras recortar, con un carácter nulo o con un sustituto Unicode suelto. Cualquier otro texto se normaliza y se busca, aunque no tenga forma de email: si no existe, es un email desconocido.
- **Contraseña no comprobable**: ausente, nula, vacía, de más de 128 puntos de código o con un sustituto Unicode suelto. Una contraseña con un carácter nulo sí se comprueba.
- **Ventana deslizante**: una petición cuenta durante el periodo del límite contado desde que se anotó; no hay un reinicio a hora fija.
- **Tiempo de espera**: los segundos enteros, como mínimo 1, que faltan para que el número de peticiones anotadas en la ventana baje del límite. Si hay más anotaciones que el límite, por ejemplo por peticiones simultáneas, cuenta desde la anotación que deja el número por debajo del límite, no desde la más antigua. El cliente lo muestra en minutos redondeados hacia arriba, como mínimo 1, como en la 009.

### Valores de esta spec
| Valor | Fijado |
|---|---|
| Límite de entrada por IP | 20 peticiones por minuto, ventana deslizante |
| Límite de fallos por IP y email | 5 entradas fallidas en 15 minutos, ventana deslizante |
| Tamaño máximo del cuerpo | 4096 bytes, como el registro |
| Longitud máxima de la contraseña comprobada | 128 puntos de código |
| Tiempo máximo de la entrada en el cliente | 10 s («quién soy», 5 s, como en la 009) |
| Almacén de los dos contadores | propio de la entrada y compartido por los dos límites, en memoria y por proceso, con capacidad para 20 000 entradas |

## Requisitos funcionales

### Operación de entrada
- RF-1: CUANDO un visitante envía el email y la contraseña de una cuenta activa, EL SISTEMA abre una sesión y responde 200 con `{"user": {"email": "<email de la cuenta>"}}`, la misma forma que «quién soy» con sesión. El email recibido se compara normalizado: `  Ana@Correo.ES ` entra en la cuenta `ana@correo.es`.
- RF-2: SI las credenciales no abren sesión, ENTONCES EL SISTEMA responde 400 con `{"code": "invalid_fields", "params": {"non_field": ["credentials_invalid"]}}`, idéntico en estado, cuerpo y cabeceras para todas estas causas, salvo la fecha y el saneamiento de cookies mal formadas de RF-5:
  - email desconocido, no consultable o sin forma de email;
  - contraseña errónea o no comprobable;
  - cuenta desactivada.

  Una contraseña de más de 128 puntos de código se rechaza sin calcular el hash. Ningún contenido del email ni de la contraseña, incluidos el nulo y los sustitutos sueltos, produce un error del servidor.
- RF-3: SI una IP supera las 20 peticiones de entrada en un minuto, ENTONCES EL SISTEMA responde con el error de límite superado de la 009 (429 con `{"code": "throttled", "retry_after": N}` y la cabecera `Retry-After` con el mismo N), donde N es el tiempo de espera, sin comprobar las credenciales ni tocar la sesión. Cuenta toda petición que este límite deja pasar, sea cual sea su resultado (también los rechazos por el límite de RF-4); las que rechaza él mismo no cuentan ni alargan la espera.
- RF-4: SI un par de IP y email normalizado acumula 5 entradas fallidas en 15 minutos, ENTONCES EL SISTEMA rechaza las siguientes peticiones de ese par con el mismo error de límite superado y su tiempo de espera, también cuando la contraseña es correcta, sin comprobar las credenciales ni tocar la sesión.
  - Cuentan todas las entradas fallidas, también las de un email no consultable; para la clave, un email ausente o nulo cuenta como texto vacío. El fallo se anota después de comprobar las credenciales, y un rechazo por este límite no anota un fallo.
  - Un acierto no reinicia el contador: los fallos anteriores siguen contando hasta que salen de la ventana.
  - El contador de un par no afecta al mismo email desde otra IP.
- RF-5: CUANDO la entrada tiene éxito, EL SISTEMA descarta siempre la sesión anterior del navegador, sea anónima, de otra cuenta o de la misma, y crea una con identificador nuevo y token CSRF nuevo. SI la entrada no tiene éxito, por cualquier motivo, ENTONCES EL SISTEMA no modifica la sesión actual; las cookies solo cambian si llegan mal formadas, por el saneamiento que el sistema aplica a cualquier petición, igual en todas las causas de RF-2.
- RF-6: SI una petición de entrada no lleva un token CSRF válido, ENTONCES EL SISTEMA la rechaza con `csrf_failed` antes de leer el cuerpo; SI el cuerpo no es un objeto JSON válido o lleva el email o la contraseña con un tipo que no es texto ni nulo, ENTONCES la rechaza con `invalid_request`; y SI declara o aporta más de 4096 bytes o llega troceado, ENTONCES la rechaza con `payload_too_large`, con la misma precedencia entre estos rechazos que el registro de la 009. En los tres casos no comprueba las credenciales, no anota un fallo de RF-4 y no toca la sesión. Los campos desconocidos se ignoran. Las respuestas de la entrada llevan `Cache-Control: no-store` como en la 009: errores incluidos, salvo los errores del servidor y la redirección por barra final.

### Interfaz
- RF-7: MIENTRAS no hay sesión, la barra superior muestra «Entrar» (botón secundario) y «Registrarse» (principal) juntos, en ese orden, y ninguno de los dos desborda la barra a 375 px. Mientras el cliente aún no sabe si hay sesión no muestra acciones, y con sesión muestra solo «Salir», como en la 009. Tras salir, el foco va a «Entrar».
- RF-8: CUANDO el visitante envía el formulario de entrada, EL SISTEMA se comporta como el formulario de registro de la 009 salvo en lo que se fija aquí:
  - si el email, tras recortar, o la contraseña están vacíos, no envía nada y marca cada campo vacío, como el registro;
  - mientras la petición está en curso, bloquea un segundo envío, deja el botón de envío «Entrar» (principal) como no disponible y los campos en solo lectura, y los libera al terminar;
  - si se abre la sesión, lo lleva al mapa sin añadir una entrada al historial, con la barra en «Salir», y anuncia «Has entrado.»; la siguiente petición que cambia el estado lleva ya el token CSRF nuevo;
  - SI las credenciales son incorrectas, ENTONCES muestra «El email o la contraseña no son correctos.», conserva el email y borra la contraseña;
  - SI se supera un límite, ENTONCES muestra «Demasiados intentos. Inténtalo de nuevo en N minutos.», como en la 009, y conserva los dos campos;
  - SI la respuesta de éxito tiene una forma inválida, o la petición falla o vence a los 10 s, ENTONCES pregunta «quién soy»: con sesión continúa como un éxito y, sin ella, muestra el error general del registro, conserva los dos campos y permite reintentar. SI la respuesta de error trae un código desconocido o una forma inválida, o es un límite superado sin un tiempo de espera válido, ENTONCES muestra el error general del registro. Ante `csrf_failed` reintenta una sola vez tras preguntar «quién soy», como en la 009;
  - todo error que no es de un campo vacío lleva el foco a la región de estado y se anuncia una sola vez por petición.

  El éxito y la redirección de RF-9 son una sola navegación. «Has entrado.» solo se anuncia cuando la sesión la abre este envío o la encuentra la consulta de «quién soy» que sigue a un fallo o vencimiento de este envío. El formulario usa los campos, «Mostrar contraseña» y los botones de la 016. Enlaza con el registro («¿No tienes cuenta? Regístrate»), y el registro enlaza con la entrada («¿Ya tienes cuenta? Entra»). Tras entrar siempre se va al mapa: no hay parámetro de destino ni redirección configurable.
- RF-9: CUANDO se abre `/login`, EL SISTEMA muestra la página de entrada; `/login/` se normaliza a `/login`. MIENTRAS se resuelve «quién soy», muestra el formulario sin esperar, como `/register`; si hay sesión, o llega después, lleva al mapa sin añadir una entrada al historial.

## Requisitos no funcionales
- **Permisos (constitución, punto 5)**:
  - La entrada la usan el visitante y el usuario con sesión; para este, la sesión se sustituye (RF-5).
  - No acepta un identificador de usuario ni los campos `is_staff`, `is_superuser` o `is_active`: se ignoran. No hay recursos por identificador, así que no hay caso de 404 ni de 403 por objeto.
  - Solo admite POST. Otro método recibe el error de método no admitido, salvo con el límite de RF-3 superado.
- **Orden de comprobaciones**: límite por IP → método → CSRF → tamaño y forma del cuerpo → límite por IP y email → comprobación de credenciales → anotación del fallo o apertura de la sesión. Es el orden de la 009 con el límite del par en el primer punto en que se conoce el email.
- **Igualdad de tiempo**: con credenciales erróneas, la entrada calcula el hash de la contraseña exactamente una vez para un email desconocido consultable, una contraseña errónea, una cuenta desactivada y una cuenta con contraseña inutilizable. La única excepción es el rehash de una contraseña correcta guardada con un hash desactualizado (Riesgos aceptados). Que se calcule o no depende solo de la forma de lo recibido (email no consultable, contraseña no comprobable), nunca de si la cuenta existe: un rechazo sin hash solo le dice a quien envía lo que ya sabe de su propia entrada. La normalización del email se aplica a todo email consultable antes de buscarlo, exista o no la cuenta.
- **Respuestas mínimas**: el éxito lleva solo el email de la propia cuenta, nunca un identificador, `is_staff`, `is_superuser`, `last_login` ni la fecha de alta, también con una cuenta de staff.
- **Privacidad y logs**: ni el email ni la contraseña aparecen en los logs, en las respuestas de error ni en la clave de ningún contador. La clave del límite de RF-4 se deriva, con un HMAC SHA-256 con el secreto del servidor y una sal propia de este límite, del mismo email normalizado que se busca; cambiar el secreto cambia la clave. Todo email, también uno no consultable, tiene su clave sin error del servidor.
- **Errores**: formato único de la 009. Código nuevo: `credentials_invalid`, en `params.non_field` de `invalid_fields`. Nunca incluyen el valor recibido. Un 401 añadiría una cabecera de autenticación y un 403 se confundiría con `csrf_failed`; por eso las credenciales incorrectas son un 400.
- **Validación en el cliente (constitución, punto 6)**: el cliente valida la forma de cada respuesta de la entrada, éxito y error, antes de usarla, con el mismo criterio que el registro de la 009 (RF-8).
- **Contrato**: la descripción de la API y los tipos del cliente se regeneran con la operación de entrada, y el control de desfase de la CI pasa.
- **Despliegue**: la entrada no se despliega antes de la 011, que fija el proxy de confianza (ver «IP compartida» en Riesgos aceptados). En desarrollo, el proxy de Vite hace que todas las peticiones compartan una IP, y es lo esperado.
- **Dependencias (constitución, punto 1)**: ninguna nueva.
- **Accesibilidad y móvil (constitución, punto 7)**, verificadas en el navegador (Criterios de finalización):
  - Se diseña a 375 px y se amplía a 1280 px. «Entrar», «Registrarse», los campos, el envío, «Mostrar contraseña» y los enlaces cruzados miden al menos 44 px.
  - Cada campo tiene su etiqueta y su autocompletado (email y contraseña actual) y no se bloquea pegar.
  - Una región de estado anuncia el envío («Entrando…») y cada error, una vez por petición; «Has entrado.» va a la región global, que sobrevive al cambio de página.
  - Uso completo con teclado, foco visible y contraste AA.
- **Idioma (constitución, punto 8)**: los textos salen del catálogo de mensajes en castellano; rutas y códigos en inglés.

## Decisiones de seguridad
- **Almacén de los contadores**: los dos límites de la entrada comparten un almacén propio en memoria con capacidad para 20 000 entradas, para que el tráfico del mapa y del registro no expulse sus contadores. Un test de configuración fija su capacidad. Contadores compartidos entre procesos y atómicos: spec 011.
- **Límite por IP y email, no solo por email**: un límite global por email permitiría a cualquiera bloquear la cuenta de otra persona con cinco intentos.
- **Señal de salida**: la salida de la 009 vacía la sesión sin emitir la señal de Django de «usuario ha salido», y la entrada que sustituye la sesión de otra cuenta tampoco la emite. Ningún código del proyecto la escucha y no se emite a mano. Se anota en `docs/architecture.md` y un test fija que la salida no la emite, para que quien añada un receptor sepa que no se llamará.
- **Señal de entrada fallida**: Django la emite con el email recibido (la contraseña va tapada). Ningún código del proyecto la escucha; el test de fugas cubre los receptores que existan cuando se ejecuta.

## Casos límite
- `  Ana@Correo.ES ` con la contraseña correcta de `ana@correo.es`: entra (RF-1). Las dos formas comparten el contador de RF-4.
- Email desconocido, vacío, ausente, nulo, sin arroba, con un nulo o con un sustituto suelto; contraseña errónea, vacía, de 129 puntos de código o con un sustituto suelto; cuenta desactivada con su contraseña correcta: la misma respuesta, sin error del servidor (RF-2).
- Email de texto largo dentro de los 4096 bytes del cuerpo: es consultable y desconocido, con la misma respuesta (RF-2).
- Contraseña de 128 puntos de código errónea: se comprueba y calcula el hash una vez; de 129: sin hash (RF-2).
- Contraseña con un carácter nulo: se comprueba como cualquier otra (RF-2).
- Email como número, contraseña como lista u objeto, cuerpo que no es JSON o que es una lista: `invalid_request`, sin anotar un fallo (RF-6).
- Campos añadidos como `is_staff: true` o `next`: se ignoran (RF-6).
- HEAD, OPTIONS u otro método distinto de POST: método no admitido, salvo con el límite de RF-3 superado; cuentan en RF-3 (RF-3).
- Cinco fallos de un par y, después, la contraseña correcta: límite superado, sin sesión. Pasados 15 minutos desde el primer fallo, entra (RF-4).
- Cuatro fallos, un acierto y un fallo más: el sexto intento recibe el límite superado, porque el acierto no reinicia el contador (RF-4).
- Siete fallos anotados por peticiones simultáneas: el tiempo de espera cuenta hasta que quedan menos de 5 en la ventana, no hasta que sale el más antiguo (RF-4).
- Cinco fallos con un email desde una IP: el mismo email entra desde otra IP que no comparta /64 (RF-4).
- Dos direcciones IPv6 del mismo /64 comparten los dos límites (RF-3, RF-4).
- Petición 21 de entrada en un minuto desde una IP, aunque sus credenciales sean correctas: límite superado. Un rechazo por RF-4 sí cuenta en RF-3; uno por RF-3 no cuenta en ninguno (RF-3).
- Petición sin token CSRF desde una IP que ya superó RF-3: error de límite, no de CSRF (RF-3, RF-6).
- Entrada con la sesión de otra cuenta abierta: la anterior se descarta, con identificador y token CSRF nuevos. Con la de la misma cuenta, o con una cuenta de staff, igual; la respuesta lleva solo el email (RF-5).
- Entrada con una cookie de sesión caducada o mal formada: con las credenciales correctas entra; con las erróneas recibe el mismo error, y el saneamiento de la cookie es igual en todas las causas (RF-2, RF-5).
- Entrada fallida o rechazada por un límite con una sesión válida abierta: la sesión sigue igual y no hay cookies nuevas (RF-5).
- Dos entradas simultáneas de la misma cuenta desde el mismo navegador: cada una crea su sesión y el navegador se queda con la de la última respuesta; la otra deja de usarse y caduca (RF-5).
- Cuerpo troceado o de 4097 bytes: `payload_too_large` (RF-6).
- Doble clic o doble Intro en «Entrar»: un solo envío (RF-8).
- La petición vence a los 10 s pero el servidor abrió la sesión: el cliente pregunta «quién soy» y continúa como un éxito (RF-8).
- Entrar y pulsar «Salir» a continuación: sale a la primera, sin `csrf_failed` ni reintento (RF-8).
- Pulsar «Atrás» tras entrar: no vuelve al formulario (RF-8).
- `/login?next=https://otro.sitio`: el parámetro se ignora y tras entrar se va al mapa (RF-8).
- Abrir `/login` con sesión, o que la sesión llegue después de pintar el formulario o durante un envío: va al mapa una sola vez, sin añadir historial (RF-8, RF-9).
- A 375 px la barra superior sin sesión muestra la marca, «Entrar» y «Registrarse» sin desbordar (RF-7).

## Fuera de alcance
- «¿Has olvidado tu contraseña?» y la recuperación de contraseña (spec 013).
- Textos legales en el formulario de entrada (spec 014).
- Fotos de fondo de las páginas de registro y entrada: spec posterior, antes de la 008.
- Parámetro de destino tras entrar o redirección configurable: se evita la redirección abierta.
- «Recuérdame», segundo factor, captcha, entrada con terceros, JWT y aplicación móvil.
- Aviso por correo de una entrada nueva, lista de sesiones abiertas y cerrar otras sesiones.
- Desbloqueo manual de un par bloqueado, y límites globales por email o por cuenta.
- Registro de eventos de seguridad (intentos fallidos y bloqueos) para detectar un ataque en curso: spec 011.
- Proxy de confianza, contadores compartidos y atómicos, y tope global del coste del hash (spec 011).
- Registro uniforme: llega con la 013 (ver «Riesgos aceptados»).

## Cambios en otras specs
Se hacen con `/sdd-change`, solo en el texto:
- **Spec 009, RF-9**: sin sesión, la barra muestra «Entrar» y «Registrarse» (RF-7 de esta spec).
- **Spec 009, RF-10**: el formulario de registro enlaza con la entrada («¿Ya tienes cuenta? Entra»).
- **Spec 009, RF-12**: tras salir, el foco va a «Entrar» en lugar de a «Registrarse».
- **Spec 016, Definiciones (Botón)**: «Entrar» de la barra superior es un botón secundario, y el envío «Entrar» del formulario de entrada es principal.
- **Spec 016, RF-4 y RF-5**: la región de estado del formulario de entrada se presenta como la del registro, con «Entrando…» como envío en curso.

## Riesgos aceptados
- **Enumeración por el registro**: el registro de la 009 devuelve `email_taken`, así que ya revela qué emails tienen cuenta, aunque la entrada no lo haga. Lo mitiga el límite de 10 registros por hora e IP; el arreglo llega con la 013.
- **IP compartida**: detrás de un proxy, o con una dirección vacía que cae en el cubo común, todas las peticiones comparten IP y el par IP y email queda en la práctica como solo el email: cualquiera bloquea la cuenta de otra persona con 5 intentos cada 15 minutos, y 20 peticiones por minuto bloquean toda la entrada. Por eso la entrada no se despliega antes de la 011, que fija el proxy de confianza. Un NAT tiene el mismo efecto a menor escala.
- **Muchas direcciones contra una cuenta**: un solo abonado IPv6 suele tener un /56 o un /48, de 256 a 65 536 bloques /64, y con cada uno obtiene 5 intentos por email y 20 hashes por minuto, sin necesidad de una red de equipos. Los límites no lo frenan, y la longitud mínima y la lista de contraseñas comunes de la 009 solo protegen a las cuentas creadas por el registro. La 011 lo revisa.
- **Carrera en paralelo**: el fallo se anota después del hash y ningún contador es atómico, así que varias peticiones simultáneas pueden superar los 5 fallos del par y las 20 peticiones de la IP. Lo acotan el número de procesos y el coste del hash.
- **Contadores en memoria y por proceso**: el límite efectivo se multiplica por el número de procesos y se pierde al reiniciar. Además, el propio tráfico de entrada puede llenar el almacén: rotando bloques /64 con emails nuevos, un atacante expulsa contadores, los suyos y los de otros. La 011 los hace compartidos y atómicos.
- **Coste del hash**: cada entrada consultable calcula un hash costoso; solo lo frena el límite por IP hasta el tope global de la 011.
- **Diferencias de tiempo residuales** entre una cuenta existente y otra que no (consulta a la base de datos, rehash de una contraseña correcta guardada con un hash desactualizado): se aceptan.
- **Sesión abierta en otra pestaña**: si la entrada falla o vence y otra pestaña ha abierto una sesión, el cliente continúa como un éxito y anuncia «Has entrado.», aunque la sesión sea de otra cuenta: el navegador ya tiene sesión.
- **Contraseña puesta desde el terminal**: la orden `changepassword` de Django aplica los validadores pero no el tope de 128 puntos de código; si el desarrollador pone una contraseña más larga, esa cuenta no podrá entrar. Solo afecta al desarrollador.

## Criterios de finalización
- Cada RF tiene un test automático: pytest en el backend, vitest para la lógica del cliente y comprobación en navegador para RF-7, RF-8 y RF-9, registrada en `validation.md`.
- **Pruebas de mecanismo** (la spec toca seguridad), cada una con una mutación que debe hacer fallar un test, registradas en `validation.md`:
  - respuesta idéntica en todas las causas de RF-2;
  - contraseña de más de 128 puntos de código sin hash, y hash calculado exactamente una vez con email desconocido consultable, contraseña errónea, cuenta desactivada y contraseña inutilizable, contado en el test;
  - cada límite, con su ventana deslizante y su tiempo de espera; el acierto que no reinicia el contador; el límite del par aunque la contraseña sea correcta; y el mismo email desde otra IP;
  - clave del contador sin el email y dependiente del secreto;
  - sesión nueva al entrar (identificador y token CSRF) y sesión intacta tras un fallo;
  - CSRF obligatorio y `no-store` en todas las respuestas que fija RF-6: éxito, credenciales incorrectas, los dos límites y los rechazos de RF-6; salvo los errores del servidor y la redirección por barra final;
  - la salida no emite la señal de «usuario ha salido».
- **Fugas**: un test con un email y una contraseña centinela, como `test_leaks.py`, comprueba que no aparecen en los logs, en las respuestas ni en las claves de los dos contadores.
- La suite de tests, el análisis estático, la comprobación de migraciones y el control de desfase del contrato están en verde. Frontend: vitest, build y eslint de los ficheros tocados.
- **Comprobación en el navegador**, a 1280 y 375 px (la barra sin sesión, en un navegador real a 375 px), con la consola sin errores propios de la aplicación y un recorrido solo con teclado, a través del proxy de Vite: registrarse con una cuenta `@example.com`, salir, entrar y pulsar «Salir» a continuación (una sola petición de salida, sin `csrf_failed` ni reintento), entrar otra vez, recargar y seguir con sesión, comprobar las credenciales incorrectas y, la última, el límite de fallos del par. En el mismo recorrido se comprueban las medidas de accesibilidad: controles de 44 px, contraste AA de los textos nuevos, autocompletado, pegar en los campos, foco visible y los anuncios («Entrando…», «Has entrado.» y cada error una vez). Crear la cuenta escribe en la base de datos de desarrollo: el desarrollador lo autoriza expresamente en ese momento. Si hay que repetir el límite, el reinicio del backend, también con su autorización, pone a cero los contadores.
- `docs/architecture.md` recoge la entrada, sus dos límites, su almacén y la nota de la señal de salida; las specs 009 y 016 quedan actualizadas con `/sdd-change` (Cambios en otras specs).

## Dudas abiertas
- Ninguna sobre el comportamiento.
- **Notas para el plan (no cambian la spec)**:
  - Comprobar en el contenedor, con las versiones fijadas, cuántas veces calcula el hash la autenticación de Django con un email desconocido, una contraseña errónea, una cuenta desactivada, una contraseña inutilizable, un email vacío y una contraseña correcta con un hash desactualizado; que la normalización y los rechazos sin hash no rompen la igualdad; y con qué hasher corre el test que cuenta los hashes, porque el de los tests no ejercita el rehash.
  - Comprobar que la clave HMAC se calcula sin error con un email que lleva un sustituto suelto, que la clave y la búsqueda usan la misma forma normalizada y que la normalización es idempotente.
  - Comprobar qué receptores conectan Django y las apps instaladas a las señales de entrada correcta (el que escribe `last_login`), de entrada fallida y de salida.
  - Comprobar qué cookies escriben o borran los middlewares de sesión y de CSRF cuando llegan mal formadas.
  - Comprobar la capacidad y la política de expulsión del almacén en memoria de Django, y cómo calcula DRF la espera cuando el historial supera el límite.
  - La hora entra como parámetro en las ventanas de los dos límites, para poder probarlas.
  - La guarda del URLconf de la 009 exige la comprobación explícita de CSRF a la nueva vista.
