# Spec 009 — Registro, sesión y salida
Estado: implementada
Depende de: spec 004 (usuarios, alta con contraseña obligatoria, normalización del email y "Reglas para specs posteriores"), spec 005 (el propietario de un recurso sale de la sesión) y spec 006 (interfaz web, página del mapa, formato de errores de la API y límite de peticiones por IP).

## Contexto y objetivo
RentRadar ya guarda usuarios y bienes, y cualquiera puede ver el mapa, pero nadie puede identificarse. Esta spec entrega la primera funcionalidad con cuenta, de la base de datos a la pantalla. Un visitante crea una cuenta con su email y una contraseña, y el registro le abre la sesión. La web recuerda la sesión al recargar y el usuario puede salir. La API conoce desde ahora al usuario de cada petición de estas operaciones, que es lo que necesitan las specs que escriben datos (publicar bienes, reservas).

Incluye:
- registro que abre sesión, «quién soy» y salida;
- la protección CSRF de las operaciones que cambian el estado;
- las reglas de contraseña que la 004 dejó para la autenticación;
- el límite de peticiones de registro;
- una barra superior mínima con «Registrarse» y «Salir», y la página de registro.

La autenticación es la sesión de Django con CSRF, en el mismo origen que la página. JWT y la aplicación móvil quedan fuera por ahora. Se prueba de punta a punta sin cuentas creadas a mano: el registro abre la sesión y con ella se comprueban «quién soy» y la salida.

La **entrada** (con su error uniforme de credenciales incorrectas, sus límites de intentos y la página `/login`) es la spec 015. La navegación completa llega en la spec 008. La verificación de email y la recuperación de contraseña, en la 013, y el borrado de cuenta y los textos legales, en la 014. Orden: 009 → 015 → 013 → 014 → 011. Hasta la 013 el registro **no** es uniforme: avisa de que un email ya existe (ver «Riesgos aceptados»).

## Usuarios
- **Visitante**: cualquier persona que abre RentRadar, sin sesión.
- **Usuario**: persona con cuenta y sesión abierta. En esta spec no tiene más capacidades que un visitante: puede salir.
- **Staff y superusuario**: sin capacidades distintas de las de un usuario en esta spec.
- **Desarrollador del equipo**: prueba el flujo en el navegador y ejecuta los tests.

## Historias de usuario
- HU-1. Como visitante, quiero crear una cuenta con mi email y una contraseña, para usar RentRadar como usuario.
- HU-2. Como usuario, quiero seguir con la sesión abierta al recargar la página y poder salir cuando quiera, para controlar quién usa mi cuenta.
- HU-3. Como visitante, quiero que el mapa siga funcionando igual sin cuenta, para explorar sin registrarme.
- HU-4. Como desarrollador, quiero que la API conozca al usuario de la sesión, para que las specs posteriores fijen al propietario de un recurso a partir de ella.

## Definiciones
- **Credenciales**: el email y la contraseña, enviados juntos.
- **Email normalizado**: el de RF-2 de la 004 (recortado, en forma NFKC y entero en minúsculas).
- **Contraseña aceptable**: la que cumple todo esto:
  - tiene de 10 a 128 puntos de código, contados tal como llegan: no se recorta ni se normaliza, y los espacios cuentan;
  - no es una de las contraseñas comunes de la lista de Django, con el criterio de comparación de Django (que ignora mayúsculas y espacios en los extremos);
  - no está formada solo por dígitos;
  - no se parece demasiado al email normalizado, con el criterio de similitud de Django;
  - no contiene un carácter nulo ni un sustituto Unicode suelto.
  «Tal como llegan» vale para la longitud y el hash; la lista de comunes y la similitud usan el criterio de Django. Se acepta que pasen contraseñas como `aaaaaaaaaa` si no están en la lista.
