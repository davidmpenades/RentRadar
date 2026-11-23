# Spec 019 — Cadena de suministro
Estado: borrador
Depende de: spec 002 (integración continua mínima), cuyo flujo se amplía; spec 006, que añadió a esa integración continua las comprobaciones del frontend y la auditoría de npm; y el plan de seguridad del proyecto, cuya sección de cadena de suministro se actualiza.

## Contexto y objetivo
El proyecto ya construye de forma reproducible una parte de lo que usa: las dependencias de Python llevan hash y se instalan exigiéndolo, y el frontend se instala desde un lockfile versionado sin ejecutar scripts. La integración continua existe y audita las dependencias de producción de npm. Falta lo demás, y es lo que permite que algo ajeno entre sin que nadie lo vea:
- las imágenes base se identifican por una etiqueta que su autor puede mover;
- las dependencias de Python no se auditan;
- nada propone actualizaciones, así que las dependencias envejecen sin aviso;
- las acciones de la integración continua se identifican por una etiqueta que su autor puede mover;
- no hay ninguna comprobación de secretos, ni al hacer un commit ni en el historial ya publicado;
- el repositorio no impone que lo integrado haya pasado la integración continua, y los flujos de personas ajenas pueden ejecutarse sin que nadie los apruebe.

Esta spec cierra esos huecos, mantiene con una comprobación lo que ya está bien y deja el plan de seguridad al día. El objetivo es que cada pieza externa que entra en el proyecto (imagen base, paquete, acción, herramienta), salvo las bibliotecas de sistema de las imágenes (riesgos residuales), esté identificada de forma inmutable, vigilada y revisada por una persona antes de integrarse, y que ningún secreto llegue ni haya llegado al repositorio sin que se sepa.

## Usuarios
- **Desarrollador**: mantiene el repositorio, recibe las propuestas de actualización y los avisos, y rota lo que se filtre.
- **Revisor de cambios**: decide qué se integra en `dev` con el resultado de la integración continua delante.
- **Persona ajena al equipo**: puede proponer cambios desde una copia del repositorio; no debe poder ejecutar nada con permisos ni secretos del proyecto.

## Historias de usuario
- HU-1. Como desarrollador, quiero que las imágenes base y las acciones de la integración continua estén identificadas de forma inmutable, para que su autor no pueda cambiar lo que ejecuto sin que me entere.
- HU-2. Como desarrollador, quiero que la integración continua me avise de vulnerabilidades conocidas en las dependencias de Python y de npm, y recibir propuestas de actualización, para no depender de acordarme de mirar.
- HU-3. Como desarrollador, quiero que un secreto se detenga antes de entrar en un commit y que se compruebe una vez todo el historial, para saber si algo ya se filtró y rotarlo.
- HU-4. Como revisor, quiero que `dev` solo reciba cambios con la integración continua en verde y que los flujos de personas ajenas requieran aprobación, para que nadie salte la puerta de calidad ni ejecute código propio con los permisos del proyecto.
- HU-5. Como desarrollador, quiero que el plan de seguridad diga qué está hecho y qué falta, para decidir el siguiente paso con datos correctos.

## Definiciones
- **Digest**: el identificador criptográfico de una imagen de contenedor. Dos imágenes con el mismo digest son idénticas; una etiqueta, en cambio, puede apuntar a otra imagen mañana.
- **SHA de commit**: el identificador completo (40 caracteres) de un commit de una acción de GitHub. Una etiqueta de versión puede reasignarse; el SHA no.
- **Criterio de fallo**: la regla que decide qué avisos de una auditoría hacen fallar el paso (por ejemplo, severidad mínima o avisos sin versión corregida). Se decide en la clarificación (RF-4).
- **Pasada única del historial**: un análisis de secretos de todos los commits de todas las ramas y etiquetas del repositorio, hecho una vez por el desarrollador en su equipo, no en cada ejecución de la integración continua.
- **Rotar**: invalidar la credencial filtrada y emitir otra nueva. Borrar el secreto del historial no lo invalida: quien ya lo copió puede seguir usándolo.
- **Rama por defecto**: la rama contra la que el repositorio remoto abre por omisión las propuestas automáticas. Hoy es `dev` según la referencia remota local; se comprueba en el servidor con una consulta de solo lectura a su API (criterios de finalización).
- **Herramienta nueva**: cualquier programa que esta spec añade al proyecto o a la integración continua para auditar, vigilar o analizar (constitución, punto 1).

