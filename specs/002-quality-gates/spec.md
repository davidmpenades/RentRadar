# Spec 002 — Puertas de calidad: comprobación previa al commit e integración continua
Estado: borrador
Depende de: spec 001 (esqueleto del backend), en concreto de RF-33 (la suite de tests se ejecuta sin indicar el entorno, en `test`, y falla con código distinto de cero), RF-35 (el análisis estático revisa estilo, errores comunes y formato sin cargar la aplicación) y RF-26 y RF-27 (la plantilla de variables incluye todas las que lee el backend, con valores de ejemplo legibles y no aleatorios).

## Contexto y objetivo
La spec 001 permite ejecutar los tests y el análisis estático a mano. La constitución (punto 4) exige que ningún commit se haga en rojo, y la regla de "secretos nunca en git" (AGENTS.md y punto 6) no puede depender de la memoria de quien hace el commit. Esta spec automatiza dos puertas:
- **antes de cada commit**: análisis estático, formato y detección de secretos, rápidos y sin necesidad de tener el entorno levantado;
- **en integración continua**: el análisis estático, la suite completa contra una base de datos geoespacial y la comprobación de migraciones, en cada cambio que llega al repositorio remoto.

Los tests no se ejecutan antes del commit: los garantizan el flujo de implementación de cada tarea y la integración continua.

## Usuarios
- **Desarrollador del equipo**: hace commits y sube ramas.
- **Revisor de cambios**: consulta el resultado de la integración continua antes de integrar una rama.

## Historias de usuario
- HU-1. Como desarrollador, quiero que el commit se bloquee si el código no supera el análisis estático o el formato, o si contiene un secreto, para no ensuciar el historial ni filtrar credenciales.
- HU-2. Como revisor, quiero que la integración continua ejecute los tests y el análisis en cada cambio y marque claramente lo que falla, para no integrar nada en rojo.

## Definiciones
- **Comprobación previa al commit**: la verificación automática que se ejecuta en la máquina del desarrollador al hacer un commit y que puede impedirlo.
- **Secreto**: cualquier credencial que dé acceso a un sistema: claves privadas, tokens, contraseñas o cadenas de conexión con contraseña.
- **Petición de integración**: la propuesta de integrar una rama en otra en el repositorio remoto.
- **Entorno limpio**: una máquina sin estado previo, en la que todo se instala desde las dependencias fijadas del repositorio.

## Requisitos funcionales

### Comprobación previa al commit
- RF-1: CUANDO el desarrollador intenta un commit que incluye código del backend que no supera el análisis estático o el formato, EL SISTEMA bloquea el commit y muestra las infracciones.
- RF-2: SI un commit incluye un secreto (clave privada, token, credencial) o un fichero de variables de entorno local, ENTONCES EL SISTEMA bloquea el commit e indica el fichero y la línea, sin mostrar el secreto completo.

### Integración continua
- RF-3: CUANDO se sube un cambio a cualquier rama del repositorio remoto, o se abre o actualiza una petición de integración, EL SISTEMA ejecuta en un entorno limpio el análisis estático y la suite de tests contra una base de datos geoespacial.
- RF-4: CUANDO la integración continua se ejecuta, EL SISTEMA comprueba que no hay cambios en el modelo de datos sin su migración correspondiente.
- RF-5: SI falla algún paso de la integración continua, ENTONCES EL SISTEMA marca la ejecución como fallida y muestra qué paso ha fallado.
- RF-6: EL SISTEMA ejecuta la integración continua sin secretos reales de producción.

## Requisitos no funcionales
- **Permisos**: esta spec no expone endpoints, así que no hay accesos de anónimo, usuario ni propietario que declarar.
- **Reparto del principio 4 de la constitución**: el análisis estático, el formato y la detección de secretos se comprueban antes de cada commit; los tests se ejecutan en el flujo de implementación de cada tarea; y la integración continua lo comprueba todo y es la puerta obligatoria. Este reparto queda documentado en el repositorio.
- **Seguridad**: la integración continua se ejecuta con permisos de solo lectura sobre el repositorio. Ni la comprobación previa al commit ni la integración continua muestran secretos completos en su salida.
- **Coherencia**: la integración continua usa la misma versión mayor de la base de datos geoespacial y las mismas dependencias fijadas que el entorno local de la spec 001.
- **Rapidez**: la comprobación previa al commit no necesita el entorno local levantado ni acceso a la base de datos.
- **Idioma**: nombres de pasos y configuración en inglés; documentación en castellano (constitución, punto 8).

## Casos límite
- Un commit que solo toca documentación no se bloquea por el análisis del backend, pero sí pasa la detección de secretos (RF-2).
- La detección de secretos se encuentra con la plantilla de variables de la spec 001: no la bloquea, porque la plantilla trae valores de ejemplo legibles y no aleatorios (RF-27 de la spec 001: "el de la clave secreta contiene `insecure-`").
- Un secreto aparece en un fichero que no es de código (documentación, configuración): también bloquea el commit (RF-2).
- Un cambio llega a la vez por una subida de rama y por una petición de integración abierta: las dos ejecuciones son válidas y cada una informa por separado.
- La base de datos de la integración continua tarda en estar lista: la suite espera a que esté disponible en lugar de fallar por arrancar antes (coherente con el RF-3 de la spec 001: "si la base de datos tarda más que la aplicación en estar lista al arrancar, la aplicación espera a que esté disponible").
- El desarrollador se salta la comprobación previa al commit a propósito: la integración continua sigue siendo la puerta obligatoria (RF-3 y RF-5).

## Fuera de alcance
- **Los tests no se ejecutan en la comprobación previa al commit**: los garantizan el flujo de implementación de cada tarea y la integración continua.
- **Van como requisitos de la spec de despliegue**: la redirección a HTTPS, HSTS, la cabecera de confianza del proxy que termina TLS y que la comprobación de seguridad de despliegue del framework pase sin avisos en integración continua.
- Despliegue continuo y publicación de imágenes o artefactos.
- Reglas de protección de ramas en el repositorio remoto. Se configuran fuera del código.
- Puertas de calidad del frontend (irán con la spec del frontend).
- Comprobación de tipos estática, cobertura mínima de tests y análisis de vulnerabilidades de dependencias.
- Limpiar el historial de git de secretos ya subidos (no hay secretos en el historial (verificado con git grep)).

## Criterios de finalización
- Cada RF tiene una comprobación registrada en la validación:
  - RF-1: un commit con una infracción de formato queda bloqueado.
  - RF-2: un commit con un secreto de prueba y otro con un fichero de variables local quedan bloqueados.
  - RF-3 y RF-5: una ejecución real de la integración continua en una petición de integración sale en verde, y otra con un test roto a propósito sale en rojo y señala el paso que falla.
  - RF-4: un cambio de modelo sin migración hace fallar la integración continua.
  - RF-6: la configuración de la integración continua no usa ningún secreto de producción.
- La rama de la spec 001 integrada en dev pasa la integración continua en verde.
- El plan cabe en 10 tareas como máximo.

## Dudas abiertas
- Ninguna.