- **Sesión**: relación entre un navegador y una cuenta, identificada por una cookie que los scripts de la página no pueden leer. Caduca a los 14 días de abrirse, sin renovarse con la actividad. Una sesión **válida** es una que existe, no ha caducado y pertenece a una cuenta activa.
- **Token CSRF**: valor que el cliente envía en una cabecera en cada petición que cambia el estado (registro y salida) y que demuestra que sale de la propia página. Es de doble envío: la petición debe llevar la misma cadena en la cabecera y en una cookie legible por la página, y no está ligado a la sesión. El cliente lo recibe en esa cookie al preguntar «quién soy», y cambia cada vez que se abre una sesión.
- **«Quién soy»**: consulta del cliente por la sesión de su navegador.
- **Barra superior**: franja superior de la página, con la marca (un enlace a la página del mapa) y las acciones de sesión, en todas las páginas. No es la «cabecera» del panel de resultados de la 006.
- **IP del visitante**: la dirección de la conexión; en IPv6, su prefijo /64, de modo que las direcciones de un mismo /64 comparten el límite. Una IP vacía o no válida cae en un cubo fijo común, así que nunca queda sin límite. Detrás de un proxy sería la del proxy hasta que la spec 011 fije cuál es de confianza.
- **Página de registro**: página propia de RentRadar, con la dirección definitiva `/register`. La dirección con barra final (`/register/`) se normaliza a ella.
- **Demasiado anidado**: un JSON que el analizador de la API no admite por su profundidad. No hay un límite de profundidad propio: un objeto válido anidado dentro de una clave desconocida no es demasiado anidado; se acepta y esa clave se ignora como cualquier campo desconocido.

### Valores de esta spec
| Valor | Fijado |
|---|---|
| Longitud de la contraseña | de 10 a 128 puntos de código |
| Caducidad de la sesión | 14 días desde que se abre, sin renovación |
| Límite de registro por IP | 10 peticiones en una hora deslizante |
| Tamaño máximo del cuerpo de una petición de registro | 4 KiB |
| Tiempo máximo de espera de «quién soy» | 5 s |
| Tiempo máximo de espera del registro y de la salida | 10 s |

En el límite cuenta toda petición que no rechace el propio límite: las aceptadas y las que después se rechazan por CSRF, por cuerpo inválido o demasiado grande (413), por validación o por método no admitido. Los demás números los fija el plan: el almacén de los contadores y la altura de la barra superior.

## Requisitos funcionales

### Registro
- RF-1: CUANDO un visitante envía unas credenciales válidas con un email no registrado, EL SISTEMA crea la cuenta con las reglas de la 004 (email normalizado, contraseña solo como hash y sin permisos de administración), abre una sesión y responde con el email de la cuenta.
- RF-2: SI el email o la contraseña de un registro no cumplen las reglas de la 004 o la contraseña no es aceptable, ENTONCES EL SISTEMA rechaza el registro sin crear la cuenta ni la sesión y sin tocar la sesión actual, y responde con todos los códigos de error por campo, sin el valor recibido.
  - El orden es fijo: el email antes que la contraseña y, dentro de la contraseña, `password_required`, `password_too_long`, `password_too_short`, `password_too_common`, `password_entirely_numeric` y `password_too_similar`.
  - Un email ya registrado se rechaza con `email_taken`, de forma explícita y junto con los demás.
  - Un email o una contraseña ausentes, nulos o vacíos dan `email_empty` y `password_required`. Un email con carácter de control, incluido el nulo, incluye `email_control_char` (el nulo, el tabulador y el salto de línea dan además `email_invalid`). Un email con un sustituto Unicode suelto da `email_invalid`, sin error del servidor; la regla es de la 004 (RF-4) y vale para todas las vías de alta y de cambio de email. Una contraseña con un nulo o un sustituto suelto da `password_invalid`, que va sola: si aparece, no se dan los demás códigos de contraseña.
- RF-3: SI una IP supera las 10 peticiones de registro por hora, ENTONCES EL SISTEMA rechaza la petición con el error de límite superado y el tiempo de espera, sin crear nada, aunque las credenciales sean válidas.

### Sesión
- RF-4: CUANDO se abre una sesión por registro, EL SISTEMA descarta siempre la sesión anterior del navegador, sea anónima, de otra cuenta o de la misma, y crea una con identificador nuevo y token CSRF nuevo.
- RF-5: CUANDO el cliente pide salir con un token CSRF válido, EL SISTEMA destruye la sesión en el servidor si la hay y retira siempre la cookie de sesión, aunque la sesión esté caducada o mal formada. El identificador anterior deja de autenticar. Sin sesión responde bien y no cambia nada.
- RF-6: CUANDO el cliente pregunta «quién soy», EL SISTEMA responde con el email de la sesión válida o, si no la hay, con la indicación de que no hay sesión, sin devolver un error, y deja el token CSRF en su cookie.
- RF-7: SI una petición de registro o de salida no lleva un token CSRF válido, ENTONCES EL SISTEMA la rechaza con el error `csrf_failed` antes de leer el cuerpo, sin crear cuenta ni sesión y sin tocar la sesión actual. Vale también para la salida sin sesión.
- RF-8: SI el cuerpo de una petición de registro no es JSON válido, está demasiado anidado (ver «Definiciones»), no es un objeto, o lleva el email o la contraseña con un tipo que no es texto (número, lista u objeto), ENTONCES EL SISTEMA la rechaza como `invalid_request`; y SI declara más de 4 KiB, llega con codificación troceada (`Transfer-Encoding`, de cualquier tamaño) o se leen más de 4 KiB, la rechaza como `payload_too_large`. En ambos casos no crea nada. Un email o una contraseña ausentes, nulos o vacíos no son `invalid_request`: los trata RF-2.