## Requisitos funcionales
- RF-1: EL SISTEMA referencia por digest todas las imágenes base de los contenedores del proyecto, incluida la imagen con la que se regeneran los locks de dependencias, con la etiqueta legible junto al digest.
- RF-2: EL SISTEMA documenta cómo actualizar un digest, tanto a mano como a partir de una propuesta automática, incluida la comprobación de que la imagen nueva se construye y pasa la integración continua antes de integrarla.
- RF-3: CUANDO se ejecuta la integración continua, EL SISTEMA audita las dependencias de Python fijadas contra una base de vulnerabilidades conocidas, y la auditoría de npm que ya existe sigue auditando las de npm. Cada auditoría va en un trabajo propio, que se ejecuta aunque fallen otras comprobaciones.
- RF-4: SI la auditoría de Python o la de npm encuentra un aviso que cumple el criterio de fallo, ENTONCES EL SISTEMA falla ese paso y marca la ejecución como fallida. Los avisos que no cumplen el criterio se muestran sin fallar. Toda excepción a un aviso se registra con su motivo y una fecha de revisión; pasada esa fecha, el paso falla. [NECESITA ACLARACIÓN: el criterio]
- RF-5: SI una auditoría no puede completarse (servicio de avisos inaccesible o error de la herramienta), ENTONCES EL SISTEMA no da el paso por superado.
- RF-6: EL SISTEMA propone de forma periódica actualizaciones de las dependencias de Python, de npm, de las imágenes y de las acciones de la integración continua, como propuestas de integración hacia la rama por defecto. Las propuestas de actualización de versión esperan un periodo mínimo desde que la versión se publica en su registro, en todos los ecosistemas.
- RF-7: EL SISTEMA referencia cada acción de la integración continua por el SHA completo de un commit, con la versión legible en un comentario de la misma línea.
- RF-8: CUANDO el desarrollador crea un commit, EL SISTEMA analiza en busca de secretos el contenido preparado para el commit, no el árbol de trabajo, y rechaza el commit si encuentra alguno.
- RF-9: CUANDO se ejecuta la integración continua, EL SISTEMA analiza en busca de secretos todos los commits que el cambio añade respecto a la rama de destino y falla si encuentra alguno. SI ese rango no se puede resolver o está vacío, ENTONCES EL SISTEMA falla el paso. El paso muestra cuántos commits analizó. El análisis de secretos va en un trabajo propio, que se ejecuta aunque fallen otras comprobaciones.
- RF-10: EL SISTEMA hace una pasada única por todo el historial (todas las ramas y etiquetas) y registra en la validación cuántos hallazgos hubo y cómo se resolvió cada uno, sin incluir ningún valor.
- RF-11: SI un hallazgo es un secreto real, ENTONCES EL SISTEMA exige rotar la credencial y registrar la rotación (qué se rotó y cuándo, sin valor); borrarlo del historial no la da por resuelta. SI es un falso positivo, ENTONCES EL SISTEMA lo registra con su motivo. Las excepciones del análisis de secretos se definen por hallazgo concreto, nunca por ruta ni por regla, cada una con su motivo; añadir una excepción es un cambio de control y se revisa como tal.
- RF-12: EL SISTEMA exige, para integrar en `dev`, que la integración continua esté en verde y que el cambio llegue por una propuesta de integración, sin empujes forzados ni borrado de la rama. Es un ajuste manual del repositorio remoto que hace el propietario, y la spec registra cómo se comprueba.
- RF-13: MIENTRAS una propuesta venga de una copia ajena del repositorio, EL SISTEMA exige la aprobación de una persona con permiso de escritura antes de ejecutar sus flujos. Además, el repositorio remoto bloquea en el servidor los envíos que contienen secretos de formatos conocidos. Ambos son ajustes manuales del repositorio remoto que hace el propietario, y la spec registra cómo se comprueba cada uno.
- RF-14: EL SISTEMA recoge en el plan de seguridad que el alcance de una revisión de seguridad se declara de forma explícita (la revisión automática solo ve el diff) en lugar de prometer una revisión de todo el módulo, y que su sección de cadena de suministro refleja lo hecho y lo pendiente, incluido el riesgo de los MCP y los plugins de Claude Code sin fijar ni auditar, que se lleva a la spec del arnés.
- RF-15: EL SISTEMA instala siempre desde dependencias fijadas, y lo comprueba:
  - Python: toda dependencia, transitivas incluidas, tiene hash en su lock y la instalación lo exige. SI una dependencia no lo tiene, ENTONCES la construcción de la imagen falla.
  - Frontend: la instalación usa el lockfile versionado, sin ejecutar scripts de instalación. SI el lockfile falta o no coincide con las dependencias declaradas, ENTONCES la instalación falla.

