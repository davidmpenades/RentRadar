# Spec 002 — Integración continua mínima
Estado: aprobada
Depende de: spec 001 (esqueleto del backend), en concreto de RF-33 (la suite de tests se ejecuta sin indicar el entorno, en `test`, y falla con código distinto de cero), RF-35 (el análisis estático revisa estilo, errores comunes y formato sin cargar la aplicación) y RF-26 y RF-27 (la plantilla de variables incluye todas las que lee el backend, con valores de ejemplo legibles y no aleatorios).

## Contexto y objetivo
La spec 001 permite ejecutar los tests y el análisis estático a mano. La constitución (punto 4) exige que nada se integre en rojo. Esta spec añade una única puerta: una integración continua en GitHub Actions que ejecuta el análisis estático y los tests del backend con Docker Compose, igual que en local.

## Usuarios
- **Desarrollador del equipo**: sube ramas y abre peticiones de integración.
- **Revisor de cambios**: consulta el resultado antes de integrar una rama en `dev`.

## Historias de usuario
- HU-1. Como revisor, quiero que la integración continua ejecute el análisis estático y los tests en cada cambio y marque claramente qué paso falla, para no integrar nada en rojo.

## Definiciones
- **Petición de integración**: la propuesta de integrar una rama en otra en el repositorio remoto (pull request).
- **Entorno limpio**: una máquina sin estado previo, en la que todo se construye desde el repositorio.
- **Análisis estático**: `ruff check` y `ruff format --check` sobre el backend (RF-35 de la 001).
- **Suite de tests**: `pytest -q` sobre el backend (RF-33 de la 001).

## Requisitos funcionales
- RF-1: CUANDO se sube un cambio a `dev` o a una rama `feature/**`, o se abre, se actualiza con nuevos commits o se reabre una petición de integración hacia `dev`, EL SISTEMA ejecuta la integración continua, aunque el cambio solo toque documentación.
- RF-2: EL SISTEMA ejecuta la integración continua en un entorno limpio (`ubuntu-latest` hospedado) con Docker Compose, con la imagen del backend construida desde el mismo Dockerfile y `docker-compose.yml` que el entorno local; la versión de la base de datos geoespacial es la que fija `docker-compose.yml`.
- RF-3: EL SISTEMA ejecuta tres pasos visibles y separados, en este orden: preparación, análisis estático y tests. SI falla uno, ENTONCES los siguientes no se ejecutan.
  - Preparación: crea el fichero de variables a partir de la plantilla del repositorio (`cp .env.example .env`) y construye la imagen. No usa secretos de GitHub.
  - Análisis estático: usa la orden de AGENTS.md con `--no-deps` y `--entrypoint ""`, sin base de datos. El fichero de variables lo exige la interpolación de Compose, no la base de datos.
  - Tests: `pytest -q` contra la base de datos geoespacial, con el entorno `test` (RF-33 de la 001).
- RF-4: SI falla algún paso, ENTONCES EL SISTEMA marca la ejecución como fallida y muestra qué paso ha fallado.
- RF-5: EL SISTEMA cancela la ejecución en curso de una rama cuando llega una nueva para esa misma rama.
- RF-6: AL terminar, falle o no algún paso, EL SISTEMA elimina los contenedores y volúmenes de la ejecución (`docker compose down -v`).
- RF-7: EL SISTEMA falla la suite de tests si hay cambios de modelos sin migración (`makemigrations --check --dry-run`). Se implementa como test de pytest, no como paso del CI, y amplía el RF-33 de la 001. Con cero modelos pasa en vacío.

## Requisitos no funcionales
- **Seguridad**:
  - El flujo declara `permissions: contents: read` a nivel de flujo.
  - La única acción de terceros es `actions/checkout`, aprobada como dependencia (constitución, punto 1), fijada a su versión mayor vigente y con `persist-credentials: false`.
  - No se usan secretos de GitHub; el único token es el `GITHUB_TOKEN` implícito, de solo lectura.
  - Los eventos permitidos son `push` y `pull_request`; `pull_request_target` y `workflow_run` están prohibidos. Las peticiones desde forks solo se ejecutan con `pull_request`, que da token de solo lectura y ningún secreto.
  - El flujo no vuelca el entorno en los logs (`docker compose config`, `env`, `set -x`).
- **Lint sin base de datos**: el paso de análisis estático no necesita la base de datos (RF-35 de la 001).
- **Coherencia**: el flujo no duplica versiones ni órdenes: reutiliza `docker-compose.yml` y las órdenes de AGENTS.md.
- **Permisos de la API**: la spec no expone endpoints, así que no hay accesos de anónimo, usuario ni propietario que declarar.
- **Idioma**: nombres de pasos y configuración en inglés; comentarios y documentación en castellano (constitución, punto 8).

## Casos límite
- La base de datos tarda en estar lista: los tests esperan a que esté disponible gracias al healthcheck de Compose en lugar de fallar por arrancar antes.
- Un cambio llega a la vez por una subida de rama y por una petición de integración: se aceptan las dos ejecuciones y cada una informa por separado.
- Falla el análisis estático: el paso de tests no se ejecuta y el resultado indica el paso que falló (RF-3, RF-4).
- Los tests se ejecutan dentro del contenedor: el test de `geteuid == 10001` exige este modo (RF-2).
- Llegan commits nuevos a una rama con una ejecución en curso: se cancela la anterior (RF-5).

## Fuera de alcance
- Pasan a una spec posterior: pre-commit, detección de secretos y escaneo del historial.
- Protección de ramas: es un ajuste manual en GitHub que hace el propietario cuando la integración continua esté en verde.
- Despliegue continuo y publicación de imágenes.
- Puertas de calidad del frontend (irán con la spec del frontend).
- Comprobación de tipos estática, cobertura mínima de tests y análisis de vulnerabilidades de dependencias.
- Requisitos de despliegue (HTTPS, HSTS, proxy, `check --deploy`): van en la spec de despliegue.

## Criterios de finalización
- Cada RF tiene una comprobación registrada en `specs/002-quality-gates/validation.md`, con el enlace a cada ejecución:
  - RF-1, RF-2, RF-3, RF-5 y RF-6: una ejecución real sobre una petición de integración hacia `dev` sale en verde con los tres pasos visibles y el flujo no referencia ningún secreto de GitHub.
  - RF-4: dos ejecuciones en la rama desechable `ci/red-check`, con una petición hacia `dev` que nunca se integra y después se borra: una con un error de formato, que falla en el análisis estático, y otra con un test roto, que falla en los tests.
  - RF-7: test automático que falla si hay cambios de modelos sin migración.