### Interfaz
- RF-9: MIENTRAS el cliente aún no sabe si hay sesión, la barra superior no muestra acciones de sesión; después muestra «Registrarse» si no hay sesión y «Salir» si la hay, y nunca el email de la cuenta. La marca de la barra es un enlace a la página del mapa. Si «quién soy» falla, no responde en 5 s o su respuesta tiene una forma inválida, se trata como sin sesión y no bloquea el mapa.
- RF-10: CUANDO el visitante envía el formulario de registro con el email y la contraseña no vacíos, EL SISTEMA deshabilita el envío mientras la petición está en curso y, si se abre la sesión, lo lleva al mapa sin añadir una entrada al historial y con la barra superior en «Salir». El cliente solo comprueba que no estén vacíos; el resto lo valida el servidor.
- RF-11: SI el servidor rechaza el formulario, la petición falla o vence su tiempo máximo de 10 s, ENTONCES EL SISTEMA muestra el error en castellano junto al campo afectado o, si es general, en la región de estado, conserva el email, borra la contraseña solo si el resultado trae un error de la contraseña y la conserva en cualquier otro caso, y lleva el foco al primer campo con error (email antes que contraseña) o, si el error es general, a la región de estado. Ante `csrf_failed`, el cliente vuelve a preguntar «quién soy» y reintenta una sola vez antes de mostrar el error. Si la petición falla o vence, el error es general y el envío vuelve a habilitarse para reintentar; antes de mostrar el error de un tiempo vencido, el cliente pregunta «quién soy» y, si hay sesión, continúa como un éxito.
- RF-12: CUANDO el visitante pulsa «Salir», EL SISTEMA cierra la sesión, pasa la barra superior a «Registrarse», anuncia «Has salido», lleva el foco a «Registrarse» y lo deja en la página en que estaba. SI falla o vence su tiempo máximo de 10 s, la barra sigue en «Salir», el foco queda en «Salir» y se muestra y anuncia «No se ha podido salir. Inténtalo de nuevo.» con un botón «Reintentar». La salida usa el mismo reintento ante `csrf_failed` que RF-11.
- RF-13: MIENTRAS un visitante abre la página de registro, EL SISTEMA muestra el formulario sin esperar a «quién soy» y, si la sesión llega después o ya existía, lo lleva al mapa sin añadir una entrada al historial.

## Requisitos no funcionales
- **Permisos (constitución, punto 5)**:
  - Registro: lo usa el visitante. Un usuario con sesión también puede: su sesión se sustituye por la nueva (RF-4).
  - Salida: con sesión cierra solo la sesión de la cookie de la petición; sin sesión responde bien y no cambia nada. Ninguna operación permite cerrar o ver la sesión de otro.
  - «Quién soy»: lo usan el visitante y el usuario, y solo devuelve datos de la sesión de la propia petición. Sin sesión responde correctamente y no con un error, para que una visita anónima normal no deje errores en la consola del navegador.
  - Estas operaciones identifican al usuario por su sesión. La lista pública de la 006 no (ver «Lista pública sin cambios»).
  - Ninguna operación acepta del cliente un identificador de usuario ni los campos `is_staff`, `is_superuser` o `is_active`: se ignoran y la cuenta creada no recibe permisos (004). El staff y el superusuario no tienen más capacidades aquí.
  - No hay recursos por identificador, así que no hay caso de 404 ni de 403 por objeto. Cuando existan recursos con propietario, este sale de la sesión (005).
  - El registro y la salida admiten solo POST, y «quién soy» solo GET y HEAD. Cualquier otro método recibe el error de método no admitido, salvo en el registro con el límite superado (ver «Orden de comprobaciones»).