## Requisitos no funcionales
- **Seguridad**:
  - Ninguna propuesta automática de actualización se integra sin revisión humana ni sin pasar la integración continua.
  - Ningún análisis de secretos imprime ni guarda el valor encontrado: ni en pantalla, ni en los logs de la integración continua, ni en los informes que se conserven.
  - Las herramientas nuevas se fijan por versión exacta y, las que corren en la integración continua, por una referencia inmutable (RF-7). Su incorporación necesita aprobación explícita (constitución, punto 1); se pide en la clarificación.
  - La integración continua no gana permisos ni secretos: sigue con permisos de solo lectura y sin secretos de GitHub, salvo que la clarificación decida lo contrario para una herramienta concreta.
  - Un hallazgo de secreto detiene el trabajo y se resuelve antes de seguir (RF-11).
  - El servicio que analiza secretos en el equipo corre sin red, monta solo lo necesario y en solo lectura, sin capacidades ni privilegios adicionales, con un usuario que no es administrador, y no arranca con el resto del entorno de desarrollo.
- **Privacidad**:
  - Ningún fichero versionado de esta spec, incluida la configuración de las herramientas de análisis, contiene rutas personales ni el nombre del usuario del sistema, ni patrones para buscarlos.
  - Los informes de las pasadas se guardan fuera del repositorio o se descartan; los que se versionen no llevan valores.
- **Reproducibilidad**: las comprobaciones se ejecutan igual en local y en la integración continua cuando es posible (constitución, punto 3).
- **Permisos de la API**: la spec no toca endpoints; no hay accesos de anónimo, usuario ni propietario que declarar.
- **Idioma**: nombres de pasos y configuración en inglés; documentación y comentarios en castellano (constitución, punto 8).
- **Accesibilidad y móvil**: no aplican; la spec no cambia la interfaz.

