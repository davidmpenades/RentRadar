# Spec 004 — Usuarios y categorías
Estado: aprobada
Depende de: spec 001 (RF-29 y RF-30: fechas con zona horaria y UTC como referencia) y spec 002 (RF-7: los cambios de modelos sin migración hacen fallar los tests).

## Contexto y objetivo
RentRadar no tiene todavía datos de dominio. Antes de construir autenticación, bienes o búsqueda, hacen falta dos piezas de datos:
- **Usuarios** que se identifican por su email, sin nombre de usuario. El modelo de usuario debe quedar fijado antes de la primera migración que dependa de él, porque cambiarlo después es inviable.
- **Categorías** cerradas y con identificador estable, sembradas desde el principio, para que la spec 005 (bienes) pueda clasificar cada bien.

Esta spec solo define datos y reglas: no hay endpoints ni pantallas. Todo lo relativo a bienes, ubicación y privacidad de la ubicación va en la spec 005.

## Usuarios
- **Usuario registrado**: persona con cuenta; en esta spec solo existe como dato.
- **Desarrollador del equipo**: crea usuarios y superusuarios, y ejecuta los tests.

## Historias de usuario
- HU-1. Como usuario, quiero identificarme con mi email para no tener que recordar un nombre de usuario aparte.
- HU-2. Como usuario, quiero que no puedan existir dos cuentas con mi email escrito con distintas mayúsculas, para que nadie suplante mi cuenta.
- HU-3. Como anunciante, quiero una lista cerrada de categorías con nombres en castellano, para clasificar mis bienes de forma coherente (los bienes llegan en la spec 005).
- HU-4. Como desarrollador, quiero que la base de datos garantice la unicidad y las longitudes aunque se salte la validación, para que ningún dato inválido entre por otra vía.

## Definiciones
- **Texto recortado**: el texto sin los espacios en blanco (espacios, tabuladores y saltos de línea) del principio y del final. El sistema guarda siempre el texto ya recortado.
- **Longitud**: número de caracteres del texto recortado, no de bytes.
- **Carácter de control**: el carácter nulo (`\x00`) y cualquier otro carácter de control Unicode (categoría Cc), incluidos los tabuladores y saltos de línea que queden dentro del texto tras recortarlo.
- **Rechazar**: no guardar el dato ni modificar nada. Tiene dos niveles:
  - **En validación**: el sistema devuelve un error con un código de error y el campo afectado, sin incluir el valor recibido.
  - **En la base de datos**: si se guarda saltándose la validación, la base de datos devuelve un error de integridad, que no tiene por qué nombrar el campo.
- **Permisos de administración**: las marcas de miembro del equipo (`is_staff`) y de superusuario (`is_superuser`).
- **Semilla**: el conjunto fijo de once categorías de RF-19.

## Requisitos funcionales

### Usuarios
- RF-1: EL SISTEMA identifica a cada usuario por su email, que es su identificador de acceso; no existe un nombre de usuario.
- RF-2: CUANDO se crea un usuario o se cambia su email, EL SISTEMA guarda el email recortado y entero en minúsculas (parte local y dominio).
- RF-3: CUANDO se crea un usuario, EL SISTEMA guarda la contraseña solo en forma de hash.
- RF-4: SI al crear un usuario o cambiar su email el email recortado está vacío, no tiene formato de email válido o contiene caracteres de control, ENTONCES EL SISTEMA lo rechaza en validación.
- RF-5: SI el email recortado supera 254 caracteres, ENTONCES EL SISTEMA lo rechaza en validación y en la base de datos.
- RF-6: SI al crear un usuario o cambiar su email, el email coincide sin distinguir mayúsculas con el de otro usuario, ENTONCES EL SISTEMA lo rechaza en validación.
- RF-7: SI se intenta guardar un usuario cuyo email coincide en minúsculas con el de otro usuario, aunque se salte la validación o lleguen dos altas a la vez, ENTONCES la base de datos lo rechaza con un error de integridad.
- RF-8: SI la contraseña está vacía o ausente al crear un usuario o un superusuario, ENTONCES EL SISTEMA rechaza la creación en validación y no crea un usuario con contraseña inutilizable.
- RF-9: SI la contraseña supera 128 caracteres, ENTONCES EL SISTEMA la rechaza en validación sin calcular su hash.
- RF-10: CUANDO se crea un usuario ordinario, EL SISTEMA no le concede permisos de administración.
- RF-11: CUANDO se crea un superusuario, EL SISTEMA le concede permisos de administración.
- RF-12: EL SISTEMA no incluye el valor recibido del email ni la contraseña en ningún error que devuelve ni en ningún registro de log que emite la aplicación. CUANDO la base de datos rechaza un email duplicado, la capa que guarda usuarios captura el error de integridad dentro de una transacción atómica y lo traduce a un código de error sin el valor, sin propagarlo crudo ni registrarlo.