- **Orden de comprobaciones**: límite por IP → método → CSRF → tamaño y forma del cuerpo → validación → creación, como la lista pública de la 006. El límite solo existe en el registro: la salida va método → CSRF. Con el límite superado, cualquier método del registro recibe el error de límite. Una petición sin token CSRF desde una IP que ya superó el límite recibe el error de límite, no el de CSRF.
- **Sesión y cookies**:
  - La cookie de sesión no es legible por scripts, no se envía en peticiones entre sitios (SameSite Lax) y es solo HTTPS en producción. La del token CSRF es legible por la página.
  - La caducidad es de 14 días fijos. El cierre de sesión se aplica en el servidor (RF-5).
  - El token CSRF es de doble envío: lo que se garantiza y se prueba es que cambia al abrir una sesión (RF-4), no que esté ligado a ella.
  - El cliente de sesión envía las cookies del mismo origen. El de la lista pública sigue sin enviarlas.
- **Lista pública sin cambios**: la lista de la 006 sigue sin autenticar al visitante: no lee ni modifica la sesión, y su respuesta es idéntica con o sin sesión, sin cookies, también con una cookie de sesión mal formada. Añadir la autenticación no la cambia.
- **Caché**: toda respuesta de registro, salida y «quién soy» lleva `Cache-Control: no-store`, errores incluidos, y la de «quién soy» se declara variable por la cookie. Ninguna caché compartida puede servir la respuesta de una persona a otra. Quedan fuera hasta la 011, como en la 006, las redirecciones por barra final y los errores internos del servidor (5xx).
- **Respuestas mínimas**: las de éxito llevan solo el email de la propia cuenta, o la indicación de que no hay sesión. Nunca llevan un identificador, `is_staff`, `is_superuser`, `last_login` ni la fecha de alta. Nunca llevan el email de otro usuario.
- **Desconfianza de la entrada (constitución, punto 6)**:
  - El backend valida tipo, tamaño y contenido de cada campo (RF-2, RF-8). Los campos desconocidos se ignoran.
  - Una contraseña de más de 128 caracteres se rechaza sin calcular su hash (004, RF-9). Ningún contenido del email ni de la contraseña, incluidos el nulo y los sustitutos sueltos, produce un error del servidor.
  - El tamaño se mide en bytes del cuerpo leído, no en caracteres.
  - El cliente valida la forma de cada respuesta (email como texto no vacío, o la indicación de que no hay sesión) antes de usarla. Si la respuesta de un registro llega con forma inválida o la petición vence, el cliente pregunta «quién soy» y decide con eso: si hay sesión continúa como un éxito, y si no, muestra un error general.
- **Errores**:
  - Tienen un formato único con códigos estables en inglés: uno general y, en el registro, uno por campo (los de la 004 y los de contraseña de esta spec). Los propios de esta spec son `csrf_failed` (403, distinto de `forbidden`), `invalid_request` (400) y `payload_too_large` (413). La lista completa se fija en el plan.
  - Nunca incluyen el valor recibido. El cliente traduce los códigos.
  - Mensajes en castellano que fija la spec porque cuidan la privacidad: límite superado, «Demasiados intentos. Inténtalo de nuevo en N minutos.», con N en minutos redondeados hacia arriba y como mínimo 1 («1 minuto»); email repetido, «Ya existe una cuenta con este email.»
- **Privacidad y logs**: ni los logs ni los errores ni los contadores de los límites contienen la contraseña ni el email. Ni el email ni la contraseña salen del servidor hacia ningún tercero.
- **Contrato**: la API sigue versionada. Su descripción legible por máquina y los tipos del cliente se regeneran, y el control de desfase de la CI pasa.
- **Mismo origen**: el navegador llama a la API desde el mismo origen que la página, y la API no concede permisos entre orígenes.
- **Dependencias (constitución, punto 1)**: ninguna dependencia nueva. Se usan la autenticación de Django, la de DRF y la interfaz actual; el frontend no añade librería de rutas.
- **Accesibilidad y móvil (constitución, punto 7)**:
  - Se diseña a 375 px y se amplía a 1280 px. La barra superior no desborda y los controles miden al menos 44 px: «Registrarse», «Salir», los campos, el envío y «Mostrar contraseña».
  - Cada campo tiene su etiqueta y sus atributos de autocompletado (email, contraseña nueva) y no se bloquea pegar. Los errores se asocian al campo.
  - Una región de estado anuncia el envío («Creando la cuenta…»), el éxito y los errores, una vez por petición.
  - El formulario tiene un control «Mostrar contraseña» que alterna ver y ocultar el texto, para evitar errores de escritura mientras no haya recuperación de contraseña.
  - Uso completo con teclado, foco visible, contraste AA y sin animaciones si el visitante pide reducir el movimiento.
