# Spec 018 — Limpieza antes de lanzar
Estado: implementada
Depende de: la revisión de solo lectura previa al lanzamiento (17-11-2026), en sus partes de historial, secretos y licencias, y de la spec 017 (imágenes de categoría), cuyo registro de procedencia se corrige.

## Contexto y objetivo
La revisión previa al lanzamiento encontró varios defectos pequeños que no son funcionalidades nuevas:
- el registro de procedencia de la 017 atribuye imágenes a un commit que no las añade;
- hay rutas absolutas con el usuario del sistema en un repositorio público;
- `.gitignore` no cubre ficheros de claves ni volcados;
- los permisos de Claude Code no preguntan antes de borrar contenedores con sus volúmenes;
- la atribución del mapa tiene una parte en inglés.

Esta spec los corrige o los documenta, y deja en la memoria del proyecto lo que pasa a otras specs. Las WebP de la v2, cuyo fondo se quitó con remove.bg en su versión gratuita, no se purgan del historial: se documenta que siguen en él.

## Usuarios
- **Desarrollador**: mantiene el repositorio y decide qué se publica en él.
- **Lector del repositorio público**: cualquiera que consulte el historial o los ficheros en GitHub.
- **Usuario del mapa**: ve la atribución de los datos del mapa.

## Historias de usuario
- HU-1. Como desarrollador, quiero que el registro de procedencia de las imágenes diga solo lo que el historial confirma, para poder defender su origen.
- HU-2. Como desarrollador, quiero que el repositorio público no revele rutas ni el usuario de mi equipo.
- HU-3. Como desarrollador, quiero que git ignore claves y volcados, y que Claude Code pregunte antes de borrar contenedores con sus volúmenes, para no publicar ni perder datos por error.
- HU-4. Como usuario del mapa, quiero ver la atribución que exigen los proveedores de los datos.
- HU-5. Como desarrollador, quiero que la memoria del proyecto recoja lo que la revisión deja pendiente para otras specs.

## Definiciones
- **v2 de las imágenes**: las once imágenes de la v1 más el kayak regenerado, todas con el fondo quitado con remove.bg. Es el único conjunto anterior a la v3 que entró en git.
- **Comprobable con git**: un hecho que se puede comprobar con órdenes de git de solo lectura sobre el repositorio (`git show`, `git log`, `git ls-tree`, `git branch --contains`).
- **Ruta personal**: una ruta absoluta bajo el directorio personal del usuario del sistema.

## Requisitos funcionales
- RF-1: EL SISTEMA documenta en el registro de procedencia de la 017 que solo la v2 entró en git, en el commit `406b9af` (doce WebP), y que `2599bc3` no añade ninguna WebP.
- RF-2: EL SISTEMA documenta en ese registro que las WebP de la v2 siguen en el historial público por decisión del desarrollador y que el producto no las sirve desde `63b98cb`.
- RF-3: EL SISTEMA marca como «según el desarrollador» toda afirmación nueva o corregida de ese apartado que no sea comprobable con git.
- RF-4: EL SISTEMA no contiene, en ningún fichero versionado, una ruta personal ni el nombre del usuario del sistema como palabra completa.
- RF-5: EL SISTEMA describe en los registros de pruebas de mecanismo de la 006 dónde vivió la copia temporal sin dar su ruta.
- RF-6: EL SISTEMA hace que git ignore, en cualquier carpeta, los ficheros `*.pem`, `*.key`, `*.p12`, `id_rsa*`, `*.sql` y `*.dump`.
- RF-7: SI un fichero se llama `.env.example`, ENTONCES EL SISTEMA sigue sin ignorarlo, en la raíz y en `frontend/`.
- RF-8: CUANDO Claude Code va a ejecutar `docker rm -v` o `docker compose rm -v`, EL SISTEMA pide confirmación. El resto de permisos del proyecto no cambia.
- RF-9: EL SISTEMA conserva la atribución del mapa con el texto que da la página oficial de OpenFreeMap, incluido «Data from» en inglés, como excepción registrada al idioma de la interfaz. Registra la cita, la fecha de consulta, la huella de la página y la excepción.
- RF-10: EL SISTEMA recoge en la memoria del proyecto:
  - que no hay servidor de producción;
  - en la 007, que la consulta de la lista pública no puede usar el índice espacial y cómo se mide antes de tocarla;
  - el cierre de la revisión previa al lanzamiento, conservando lo que sigue pendiente de ella;
  - el número del PR de la 017;
  - la hoja de ruta con la 015 (entrada) antes de la 007: la 015, sin fondos con fotos y con el aviso pendiente de `user_logged_out`; las fotos de registro y entrada, en una spec pequeña justo antes de la 008 (portada), con su licencia anotada;
  - como pendientes de la 014 o de la 011, sin resolverlos: el aviso de la licencia OFL-1.1 de la fuente Bricolage Grotesque, y que cuatro skills versionadas no tienen licencia anotada (grill-me, grilling, systematic-debugging y web-design-guidelines).

  Todo ello dentro del límite de ~50 líneas.
