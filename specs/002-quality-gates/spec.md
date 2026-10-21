# Spec 002 — Integración continua mínima
Estado: borrador
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

## Requisitos funcionales
- RF-1: CUANDO se sube un cambio a `dev` o a una rama `feature/**`, o se abre o actualiza una petición de integración hacia `dev`, EL SISTEMA ejecuta la integración continua.
- RF-2: EL SISTEMA ejecuta la integración continua en un entorno limpio con Docker Compose, con la misma imagen del backend y la misma base de datos geoespacial (`postgis/postgis:18-3.6`) que el entorno local.
- RF-3: ANTES de ejecutar los pasos, EL SISTEMA crea el fichero de variables a partir de la plantilla del repositorio (`cp .env.example .env`); no usa secretos de GitHub.
- RF-4: EL SISTEMA ejecuta como paso visible y separado el análisis estático (`ruff check` y `ruff format --check`).
- RF-5: EL SISTEMA ejecuta como paso visible y separado la suite de tests (`pytest -q`) contra la base de datos geoespacial.
- RF-6: SI falla algún paso, ENTONCES EL SISTEMA marca la ejecución como fallida y muestra qué paso ha fallado.
- RF-7: EL SISTEMA falla la suite de tests si hay cambios de modelos sin migración (`makemigrations --check --dry-run`). Se implementa como test de pytest, no como paso del CI.

## Requisitos no funcionales
- **Seguridad**: el flujo declara `permissions: contents: read`. La única acción de terceros es `actions/checkout`, aprobada como dependencia (constitución, punto 1). No se usan secretos de GitHub.
- **Lint sin base de datos**: el paso de lint no necesita la base de datos: usa la orden de AGENTS.md con `--entrypoint ""` y `--no-deps` (RF-35 de la 001).
- **Coherencia**: el flujo no duplica versiones ni órdenes: reutiliza `docker-compose.yml` y las órdenes de AGENTS.md.
- **Permisos de la API**: la spec no expone endpoints, así que no hay accesos de anónimo, usuario ni propietario que declarar.
- **Idioma**: nombres de pasos y configuración en inglés; documentación en castellano (constitución, punto 8).

## Casos límite
- La base de datos tarda en estar lista: los tests esperan a que esté disponible en lugar de fallar por arrancar antes (coherente con el RF-3 de la spec 001).
- Un cambio llega a la vez por una subida de rama y por una petición de integración: las dos ejecuciones son válidas y cada una informa por separado.
- Falla el análisis estático: el paso de tests no oculta ni sustituye ese fallo, y el resultado indica el paso que falló (RF-6).
- Los tests se ejecutan dentro del contenedor: el test de `geteuid == 10001` exige este modo (RF-2).

## Fuera de alcance
- Pasan a una spec posterior: pre-commit, detección de secretos y escaneo del historial.
- Protección de ramas: es un ajuste manual en GitHub que hace el propietario cuando la integración continua esté en verde.
- Despliegue continuo y publicación de imágenes.
- Puertas de calidad del frontend (irán con la spec del frontend).
- Comprobación de tipos estática, cobertura mínima de tests y análisis de vulnerabilidades de dependencias.
- Requisitos de despliegue (HTTPS, HSTS, proxy, `check --deploy`): van en la spec de despliegue.

## Criterios de finalización
- Cada RF tiene una comprobación registrada en la validación:
  - RF-1, RF-2, RF-3, RF-4 y RF-5: una ejecución real sobre una petición de integración hacia `dev` sale en verde con los dos pasos visibles, y el flujo no referencia ningún secreto de GitHub.
  - RF-6: otra ejecución con un test roto a propósito sale en rojo y señala el paso de tests.
- El plan cabe en 10 tareas como máximo.

## Dudas abiertas
- Ninguna.