- **Idioma (constitución, punto 8)**: los textos de la interfaz, en castellano, salen del catálogo de mensajes. Rutas, códigos e identificadores van en inglés.

## Casos límite
- Registro con `Ana@Correo.ES` cuando existe `ana@correo.es`: se rechaza con `email_taken`, junto con los demás errores si los hay (RF-2).
- Contraseña de 9 caracteres: se rechaza; de 10: se acepta; de 128: se acepta; de 129: se rechaza sin calcular su hash (RF-2).
- Contraseña `1234567890`: se rechaza con `password_too_common` y `password_entirely_numeric`. Una contraseña de la lista de comunes, también escrita con mayúsculas o con espacios en los extremos, y otra igual al email se rechazan (RF-2).
- Contraseña con espacios al principio y al final: no se recorta, cuenta su longitud completa y se guarda tal cual (RF-2).
- Email o contraseña ausentes, `null` o vacíos: `email_empty` y `password_required`, no `invalid_request` (RF-2).
- Email con un sustituto Unicode suelto (U+D800) en el dominio: `email_invalid`, sin error del servidor y sin consultar la base de datos; vale también para `create_user`, `create_superuser` y el cambio de email (RF-2, 004 RF-4).
- Email con un carácter nulo: `email_invalid` y `email_control_char`; contraseña con un nulo o un sustituto suelto (`"\ud800"`): `password_invalid`; en ambos casos sin error del servidor (RF-2).
- Registro con campos añadidos como `is_staff: true`: se ignoran y la cuenta no recibe permisos (RF-1).
- Dos registros simultáneos con el mismo email: uno crea la cuenta y el otro recibe `email_taken` (RF-2, 004 RF-7).
- Registro con una sesión de otra cuenta abierta: la sesión anterior se descarta y la nueva tiene otro identificador y otro token CSRF (RF-4).
- Registro rechazado con una sesión abierta: la sesión no cambia (RF-2).
- Petición 11 de registro en una hora desde una IP: límite superado, aunque las anteriores fueran inválidas o rechazadas por CSRF (RF-3).
- Dos direcciones IPv6 del mismo /64 comparten el límite (RF-3).
- Petición sin token CSRF desde una IP que ya superó el límite: error de límite, no de CSRF (RF-3, RF-7).
- Petición de registro o de salida sin token CSRF, con la cabecera vacía, sin cookie o con una cabecera que no coincide con la cookie: rechazada con `csrf_failed`, sin efectos, también la salida sin sesión (RF-5, RF-7).
- Cuerpo que no es JSON, que es una lista, con el email como número o la contraseña como lista u objeto: `invalid_request`, sin error del servidor (RF-8).
- Miles de listas anidadas dentro de 4 KiB: `invalid_request` porque la raíz no es un objeto, sin error del servidor. Si el analizador no lo admitiera por su profundidad, también `invalid_request` (RF-8).
- Objeto válido anidado en una clave desconocida (por ejemplo `{"x": {"x": {…}}}`, dentro de 4 KiB): no es demasiado anidado. La clave se ignora, no hay error del servidor y la petición sigue a RF-2: sin credenciales da `email_empty` y `password_required`, y con ellas en la raíz se trata como cualquier otro registro (RF-8, RF-2).
- Cuerpo troceado (`Transfer-Encoding`), de cualquier tamaño, o que declara o aporta más de 4 KiB: `payload_too_large` (RF-8). Cuerpo vacío con tipo JSON: se trata como un objeto vacío y da `email_empty` y `password_required` (RF-2).
- Salir con una sesión caducada o con una cookie de sesión mal formada: respuesta correcta y cookie retirada (RF-5).
- «Quién soy» con cuenta desactivada, sesión de 14 días y un segundo o cookie mal formada: responde sin sesión y sin error (RF-6).
- «Quién soy» falla, tarda más de 5 s o responde con otra forma: la barra no muestra acciones al principio, después «Registrarse», y el mapa sigue funcionando (RF-9).
- El primer envío falla con `csrf_failed` porque falló «quién soy»: el cliente pregunta de nuevo y reintenta una vez; si vuelve a fallar, error general (RF-11).
- La respuesta de un registro correcto llega con forma inválida: el cliente pregunta «quién soy»; con sesión continúa y sin ella muestra un error general (RF-10).
- La petición de registro vence a los 10 s: el cliente pregunta «quién soy»; con sesión (el servidor pudo completarlo) continúa como un éxito, y sin ella muestra el error general y el envío vuelve a habilitarse para reintentar (RF-11).
- Registro rechazado solo por el email (por ejemplo `email_taken`): se conservan el email y la contraseña. Con algún error de la contraseña, esta se borra aunque también haya errores del email. Un error general, el límite superado, un fallo o un tiempo vencido conservan los dos campos (RF-11).
- Doble clic o doble Intro en el envío: se envía una vez (RF-10). Intro en el último campo: lo envía (RF-10).
- Pulsar «Atrás» tras registrarse: no vuelve al formulario (RF-10).
- Salir falla por red, por un error del servidor o porque vence a los 10 s: la barra sigue en «Salir», el foco queda en «Salir» y se muestra y anuncia el error con «Reintentar» (RF-12).
- Pulsar la marca de la barra: lleva a la página del mapa con navegación interna, y desde el mapa no cambia nada (RF-9).
- Cerrar sesión en una pestaña y pulsar «Salir» en otra que aún muestra «Salir»: funciona sin error y la barra pasa a «Registrarse» (RF-5, RF-12).
- Abrir `/register` con sesión: va al mapa sin añadir una entrada al historial. Abrirlo sin sesión y que la sesión llegue después de pintar el formulario: igual (RF-13). `/register/` se normaliza a `/register` (RF-13).
- A 375 px la barra superior no desborda, ni con «Registrarse» ni con «Salir» (RF-9).
- La lista pública pedida con una sesión abierta: respuesta idéntica a la del anónimo, sin cookies (no funcionales).