### Categorías
- RF-13: EL SISTEMA identifica cada categoría por un slug único y estable, y le asigna un nombre en castellano.
- RF-14: SI el slug está vacío o no se compone solo de minúsculas ASCII, dígitos y guiones medios sin guiones al principio, al final ni consecutivos, ENTONCES EL SISTEMA rechaza la categoría en validación.
- RF-15: SI el slug supera 50 caracteres o ya existe, ENTONCES EL SISTEMA rechaza la categoría en validación y en la base de datos.
- RF-16: SI el nombre recortado está vacío o contiene caracteres de control, ENTONCES EL SISTEMA rechaza la categoría en validación.
- RF-17: SI el nombre recortado supera 60 caracteres o coincide sin distinguir mayúsculas con el de otra categoría, ENTONCES EL SISTEMA rechaza la categoría en validación y en la base de datos.
- RF-18: SI se intenta cambiar el slug de una categoría ya guardada, ENTONCES EL SISTEMA rechaza el cambio en validación.
- RF-19: CUANDO se aplican las migraciones, EL SISTEMA deja creadas las once categorías de la semilla: `ebike` (Bicicleta eléctrica), `caravan` (Caravana), `motorhome` (Autocaravana), `van` (Furgoneta), `pool` (Piscina), `barbecue` (Barbacoa), `sports-area` (Zona deportiva), `boat` (Barco), `kayak` (Kayak), `canoe` (Piragua) y `other` (Otros).
- RF-20: CUANDO la semilla se aplica sobre una base de datos que ya contiene alguno de sus slugs, EL SISTEMA no duplica ninguna categoría y deja cada categoría de la semilla con el slug y el nombre de la semilla.
- RF-21: CUANDO se revierte la migración de la semilla, EL SISTEMA borra solo las categorías cuyos slugs son los de la semilla y conserva cualquier otra.
- RF-22: SI al revertir la migración de la semilla hay datos que dependen de alguna de sus categorías, ENTONCES EL SISTEMA falla sin borrar ninguna. En esta spec todavía no hay datos dependientes; la spec 005 introduce la protección de las categorías con bienes y su test.

## Requisitos no funcionales
- **Permisos**: esta spec no expone endpoints, así que no hay accesos de anónimo, usuario ni propietario que declarar. Las specs de API los declaran según las "Reglas para specs posteriores".
- **Desconfianza de la entrada (constitución, punto 6)**: reparto del rechazo entre la validación y la base de datos:
  - En validación y en la base de datos: la unicidad del email en minúsculas, la del slug y la del nombre de categoría en minúsculas, y las longitudes del email (254), del slug (50) y del nombre (60), contadas en caracteres.
  - Solo en validación: el formato del email, los caracteres de control, la contraseña no vacía y de 128 caracteres como máximo, la inmutabilidad del slug, el formato del slug y el recorte.
- **Errores**: cada rechazo en validación lleva un código de error estable en inglés y el campo afectado, no un mensaje en castellano; el cliente traduce los códigos. La lista de códigos se fija en el plan.
- **Seguridad**: las contraseñas solo se guardan como hash. El límite de 128 caracteres evita que una contraseña enorme dispare el coste del cálculo del hash.
- **Fechas**: las que trae el modelo de usuario (alta y último acceso) llevan zona horaria, en UTC como referencia (RF-29 y RF-30 de la 001).
- **Idioma**: identificadores, slugs y códigos de error en inglés; nombres de categoría en castellano (constitución, punto 8).
- **Riesgos aceptados por el usuario**:
  - Algunos RF agrupan dos comportamientos cercanos (por ejemplo, el rechazo en validación y en la base de datos), y cada parte tiene su propio test.
  - Las fechas que el modelo de usuario fija por su cuenta (alta) no entran como parámetro.

## Reglas para specs posteriores
- **Registro y recuperación de contraseña**: responden de forma uniforme, exista o no el email, sin revelar si un email está registrado.
- **Login**: compara el email sin distinguir mayúsculas, con la misma normalización de RF-2 (spec de autenticación).
- **Respuestas públicas**: nunca incluyen el email, `is_staff`, `is_superuser` ni `last_login` de un usuario.
- **Propiedad de los recursos**: el propietario de cualquier recurso sale siempre del usuario de la sesión, nunca del cuerpo de la petición.
- **Campos protegidos**: `is_staff`, `is_superuser` e `is_active` nunca se escriben desde la API pública.