## Amenazas
| Amenaza | Cómo se materializa | Qué la acota | RF |
|---|---|---|---|
| Etiqueta de imagen reasignada | El autor de una imagen base, o quien le robe la cuenta, publica otra imagen bajo la misma etiqueta y la siguiente construcción la usa | Digest en todas las imágenes | RF-1, RF-2 |
| Acción de la integración continua comprometida | Se mueve la etiqueta de una acción y el flujo ejecuta código ajeno con acceso al repositorio | SHA de commit; permisos de solo lectura; sin secretos | RF-7 y seguridad |
| Paquete de Python o npm malicioso o vulnerable | Una versión nueva o una transitiva con aviso publicado entra en el lock | Hashes y lockfile; auditoría con criterio de fallo; propuestas de actualización revisadas | RF-3 a RF-6, RF-15 |
| Versión maliciosa recién publicada | Una versión comprometida se publica y una propuesta automática la trae antes de que se detecte; la integración continua de la propuesta la ejecuta antes de cualquier revisión | Periodo mínimo de espera antes de proponerla; integración continua sin secretos y de solo lectura | RF-6 y seguridad |
| Lock manipulado en una propuesta | Una propuesta cambia un hash o un lockfile para colar un paquete | Revisión del diff de la propuesta por el desarrollador; la instalación que falla si no coincide solo detecta un lock inconsistente, no un paquete y su hash cambiados a la vez; integración continua obligatoria | RF-12, RF-15 |
| Secreto en un commit | Una clave o contraseña entra en el repositorio público y alguien la copia. El análisis de la integración continua detecta después del envío, con el commit ya público | Solo el análisis al hacer commit y el bloqueo del servidor lo previenen; el de la integración continua lo detecta tarde y obliga a rotar | RF-8, RF-9, RF-11, RF-13 |
| Secreto ya presente en el historial | Algo se filtró en un commit antiguo y sigue ahí | Pasada única; rotación obligatoria | RF-10, RF-11 |
| Flujo de una copia ajena | Una propuesta externa modifica un flujo para extraer permisos o ejecutar código | Aprobación previa; sin secretos ni escritura; sin eventos privilegiados (prohibidos en la spec 002) | RF-13 y seguridad |
| Salto de la puerta de calidad | Un empuje directo o forzado a `dev` evita la integración continua | Protección de la rama | RF-12 |
| Herramienta de seguridad comprometida | El propio analizador o auditor trae código malicioso | Versión exacta y referencia inmutable; aprobación explícita; sin secretos en la integración continua; aislamiento del servicio de análisis en el equipo | seguridad |
| Fatiga o falsa seguridad | Un criterio de fallo demasiado estricto se ignora, o uno laxo deja pasar lo importante; los digests envejecen sin parches | Criterio decidido y registrado; propuestas periódicas; avisos sin ignorar en silencio | RF-4, RF-6 |
| Aviso mudo | La auditoría no llega al servicio de avisos y todo parece verde | Una auditoría incompleta no cuenta como superada | RF-5 |
| Hook saltado | El análisis al hacer commit se omite o no está instalado en un clon nuevo. La integración continua lo detecta tarde, con el commit ya público, y obliga a rotar | La integración continua repite el análisis; el bloqueo del servidor solo cubre formatos conocidos | RF-9, RF-11, RF-13 |
| El control viaja en el cambio | Una propuesta (propia, ajena o automática) modifica a la vez el código y el control que debía detenerlo: configuración o excepciones del analizador, hook, servicio de análisis o flujo de la integración continua. La integración continua de una propuesta ejecuta el flujo que trae la propia propuesta | Revisión explícita por el desarrollador de todo cambio en esos ficheros de control antes de integrarlo; excepciones solo por hallazgo concreto | RF-11, RF-12 y seguridad |
| El hook como vía de ejecución | El hook versionado se ejecuta en la versión de la rama que esté en el árbol de trabajo; tras cambiar a una rama ajena para revisarla, el siguiente commit ejecuta lo que esa rama traiga, con los permisos del desarrollador | Revisar el diff de los ficheros de control antes de cambiar a una rama no propia; un hook mínimo que solo lanza una orden fija; el aislamiento del servicio de análisis | RF-8 y seguridad |
| Complementos del arnés | MCP y plugins de Claude Code, sin fijar ni auditar, ejecutan código con los permisos del desarrollador | Fuera de alcance: se anota en el plan de seguridad y se lleva a la spec del arnés | RF-14 |

Riesgos residuales aceptados: las bibliotecas de sistema instaladas en la imagen desde el gestor de paquetes del sistema operativo no se fijan ni se auditan aquí, y por eso dos construcciones con el mismo digest base pueden dar imágenes distintas; la herramienta de bloqueo se instala sin hashes al regenerar los locks; el bloqueo de secretos del servidor lo puede saltar quien hace el envío; las propuestas automáticas por un aviso de seguridad no respetan el periodo de espera, y la integración continua ejecuta la versión nueva en cuanto se abre la propuesta; una vulnerabilidad sin aviso publicado no se detecta; la protección de ramas no impide al propietario saltarse sus propias reglas si se le deja esa opción.