## Fuera de alcance
- **Entrada**: iniciar sesión, el error uniforme de credenciales incorrectas, los límites de intentos de entrada (por IP, y por IP y email), la página `/login` y «Entrar» en la barra superior (spec 015). Hasta entonces, quien sale de una cuenta no puede volver a entrar en ella.
- **Verificación del email y recuperación de contraseña** (spec 013): el registro no comprueba que el email sea de quien lo escribe, y quien olvide su contraseña no puede recuperar la cuenta.
- **Borrado de cuenta, política de privacidad y aviso legal** (spec 014): el formulario de registro no enlaza todavía los textos legales. Es un requisito obligatorio antes de abrir el registro al público.
- Cambio de contraseña, cambio de email, ver o cerrar otras sesiones y cerrar todas las sesiones.
- «Recuérdame» y sesiones de duración distinta; renovar la sesión con la actividad.
- JWT, tokens de API y aplicación móvil; registro con terceros (Google, Apple); segundo factor; captcha.
- Aviso por correo de una cuenta nueva.
- Normalización Unicode de las contraseñas: se comparan tal como llegan.
- Un límite de profundidad del JSON propio de RentRadar: lo fija el analizador, y el tope real de la petición es el de 4 KiB.
- Registro uniforme (que responda igual exista o no el email): llega con la spec 013.
- Navegación completa, menú y perfil (spec 008); páginas protegidas y datos del usuario más allá del email.
- Panel de administración y entrada del staff.
- Fijar el proxy de confianza para la IP de los límites, el almacén compartido y atómico de los contadores, el tope global del coste del hash, las comprobaciones de `Origin` y `Referer` tras un proxy HTTPS, el anti-framing de las páginas y la purga de sesiones caducadas: spec 011.
- Un comando para borrar las cuentas de prueba: no se crea (ver Criterios de finalización).

## Cambios en otras specs
Se hacen con `/sdd-change`; solo cambian textos, sin código en las specs 004 y 006 salvo lo que pida la 006 en su interfaz. Los puntos 1 a 5 ya están hechos; el 6 se hace con el cambio que alinea esta spec con el comportamiento verificado en el plan:

**Spec 004, «Reglas para specs posteriores»:**
1. **Registro**: la regla «Registro y recuperación de contraseña: responden de forma uniforme» pasa a «La recuperación de contraseña responde de forma uniforme. El registro responde de forma explícita que el email existe (`email_taken`) hasta la spec 013, que lo hará uniforme con la verificación por correo».
2. **Respuestas públicas**: la regla «nunca incluyen el email…» pasa a «nunca incluyen el email de otros usuarios; `is_staff`, `is_superuser` y `last_login` no se incluyen nunca. Solo la sesión de la propia cuenta recibe su email».
6. **Email con sustituto suelto** (RF-4 y casos límite): el email con un sustituto Unicode suelto se rechaza en validación con `email_invalid`, sin error del servidor, al crear un usuario o un superusuario y al cambiar el email.

**Spec 006:**
3. **RF-8 (mapa a pantalla completa)**: el mapa ocupa toda la zona bajo la barra superior, no la pantalla completa. Se ajustan también las menciones de «pantalla completa» de RF-13 y de los casos límite y criterios que la repiten.
4. **RF-13 (error del estilo)**: el mensaje y «Reintentar» ocupan la zona bajo la barra superior, que se conserva; no se muestran el mapa ni el panel. La página «Página no encontrada» (RF-14) también va bajo la barra.
5. **Regla de privacidad de la URL** (requisitos no funcionales, privacidad): «La dirección de la página no cambia al mover el mapa (ni fragmento ni parámetros), el historial no gana entradas y la vista no se guarda en el almacenamiento del navegador» pasa a «La zona del mapa nunca va a la URL ni al almacenamiento del navegador: mover el mapa no cambia la dirección ni añade entradas al historial. La navegación entre páginas (`/map`, `/register` y después `/login`) sí usa el historial».

## Riesgos aceptados
- **Enumeración de emails**: el registro revela si un email existe (`email_taken`). Se mitiga con el límite de 10 registros por hora y IP. La spec 013 lo corrige.
- **Suplantación del email**: sin verificación, alguien puede registrar el email de otra persona y bloquear que ella lo use. Lo corrige la spec 013.
- **Sin recuperación de contraseña** hasta la 013: quien la pierda pierde la cuenta. No afecta a nadie real, porque el registro no se abre al público antes.
- **Cuentas de prueba**: sin entrada hasta la 015, cada comprobación usa una cuenta nueva `@example.com`, y esas cuentas no se reutilizan tras salir.
- **Registro agotable bajo IP compartida**: detrás de un proxy (`NUM_PROXIES = 0`) o de un NAT, todos los visitantes comparten IP, y cualquiera agota el cupo de registro de los demás. La 011 fija el proxy de confianza.
- **Almacén de contadores**: sin caché configurada, los contadores viven en memoria por proceso, con expulsión de entradas al llenarse y sin atomicidad. El límite efectivo se multiplica por el número de procesos y una ráfaga de peticiones simultáneas puede superar las 10. La 011 lo resuelve.
- **Coste del hash**: cada registro válido calcula un hash costoso; solo lo frena el límite por IP. «Salir» y «quién soy» no tienen límite.
- **Contraseñas**: pasan las que cumplen la longitud y no están en las listas (por ejemplo `aaaaaaaaaa`). Dos formas Unicode equivalentes de la misma contraseña no coinciden.
- **Sesión fija de 14 días**: una cookie robada vale hasta que caduca o su dueño sale, y no hay lista de sesiones. Las sesiones caducadas no se purgan hasta la 011.
- **Cookie CSRF**: es legible por scripts, por diseño; llega a todo visitante desde su primera visita, aunque solo mire el mapa, y sigue tras salir (un año por defecto). La política de privacidad de la 014 la recoge.
- **Inyección de cookies desde subdominios hermanos**, comprobaciones de `Origin` y `Referer` tras un proxy HTTPS y anti-framing de las páginas: se revisan en la 011.
- **Página técnica de depuración**: con `DEBUG` activo en desarrollo puede mostrar la contraseña y el email en las variables locales. Es el mismo caso que la 006 aceptó con las coordenadas.
- **Sin textos legales en el registro** hasta la 014. Solo hay datos de desarrollo.
- **Caché compartida con la lista pública**: la lista pública cuenta por dirección IPv6 completa en la misma caché en memoria (300 entradas). Quien controle un /64 puede llenarla y expulsar el contador de registro. La 011 lo resuelve con una caché compartida.
- **Cuerpo troceado**: bajo WSGI, un cuerpo sin longitud declarada llega vacío y no se puede medir. Se rechaza toda petición con `Transfer-Encoding`, y el tope real lo pone el proxy (spec 011).
- **Cuenta huérfana**: si falla el guardado de la sesión después de crear la cuenta, existe la cuenta sin sesión; sin entrada (spec 015) no se puede usar.
- **Registro tras un proxy HTTPS**: hasta que la 011 fije `SECURE_PROXY_SSL_HEADER` y los orígenes de confianza, el registro y la salida fallan con `csrf_failed` en ese despliegue.
- **Vistas futuras con la autenticación por sesión de serie**: solo comprobaría CSRF a los usuarios ya autenticados y respondería `forbidden`. Una guarda sobre las rutas obliga a las vistas que cambian el estado a usar la comprobación explícita (specs 010 y 015).
- **Contraseñas del terminal**: `createsuperuser` interactivo y `changepassword` pasan a aplicar los validadores de contraseña.

