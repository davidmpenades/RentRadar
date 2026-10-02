# Spec 003 — Comprobaciones de salud
Estado: borrador
Depende de: spec 001 (esqueleto del backend). Se implementa después de la 002.

## Contexto y objetivo
Un orquestador o un sistema de monitorización necesita dos respuestas distintas:
- si el proceso está **vivo**, para reiniciarlo solo cuando de verdad no responde;
- si el servicio está **preparado** para atender tráfico, incluida su base de datos, para dejar de enviarle peticiones o avisar de una caída sin reiniciarlo.

Mezclar las dos provocaría reinicios en cadena cada vez que cae la base de datos. Ambas son anónimas y no revelan nada interno, porque cualquiera puede consultarlas. Además, la de preparación no puede convertirse en una forma barata de saturar la base de datos.

## Usuarios
- **Cliente anónimo de las comprobaciones de salud**: un orquestador, un balanceador o un sistema de monitorización. No se autentica.

## Historias de usuario
- HU-1. Como orquestador, quiero saber sin autenticarme si el proceso está vivo, para reiniciarlo solo cuando de verdad no responde.
- HU-2. Como orquestador o sistema de monitorización, quiero saber sin autenticarme si el servicio está preparado, incluida su base de datos, para dejar de enviarle tráfico o avisar de una caída.
- HU-3. Como operador, quiero que ante un fallo de preparación quede la causa en el log del servidor y no en la respuesta pública, para diagnosticar sin exponer detalles.

## Definiciones
- **Comprobación de vida**: responde si el proceso de la aplicación atiende peticiones. No consulta la base de datos ni ningún otro servicio.
- **Comprobación de preparación**: responde si el servicio puede atender tráfico real. Exige que la base de datos acepte la conexión y resuelva una consulta trivial dentro del plazo de RF-5.
- **Estado**: el único dato de la respuesta. Toma uno de dos valores fijos, afirmativo o negativo, que documenta el contrato del plan y que no cambian sin cambiar esta spec.
- **Resultado reciente**: el último resultado de una consulta real de preparación, guardado en la memoria de cada proceso de la aplicación durante 2 segundos.
- **Operaciones de consulta**: la consulta completa (GET) y la consulta solo de cabeceras (HEAD). Los nombres de método son inevitables porque fijan qué devuelve 405.

## Requisitos funcionales

### Vida
- RF-1: CUANDO un cliente consulta la comprobación de vida, EL SISTEMA responde con éxito y un estado afirmativo sin consultar la base de datos.
- RF-2: MIENTRAS la base de datos no esté disponible, EL SISTEMA sigue respondiendo con éxito a la comprobación de vida.

### Preparación
- RF-3: CUANDO un cliente consulta la comprobación de preparación y la base de datos está disponible, EL SISTEMA responde con éxito y un estado afirmativo.
- RF-4: SI al consultar la comprobación de preparación la base de datos falla o rechaza la conexión, ENTONCES EL SISTEMA responde con el código de servicio no disponible y un estado negativo.
- RF-5: SI la base de datos no completa la conexión y la consulta trivial en 2 segundos, ENTONCES EL SISTEMA la trata como no disponible y responde como en RF-4.
- RF-6: EL SISTEMA cierra la conexión a la base de datos que abre la comprobación de preparación al terminar cada consulta real, también cuando falla o vence el plazo.
- RF-7: CUANDO existe un resultado reciente, EL SISTEMA responde a la comprobación de preparación con ese resultado sin consultar la base de datos.
- RF-8: CUANDO la base de datos vuelve a estar disponible tras una caída, EL SISTEMA responde con un estado afirmativo a la comprobación de preparación en un plazo de 2 segundos, sin reiniciar la aplicación.

### Forma de la respuesta
- RF-9: EL SISTEMA responde a ambas comprobaciones con una forma estable que contiene únicamente el estado.
- RF-10: EL SISTEMA no incluye en el cuerpo ni en las cabeceras de las respuestas de salud versiones de software, nombres de host o de base de datos, rutas, trazas, mensajes de error internos, valores de configuración ni estado por componente.
- RF-11: EL SISTEMA marca como no almacenables en caché todas las respuestas de ambas comprobaciones, también las de servicio no disponible y método no permitido.
- RF-12: EL SISTEMA atiende ambas comprobaciones sin crear sesión ni establecer cookies en ninguna respuesta, también en las de servicio no disponible y método no permitido.

### Acceso
- RF-13: EL SISTEMA no evalúa credenciales de ningún tipo en las comprobaciones de salud. Una petición con credenciales, válidas o inválidas, recibe la misma respuesta que una anónima y nunca un rechazo por autenticación o permisos.
- RF-14: EL SISTEMA no aplica límite de tasa a las comprobaciones de salud.
- RF-15: EL SISTEMA ignora los parámetros y el cuerpo de las peticiones de salud, y la respuesta es la misma que sin ellos.
- RF-16: CUANDO un cliente usa la consulta solo de cabeceras, EL SISTEMA responde con el mismo código y las mismas cabeceras que en la consulta completa, sin cuerpo.
- RF-17: SI se invoca una comprobación de salud con una operación que no sea de consulta, ENTONCES EL SISTEMA responde con el código de método no permitido, también si el cliente tiene una sesión iniciada, y nunca con un rechazo por protección contra falsificación de peticiones.