## Casos límite
- Las propuestas automáticas llegan varias a la vez: la integración continua las ejecuta una por una y la clarificación decide si se agrupan.
- La herramienta de análisis de secretos no puede quedarse en una versión congelada: sus reglas envejecen y dejan de detectar formatos nuevos. Se actualiza por las propuestas automáticas o, si no es posible, con una revisión manual periódica que queda registrada (RF-6, RF-8, RF-9).
- Una etiqueta de imagen se actualiza con un parche de seguridad, pero el digest fijado sigue apuntando a la imagen anterior: sin la propuesta automática el parche no llega (RF-6).
- Una imagen de varias arquitecturas tiene un digest del índice y uno por arquitectura: la clarificación decide cuál se fija.
- La auditoría encuentra un aviso sin versión corregida publicada: el criterio de fallo debe decir qué pasa (RF-4).
- La auditoría encuentra un aviso en una dependencia de desarrollo que no llega a producción: el criterio de fallo debe decir qué pasa (RF-4).
- Un análisis de secretos marca datos de ejemplo o cuentas de prueba: se registra como falso positivo con su motivo y no se silencia sin registro (RF-11).
- Un secreto hallado en el historial ya está caducado o dado de baja: se registra igualmente, con la fecha de su invalidación.
- Un clon nuevo no tiene instalado el análisis al hacer commit: la integración continua lo detecta tarde, con el commit ya público, y obliga a rotar; el bloqueo del servidor solo cubre formatos conocidos (RF-8, RF-9, RF-11, RF-13).
- La versión legible junto a un SHA no coincide con el SHA: vale el SHA; la propuesta automática mantiene el comentario al día.
- Una acción no tiene versión publicada que corresponda al commit más reciente: la propuesta automática debe indicarlo y se revisa a mano (RF-6).
- La rama por defecto del repositorio remoto cambia: las propuestas automáticas siguen a la nueva rama por defecto salvo que se indique otra (RF-6).
- Una propuesta automática cambia un lock de Python con una versión de la herramienta de bloqueo distinta de la que fija el proyecto: la propuesta debe mantener los hashes (RF-6, RF-15).
- El servicio de avisos de Python o de npm cae durante una ejecución: el paso no pasa (RF-5).

## Fuera de alcance
- MCP y plugins de Claude Code sin fijar ni auditar: se anotan como riesgo (RF-14) y se resuelven en la spec del arnés.
- Firma de imágenes, SBOM, atestaciones y escaneo de vulnerabilidades de las imágenes construidas.
- Fijar o auditar las bibliotecas de sistema que instala la imagen del backend.
- Reescribir o purgar el historial para quitar un secreto: se rota, no se borra.
- Análisis de secretos en incidencias, propuestas, comentarios o logs de la integración continua.
- Análisis estático del código (SAST), análisis de licencias y gestión de secretos de producción (spec de despliegue).
- Cambiar versiones de dependencias salvo lo que una auditoría exija (RF-4): las actualizaciones normales entran por las propuestas automáticas.
- Protección de otras ramas distintas de `dev`.