## Criterios de finalización
- Cada RF tiene un test automático (backend: pytest; frontend: vitest para la lógica y comprobación en navegador para los RF de interfaz, registrada en `validation.md`).
- **Pruebas de mecanismo** (esta spec toca seguridad), cada una con una mutación que debe hacer fallar un test, registradas en `validation.md`:
  - sesión nueva al registrarse, con identificador y token CSRF que cambian (RF-4), y destrucción al salir (RF-5);
  - rechazo por CSRF en el registro y en la salida sin sesión (RF-7);
  - límite de registro, con el prefijo /64 de IPv6 (RF-3);
  - contraseña de más de 128 caracteres sin calcular el hash;
  - la lista pública sigue sin leer la sesión y sin cookies;
  - `no-store`, respuesta mínima y ningún error del servidor con contenido nulo o sustitutos sueltos.
- La suite de tests, el análisis estático, la comprobación de migraciones y el control de desfase del contrato están en verde. Frontend: vitest, build y eslint de los ficheros tocados.
- **Comprobación en el navegador**, a 1280 y 375 px, con la consola sin errores propios de la aplicación (las respuestas 4xx esperadas al probar errores se anotan) y un recorrido solo con teclado, a través del proxy de Vite y sin añadir orígenes de confianza a la configuración de Django (Django recibe `Host: localhost:5173`): registrarse, ver «Salir» en la barra superior, recargar y seguir con sesión, salir, y comprobar un error de cada tipo (email repetido, contraseña débil, límite superado). El límite de registro se prueba el último, porque las pruebas salen de la misma IP; si hace falta repetirlo, se reinicia el backend, que pone a cero el contador en memoria. Registrarse crea cuentas en la base de datos de desarrollo: el desarrollador lo autoriza expresamente en ese momento y las cuentas usan el dominio `example.com`. Esas cuentas se acumulan en la base de datos de desarrollo hasta que haga falta limpiarlas; entonces se borran una vez con orden expresa del desarrollador, o se reinicia el volumen y se ejecutan `migrate` y el comando de demostración.
- Las specs 004 y 006 quedan actualizadas con `/sdd-change` (Cambios en otras specs), y las notas de la 015 siguen el orden de comprobaciones de esta spec.
- Se revisa que ningún bien, mapa ni panel de la 006 cambie su comportamiento, salvo el que ocupen la zona bajo la barra superior, sin scroll de página.

## Dudas abiertas
- Ninguna sobre el comportamiento.
- **Notas para el plan (no cambian la spec)**:
  - DRF marca sus vistas como exentas de CSRF y su autenticación por sesión solo comprueba el token cuando el usuario ya está autenticado. El registro y la salida son anónimos, así que necesitan una comprobación de CSRF explícita. El plan debe decir cómo, y la mutación de RF-7 debe cubrir el registro y la salida sin sesión.
  - La autenticación por sesión de DRF lee el usuario de la petición de Django, que hoy no existe porque falta el middleware de autenticación. El plan debe decir qué cambia y cómo la lista pública sigue sin leer la sesión.
  - Los tests existentes que fijan la configuración de DRF, la lista cerrada de códigos de error, la posición de los middlewares y la caché cambian en la tarea que cambia lo que fijan.
  - Comprobar en el contenedor, con las versiones fijadas, el comportamiento de `login()`, de los validadores de contraseña de Django y del JSON anidado a gran profundidad dentro de 4 KiB (no debe dar un error del servidor).