### Registro
- RF-18: SI una consulta real de preparación da un estado negativo, ENTONCES EL SISTEMA registra la causa en el log del servidor sin incluir la contraseña de la base de datos ni la clave secreta.
- RF-19: EL SISTEMA no registra en el log las comprobaciones con estado afirmativo ni las respondidas con el resultado reciente.

## Requisitos no funcionales
- **Permisos**: anónimo, usuario y propietario tienen el mismo acceso, solo consulta y sin autenticación. No hay recursos por objeto, así que el 404/403 de objeto (constitución, punto 5) no aplica. Hay tests de acceso anónimo y con credenciales inválidas (RF-13).
- **Rendimiento**: la comprobación de vida no hace ninguna consulta a la base de datos (verificable con un test que cuenta consultas). Como objetivos documentados, sin test: la vida responde en menos de 1 segundo y la preparación en menos de 3 segundos con la base de datos colgada.
- **Memoria por proceso**: el resultado reciente vive en la memoria de cada proceso, sin caché compartida (constitución, punto 1).
- **Idioma**: código e identificadores en inglés; documentación en castellano (constitución, punto 8).

## Casos límite
- La base de datos cae con la aplicación en marcha: la vida sigue en éxito (RF-2), la preparación pasa a negativo en 2 segundos como máximo (RF-4, RF-7) y vuelve a afirmativo en 2 segundos tras la recuperación (RF-8).
- La base de datos acepta la conexión pero no responde: a los 2 segundos cuenta como no disponible y la conexión se cierra (RF-5, RF-6).
- Ráfaga de consultas de preparación: dentro del plazo del resultado reciente no llegan a la base de datos (RF-7) y ninguna se rechaza por tasa (RF-14). Si varias peticiones simultáneas llegan justo al vencer el plazo, pueden consultar la base de datos a la vez; no se exige exclusión entre ellas.
- Varios procesos de la aplicación: cada uno tiene su propio resultado reciente. El plazo de RF-8 se cumple en cada proceso.
- El resultado reciente es negativo: durante su plazo se sigue respondiendo negativo aunque la base de datos ya se haya recuperado (dentro de RF-8).
- Una petición llega con credenciales inválidas o caducadas: misma respuesta que una anónima (RF-13).
- Un cliente con sesión iniciada envía una operación de escritura: método no permitido, no rechazo por falsificación de peticiones (RF-17).
- Una petición llega con parámetros o cuerpo (RF-15).
- En producción, las sondas solo llegan si su host está en la lista de hosts permitidos (RF-16 de la spec 001: "en `production`, una petición dirigida a un host que no está en la lista de hosts permitidos se rechaza como petición incorrecta"): el despliegue incluye ese host en la lista. No hay excepción para las comprobaciones de salud.
- Un límite de tasa global que se añada en una spec futura no afecta a las comprobaciones de salud (RF-14).

## Fuera de alcance
- Límites de tasa en general: necesitan una caché compartida, que es una dependencia nueva.
- Caché compartida del resultado reciente entre procesos.
- Estado por componente, versión o commit desplegado en la respuesta.
- Métricas, trazas distribuidas y alertas.
- **Van como requisitos de la spec de despliegue**:
  - la capacidad del servidor (procesos e hilos) para que la vida responda bajo carga;
  - si la plataforma sondea por IP dinámica (por ejemplo, Kubernetes), reabrir la decisión de no hacer excepción con los hosts y valorar eximir solo la comprobación de vida;
  - comprobar la extensión geoespacial y aplicar las migraciones antes de enviar tráfico a una versión nueva;
  - la redirección a HTTPS, HSTS, la cabecera de confianza del proxy y la comprobación de seguridad de despliegue del framework en integración continua.

## Criterios de finalización
- Cada RF tiene un test automático. Además, la validación registra un recorrido con la base de datos real detenida: la vida responde con éxito, la preparación con servicio no disponible, y al volver a arrancar la base de datos la preparación pasa a afirmativa en 2 segundos o menos.
- RF-18 se cubre con un test que provoca el fallo con una contraseña conocida y comprueba que no aparece en el log.
- La forma de la respuesta (RF-9) y sus dos valores de estado quedan documentados en el contrato del plan.
- El plan cabe en 10 tareas como máximo.

## Dudas abiertas
- [NECESITA ACLARACIÓN] (para el plan, no bloquea esta spec) ¿Las comprobaciones de salud se implementan como vistas del framework sin la capa de API, o como vistas de la capa de API con autenticación, permisos y límite de tasa vacíos?
- [NECESITA ACLARACIÓN] (para el plan, no bloquea esta spec) ¿Cómo se reparte el plazo de 2 segundos de RF-5 entre la conexión y la consulta, y ese plazo corto se aplica solo a la comprobación de preparación o a toda la aplicación?