- RF-11: EL SISTEMA registra en la validación de la 018 la comprobación de cada RF con la orden ejecutada y su resultado.

## Requisitos no funcionales
- **Privacidad**: ningún commit de esta spec añade rutas personales ni el nombre del usuario del sistema. Se comprueba sobre las líneas añadidas de lo preparado para el commit, antes de proponerlo.
- **Seguridad**: los cambios de `.gitignore` no dejan de ignorar ningún fichero que hoy se ignore. Los de los permisos de Claude Code solo añaden casos en los que se pregunta: nada pasa de preguntar a permitir.
- **Permisos de la API**: la spec no toca endpoints; no hay accesos de anónimo, usuario ni propietario que declarar.
- **Idioma**: la interfaz va en castellano (constitución, punto 8). Única excepción: la atribución del mapa, cuyo texto da el proveedor (RF-9); queda registrada.
- **Historial**: no se reescribe ningún commit existente; los hashes citados en las specs siguen siendo válidos.

## Casos límite
- Las órdenes de comprobación de RF-4 contienen ellas mismas el patrón que buscan: se escriben de forma que no coincidan consigo mismas.
- El nombre de la cuenta de GitHub, que aparece en los enlaces de las validaciones, contiene el nombre del usuario, pero no como palabra completa: RF-4 no lo toca.
- Un patrón nuevo de `.gitignore` podría coincidir con un fichero ya versionado: hoy no coincide ninguno, y git no deja de seguir lo que ya sigue.
- La página de OpenFreeMap cambia después de la consulta: vale la cita registrada con su fecha y su huella.

## Fuera de alcance
- Purgar del historial las WebP de la v2.
- Traducir la atribución del mapa o cambiar cualquier código del frontend.
- Cambiar la consulta de la lista pública o sus índices.
- HTTPS, HSTS, proxy, CSP, compresión, servidor de producción y todo lo de la 011.
- Los permisos locales de Claude Code (`settings.local.json`).
- Otras variantes de borrado de contenedores, como `docker rm -fv` o `docker container rm`.
- Las licencias de las skills versionadas y el aviso de la licencia de la fuente.

## Criterios de finalización
- Cada RF tiene su comprobación registrada en `specs/018-prelaunch-cleanup/validation.md`.
- La spec no tiene pantalla ni cambia la interfaz:
  - RF-1 a RF-8, RF-10 y RF-11 se comprueban con órdenes reales sobre el repositorio (`git grep`, `git check-ignore`, `git show`) y con la carga del JSON de permisos.
  - RF-9, con la descarga real de la página del proveedor.
- pytest, vitest, build y eslint en verde una vez al cerrar; pytest, con el stack ya levantado.

## Dudas abiertas
Ninguna. Resueltas al aprobar:
- RF-9: se conserva el texto del proveedor (D2 = A del plan).
- RF-10: «lo pendiente» es lo que sigue abierto de la revisión previa al lanzamiento.
