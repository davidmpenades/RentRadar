# Validación — 002-quality-gates
Fecha: 2026-10-21 · Rama: `feature/002-quality-gates` · Flujo: `.github/workflows/ci.yml` · Runner: `ubuntu-latest`

Evidencia de los RF de CI, que no cubre un test automático de pytest. Los enlaces son las ejecuciones reales en GitHub Actions.

## Ejecuciones

| Id | Evento | Rama / PR | Commit | Resultado | Enlace |
|---|---|---|---|---|---|
| A | push | `feature/002-quality-gates` | 55c97ff | verde (1 min) | https://github.com/davidmpenades/RentRadar/actions/runs/39574929381 |
| B | pull_request | PR #3 hacia `dev` | 55c97ff | verde (57 s) | https://github.com/davidmpenades/RentRadar/actions/runs/39576088230 |
| C | pull_request | PR #4 (borrador) `ci/red-check` | 4692e62 | rojo en Lint | https://github.com/davidmpenades/RentRadar/actions/runs/39576614300 |
| D | pull_request | PR #4 (borrador) `ci/red-check` | caa089f | rojo en Test | https://github.com/davidmpenades/RentRadar/actions/runs/39576871595 |

La PR #4 se cerró sin integrar y la rama `ci/red-check` se borró, local y remota. En C, la rama tenía un fichero con `x=1` (error de formato); en D, ese fichero se sustituyó por un test con `assert 1 + 1 == 3`. Con `assert False`, `ruff check` habría fallado en Lint en lugar de Test.

## Validación por RF

| RF | Comprobación | Resultado |
|---|---|---|
| RF-1 | A se lanzó por el push a `feature/**` y B por la PR abierta hacia `dev`. C y D, por commits nuevos en la PR #4 (`opened` y `synchronize`). Sin `ci/**` en los disparadores, la rama `ci/red-check` solo ejecutó `pull_request`. | Cumple. `reopened` no se ejercitó; está declarado en el flujo. |
| RF-2 | Todos los runs en `ubuntu-latest`; el paso Prepare construye con `docker compose build` y el job usa `postgis/postgis:18-3.6` desde `docker-compose.yml`. En A, el paso Test muestra `Container rentradar-db-1 Started` sin `Healthy`: la espera la hizo `wait_for_db` del entrypoint, la red de seguridad prevista en el plan, y no `service_healthy`. | Cumple. Queda anotado que `docker compose run` no esperó al healthcheck. |
| RF-3 | En A y B aparecen en verde Prepare, Lint y Test, en ese orden. En C, tras fallar Lint, el paso Test quedó `skipped`. | Cumple. |
| RF-4 | C: falla Lint (`1 file would be reformatted, 42 files already formatted`, `config/tests/test_format_break.py`). D: falla Test (`assert 1 + 1 == 3`, `1 failed, 162 passed`) con Lint en verde. | Cumple. |
| RF-5 | `concurrency` con `group: ${{ github.workflow }}-${{ github.ref }}` y `cancel-in-progress: true` presentes en el flujo (verificado con `grep`). | Cumple por configuración. No se provocó una cancelación real con dos pushes seguidos. |
| RF-6 | El paso Clean up se ejecutó en A, B, C y D. En A, B y D el log muestra `Container … Removed`, `Network … Removed` y `Volume rentradar_db-data Removed`. En C, donde Test no arrancó `db`, muestra solo red y volumen eliminados. | Cumple. |
| RF-7 | `backend/config/tests/test_migrations.py`. Prueba de mecanismo en local con un `models.py` temporal sin migración: el test falló con su mensaje (no con `RuntimeError`, `TypeError` ni `CommandError`); sin el modelo pasó. Después se borró con `rm`. | Cumple. La suite completa (162 tests) pasa en local, en A y en B; en D pasan esos 162 y falla solo el test roto a propósito. |
| Seguridad | `grep` sobre el flujo: sin `pull_request_target`, `workflow_run`, `secrets.`, `set -x`, `docker compose config`, `--verbose`, `paths`, `env:`, `GITHUB_TOKEN` ni `shell:`; una sola expresión `${{ }}`, en `concurrency`. `permissions: contents: read`, `persist-credentials: false`, `actions/checkout@v7`. | Cumple. |

## Notas y ajustes manuales
- La anotación de GitHub en B avisa de que `ubuntu-latest` migrará a Ubuntu 26 a partir del 19 de octubre de 2026 (https://github.com/actions/runner-images/issues/14748). Riesgo aceptado; el job pasó en A y B.
- `actions/checkout@v7` funcionó en las cuatro ejecuciones; no se comprobaron sus requisitos de runner más allá de eso.
- No hubo choque del puerto 5432 en el runner ni límites de pull de Docker Hub.
- Pendiente, y lo hace el propietario fuera del código: protección de la rama `dev` en GitHub cuando el CI esté en verde, y el ajuste de aprobación de workflows de forks.
- Hueco conocido: las PR y los push hacia `main` no pasan por esta puerta.