## Casos límite
- Se crea `Ana@Correo.ES` y después `ana@correo.es`: el primero se guarda como `ana@correo.es` y el segundo se rechaza por unicidad (RF-2, RF-6).
- Un usuario cambia su email a `ANA@correo.es` cuando ya existe `ana@correo.es`: se rechaza (RF-2, RF-6).
- Dos usuarios con `Ana@Correo.ES` y `ana@correo.es` guardados saltándose la validación: la base de datos rechaza el segundo (RF-7).
- Email con espacios al principio o al final: se recorta antes de comparar y guardar (RF-2).
- Email con `\x00`, un tabulador interno o un salto de línea interno: se rechaza (RF-4).
- Email sin arroba o vacío tras recortar: se rechaza (RF-4).
- Email de 254 caracteres: se acepta; de 255: se rechaza (RF-5).
- `create_user` o `create_superuser` con contraseña `None` o vacía: se rechaza, sin crear un usuario con contraseña inutilizable (RF-8).
- Contraseña de 128 caracteres: se acepta; de 129: se rechaza. La fortaleza se valida en la spec de autenticación (RF-9).
- Un email rechazado por duplicado: ni el error ni el log contienen el email recibido (RF-12).
- Slug `Ebike`, `e bike`, `-ebike`, `ebike-`, `e--bike` o vacío: se rechaza (RF-14).
- Slug de 50 caracteres: se acepta; de 51: se rechaza (RF-15).
- Slug `pool` cuando ya existe: se rechaza (RF-15).
- Nombre `  piscina  ` cuando ya existe `Piscina`: tras recortar coincide sin distinguir mayúsculas y se rechaza (RF-17).
- Nombre con un tabulador interno o con `\x00`: se rechaza (RF-16).
- Nombre de 60 caracteres con tildes: se acepta, porque cada letra con tilde cuenta como un carácter; de 61: se rechaza (RF-17).
- Cambiar el slug de una categoría ya guardada: se rechaza (RF-18).
- La semilla se aplica sobre una base de datos que ya tiene `pool` con otro nombre: no se duplica y queda con el nombre `Piscina` (RF-20).
- La semilla se aplica en una base de datos de test nueva: las once categorías existen sin intervención del desarrollador (RF-19).
- Se revierte la semilla con una categoría ajena a ella en la base de datos: se borran solo las once de la semilla (RF-21).

## Fuera de alcance
- **Bienes, función de aproximación de la ubicación, servicio de escritura de bienes y privacidad de la ubicación**: van en la spec 005, incluida la protección contra el borrado de usuarios y categorías con bienes.
- **Borrado o anonimización de cuentas (RGPD, art. 17)**: queda fuera de esta spec, pero es un **requisito obligatorio antes de abrir la plataforma a usuarios reales**.
- Endpoints, serializers, autenticación y sesiones: login, registro, recuperación de contraseña, validadores de fortaleza de la contraseña y verificación de email (spec de autenticación y de API).
- Panel de administración.
- Tipos de cuenta (particular o profesional), perfil, teléfono, avatar y datos fiscales. Los usuarios heredan los campos opcionales de nombre y apellidos de AbstractUser, sin usarlos.
- Crear, editar o borrar categorías en ejecución y solicitudes de categorías nuevas: no están en el MVP; las categorías solo cambian por migración.
- Traducción del nombre de las categorías a otros idiomas.

## Restricciones de implementación pedidas por el usuario
- El usuario escribe los modelos; Claude escribe las migraciones, la semilla y los tests, y revisa línea a línea el código del usuario.
- El modelo de usuario se basa en AbstractUser, con el email como campo de acceso y sin username.
- `django.contrib.auth` y `django.contrib.contenttypes` se instalan en esta spec, y AUTH_USER_MODEL se fija antes de la primera migración del usuario, en un único paso coherente.
- El email se normaliza entero a minúsculas; la normalización estándar del framework (`normalize_email`) solo baja el dominio y no basta.
- La semilla es una migración de datos que obtiene el modelo con `apps.get_model` (nunca importa el modelo actual), usa `update_or_create` por slug y declara un `reverse_code` explícito que borra solo los slugs de la semilla.

## Criterios de finalización
- Cada RF tiene un test automático. Esta spec no tiene interfaz, así que no hay comprobaciones en navegador.
- Un test crea `Ana@Correo.ES` y comprueba que crear `ana@correo.es` choca por unicidad (RF-2, RF-6).
- RF-7 se verifica sin hilos ni `serialized_rollback`: un test determinista inserta dos veces el mismo email, con distinta capitalización, saltándose la validación, y espera un error de integridad por la restricción de unicidad sobre el email en minúsculas.
- Las restricciones de base de datos de RF-5, RF-15 y RF-17 se verifican con tests que guardan saltándose la validación y esperan un error de integridad.
- RF-12 se verifica con un test que provoca rechazos de email y contraseña y comprueba que ni el error ni el log capturado contienen los valores recibidos.
- Un test comprueba que las once categorías existen, con su slug y su nombre, tras migrar (RF-19).
- Tests de migración comprueban que reaplicar la semilla no duplica y restaura los nombres (RF-20), y que revertirla borra solo los slugs de la semilla (RF-21). La parte de RF-22 con datos dependientes se verifica en la spec 005.
- La suite de tests, el análisis estático y la comprobación de migraciones (RF-7 de la 002) están en verde.
- La base de datos de desarrollo y la de test aplican las migraciones desde cero y contienen la semilla.

## Dudas abiertas
- Ninguna. El nivel de detalle del log del servidor de PostgreSQL, que incluye el valor duplicado en sus errores de unicidad, queda para la spec de despliegue.