## Criterios de finalización
- La spec no tiene pantalla: cada RF se comprueba con una petición real de punta a punta y se registra en la validación, con el enlace a cada ejecución.
  - RF-1, RF-7 y RF-14: `git grep` sobre lo versionado que muestra que no queda ninguna referencia sin fijar, la de la imagen de regeneración de los locks incluida, y que el plan de seguridad dice lo pedido.
  - RF-2: el procedimiento documentado se ejecuta una vez de verdad sobre una imagen.
  - RF-3, RF-4 y RF-5: ejecuciones reales en una rama desechable, sin integrar nada de eso: con una dependencia con aviso conocido (falla), limpia (verde) y con el servicio de avisos inaccesible (no pasa). Este último caso se provoca dando a ese paso, solo en la rama desechable, un proxy inexistente, sin cortar la red del resto de la ejecución. En la misma rama, con un test que falla a propósito, las dos auditorías y el análisis de secretos se ejecutan igualmente.
  - RF-6: la configuración está activa en el repositorio remoto, declara el periodo de espera en cada ecosistema y llega al menos una propuesta de cada ecosistema, o se registra por qué no. La rama por defecto del repositorio remoto se comprueba en el servidor con una consulta de solo lectura a su API, y se registra.
  - RF-8: un commit local con un secreto sintético inventado se rechaza y nunca se envía; también se rechaza un commit con el secreto sintético preparado y el árbol de trabajo sin él; el mismo commit sin secreto se acepta. El valor del secreto sintético no aparece en la salida ni en ningún fichero del árbol de trabajo.
  - RF-9: la validación con un secreto sintético no se hace en este repositorio público, porque el envío lo publicaría. Se hace en un repositorio desechable privado con el mismo flujo, u otra vía que decida la clarificación; en este repositorio solo se comprueba que el flujo sin secreto pasa. El valor del secreto sintético no aparece en el registro de la ejecución del repositorio desechable privado ni en ningún fichero del árbol de trabajo. Una prueba de mecanismo en la rama desechable muestra que un rango que no se puede resolver hace fallar el paso.
  - RF-10 y RF-11: la pasada se hace y se registra, con el resultado y la acción tomada, sin valores.
  - RF-12: consulta de solo lectura de la protección de `dev` y un envío directo a `dev`, sin secreto, que se rechaza.
  - RF-13, flujos de copias ajenas: consulta de solo lectura del ajuste. La prueba real desde una copia ajena se hace solo si se dispone de una segunda cuenta; si no, se registra que no se hizo y por qué.
  - RF-13, bloqueo de secretos: solo el estado del ajuste, con una consulta de solo lectura. No se envía ningún secreto de prueba a este repositorio.
  - RF-15: dos comprobaciones de mecanismo en rama desechable (quitar un hash, desincronizar el lockfile) que hacen fallar la construcción y la instalación.
  - Aislamiento del análisis local: una prueba de mecanismo muestra que el servicio de análisis no tiene red y no puede escribir en lo que monta.
- Las suites de tests, la compilación y el análisis estático, del backend y del frontend, en verde una vez al cerrar.

## Dudas abiertas
- [NECESITA ACLARACIÓN] Criterio de fallo de las auditorías (RF-4): severidad mínima, avisos sin versión corregida y dependencias de desarrollo frente a producción.
- [NECESITA ACLARACIÓN] Aprobación explícita de las herramientas nuevas: auditor de Python, analizador de secretos y gestor de hooks (constitución, punto 1).
- [NECESITA ACLARACIÓN] Si se comprueba en la integración continua que las imágenes y acciones siguen fijadas, o basta con las propuestas automáticas (RF-1, RF-7).
- [NECESITA ACLARACIÓN] Agrupación, frecuencia, límite y periodo mínimo de espera de las propuestas automáticas (RF-6).
- [NECESITA ACLARACIÓN] Qué digest se fija en imágenes de varias arquitecturas (RF-1).
- [NECESITA ACLARACIÓN] Cuántas comprobaciones se hacen obligatorias para integrar en `dev` y cuántas aprobaciones se exigen con un solo desarrollador (RF-12).
- [NECESITA ACLARACIÓN] Cómo se ejecuta y se actualiza el análisis al hacer commit (RF-8): con la misma referencia fijada que usa la integración continua o con un gestor de hooks aparte, y quién lo mantiene al día.
- [NECESITA ACLARACIÓN] Cómo se valida RF-9 sin publicar el secreto sintético en este repositorio público: repositorio desechable privado con el mismo flujo, u otra vía.
- [NECESITA ACLARACIÓN] Si las propuestas automáticas (RF-6) cubren también las imágenes de la orquestación de contenedores, que se gestionan con un soporte distinto del de las imágenes de construcción.
- [NECESITA ACLARACIÓN] Contradicción entre RF-12 y el riesgo residual de «el propietario puede saltarse sus propias reglas»: falta decidir si las reglas se exigen también a los administradores (y entonces ese riesgo desaparece) o si el riesgo se mantiene y se acepta.
