# Plan 002 — Integración continua mínima
Spec: specs/002-quality-gates/spec.md (aprobada)

## Resumen
Un único flujo de GitHub Actions (`.github/workflows/ci.yml`, no existe `.github/`) con un job.
Ejecuta, con Docker Compose y en `ubuntu-latest`, preparación, análisis estático y tests, y limpia al final.
RF-7 no es un paso del CI: es un test de pytest que ejecuta `makemigrations --check --dry-run` en proceso.
No hay lógica de dominio, ni API, ni modelos, ni migraciones, ni interfaz.
Dependencias nuevas: ninguna, salvo `actions/checkout` (ya aprobada en la spec, constitución punto 1).

## Archivos y responsabilidades
| Archivo | Crea/Modifica | Responsabilidad | RF |
|---|---|---|---|
| backend/config/tests/test_migrations.py | Crea | Test que falla si hay cambios de modelos sin migración | RF-7 |
| .github/workflows/ci.yml | Crea | Disparadores, permisos, concurrencia, job con checkout, 3 pasos de verificación y limpieza | RF-1 a RF-6 |
| specs/002-quality-gates/validation.md | Crea (tras las tareas, ver "Validación posterior") | Evidencia de cada RF con enlaces a ejecuciones | todos |

No se tocan `docker-compose.yml`, `Dockerfile`, `.env.example` ni `AGENTS.md`.
El flujo reutiliza todo tal cual (RNF Coherencia).

## Modelo de datos y migraciones
No aplica. No se crea ni se aplica ninguna migración, ni se ejecuta `migrate`.
En la prueba de mecanismo de T1 se usa un modelo temporal sin commitear y `--dry-run`, que no escribe ficheros.

## Contrato de API
No aplica. No hay endpoints, así que no hay accesos de anónimo, usuario ni propietario que declarar.

## Lógica
Sin funciones de dominio.
El test de RF-7 llama a `call_command("makemigrations", check_changes=True, dry_run=True, interactive=False)` en proceso.
- El kwarg es `check_changes`, que es el `dest` de `--check`, y no `check`.
- El fallo llega como `SystemExit`, no como `CommandError`. El test lo captura y llama a `pytest.fail` con un mensaje en castellano.
- `interactive=False` evita que se cuelgue leyendo stdin.
- Va marcado con `@pytest.mark.django_db`: `django.contrib.sessions` está en `INSTALLED_APPS` y el comando ya consulta la base de datos.
- No se invoca nunca por subproceso con `manage.py`: usaría `DJANGO_ENV=development` y la BD de desarrollo, y se saltaría la guarda de `conftest.py`.

## Interfaz
No aplica. Lo visible es la lista de pasos del job en la pestaña Actions.

## Flujo: forma exacta (descripción, no el fichero completo)

Cabecera:
- `name: CI`.
- `on.push.branches: [dev, "feature/**"]`.
- `on.pull_request.branches: [dev]` y `types: [opened, synchronize, reopened]`.
- Sin `paths` ni `paths-ignore` (RF-1, aunque solo cambie documentación).
- No aparecen `pull_request_target`, `workflow_run`, `secrets.` ni `env:` de flujo o de job.
- `permissions: contents: read` a nivel de flujo.
- `concurrency.group: ${{ github.workflow }}-${{ github.ref }}` y `cancel-in-progress: true`.
- Job `backend-quality`: `runs-on: ubuntu-latest` y `timeout-minutes: 15`.

Esta es la única aparición de `${{ }}` en el fichero, y fuera de cualquier `run:`.
Los pasos no declaran `shell`, así que el shell por defecto aborta en el primer error.

### Orden exacto de los pasos (literal)
| N | `name` | `if` | Contenido literal |
|---|---|---|---|
| 1 | Checkout | (por defecto `success()`) | `uses: actions/checkout@v7` con `with: persist-credentials: false` |
| 2 | Prepare | (por defecto) | `run:` de dos líneas, en este orden: `cp .env.example .env` y después `docker compose build` |
| 3 | Lint | (por defecto) | `run: docker compose run --rm -T --no-deps --entrypoint "" backend sh -c "ruff check . && ruff format --check ."` |
| 4 | Test | (por defecto) | `run: docker compose run --rm -T backend pytest -q` |
| 5 | Clean up | `always()` | `run: if [ -f .env ]; then docker compose down -v; fi` |

Notas del orden:
- El paso 1 es infraestructura. Los tres pasos de verificación de RF-3 son los pasos 2, 3 y 4. El paso 5 es la limpieza de RF-6, y es un paso propio y no parte de Lint ni de Test. Checkout y limpieza son de mantenimiento y no cuentan entre los tres.
- El paso 3 es la orden de AGENTS.md más `-T` (sin TTY en CI) y nada más.
- Si falla el 1, el 2, el 3 o el 4, los siguientes no corren, salvo el 5 por su `if: always()`.
- Una cancelación por concurrencia también ejecuta el 5.

### Comportamiento de la limpieza
`docker compose down -v` interpola `${VAR:?}`, así que sin `.env` falla y ensuciaría el resultado.
Solución: el paso 5 solo llama a `down -v` si `.env` existe.
Esto es correcto porque `.env` se crea antes del `build` dentro del paso 2. Si no existe, nada se construyó ni se arrancó, y no hay nada que limpiar.
- Si falla el checkout, el paso 1 queda en rojo y la limpieza termina en verde sin hacer nada. No hay `docker-compose.yml`.
- Si falla el `cp`, ocurre lo mismo.
- Si `.env` existe y `down -v` falla, la limpieza queda en rojo como paso propio, sin tapar al paso real que falló (RF-4, RF-6).
- Se descartó `|| true`, porque ocultaría fallos reales de RF-6.
- Se descartó `hashFiles('.env')` en el `if`, porque no está comprobado que el patrón funcione con ficheros ocultos.

### Seguridad
- La concurrencia agrupa por `github.ref`, no por `head_ref` ni `ref_name`. Un push (`refs/heads/x`) y una PR (`refs/pull/N/merge`) quedan en grupos distintos, y se aceptan ambas ejecuciones (caso límite de la spec).
- Commits nuevos en la misma rama cancelan la ejecución anterior de ese mismo tipo de evento (RF-5).
- No se exporta `GITHUB_TOKEN` al entorno de Compose.
- No se usa `--verbose`, `set -x`, `docker compose config` ni `env`.
- Como el flujo no declara `env:`, no puede haber `DB_*` ni `DJANGO_*` que el shell imponga sobre `.env`.
- Solo `pull_request` en forks (token de solo lectura y sin secretos).

## Decisiones
| Decisión | Opciones | Elegida | Qué evita | Coste |
|---|---|---|---|---|
| Cómo invocar pytest (RF-3) | A) `docker compose run --rm -T backend pytest -q`. B) `docker compose up -d` y luego `docker compose exec backend pytest -q`. C) `up -d --wait db` y luego `run` | A | Arrancar `runserver` y publicar 8000 sin necesidad. Un paso extra y la gestión del ciclo de vida de `up`. `run` arranca `db` por `depends_on` y pasa por `docker-entrypoint.sh`, que ejecuta `wait_for_db` como red de seguridad (caso límite de la BD lenta). | `run` publica el 5432 de `db` en `127.0.0.1` del runner (posible choque, ver riesgos). Difiere de la orden de AGENTS.md (`exec`) y coincide con la que usó la 001 en T1 y T2. Deja `db`, la red y el volumen vivos, así que `down -v` es obligatorio. |
| Dónde va la limpieza (RF-6) | Dentro de Test; paso propio con `if: always()`; `post:` de acción | Paso propio con `if: always()` | Que un fallo de limpieza se confunda con el de Lint o Test (RF-4). | Un paso más en la lista; checkout y limpieza son de mantenimiento y no cuentan entre los tres pasos de verificación. |
| Limpieza sin `.env` | `\|\| true`; `hashFiles('.env')`; `if [ -f .env ]` en el `run`; `cp -n` dentro de la limpieza | `if [ -f .env ]` | Enmascarar fallos reales. Efectos secundarios en la limpieza. Depender de una función de expresión no verificada. | Si falta `.env` la limpieza no hace nada; es correcto porque nada se creó. |
| Concurrencia (RF-5) | Grupo por `head_ref`; por `ref_name`; `workflow-ref` | `${{ github.workflow }}-${{ github.ref }}` con `cancel-in-progress: true` | Cancelar el push y la PR de la misma rama entre sí (caso límite de la spec). | Un push a `dev` seguido de otro cancela la validación del intermedio. Se elige cancelar siempre porque RF-5 lo dice sin excepciones. |
| `@pytest.mark.django_db` en RF-7 | Marcarlo ya; marcarlo cuando exista el primer modelo propio | Marcarlo ya | `RuntimeError` por acceso a BD bloqueado. `sessions` ya provoca acceso a BD, así que no es opcional. Permite que la prueba de mecanismo falle por la razón esperada. | Usa la BD de test. La suite ya la crea para otros tests, así que el coste adicional es mínimo. |
| Ubicación del test RF-7 | Añadir a `test_tooling.py`; fichero nuevo en `config/tests/`; en `apps/core/tests/` | `backend/config/tests/test_migrations.py` | Mezclar un test de migraciones con los de herramientas. Atarlo a una app, cuando comprueba todo el proyecto. | Un fichero más. |
| Comprobación local del flujo | Añadir `actionlint` u otra herramienta; test de pytest que lea el YAML; ensayo en copia limpia; solo `grep` | Solo `grep`; la primera ejecución real en GitHub sustituye al ensayo | Dependencias nuevas (constitución punto 1). El backend no monta `.github/` ni tiene PyYAML. Levantar contenedores y una BD solo para un ensayo. | La sintaxis del YAML y las órdenes de los pasos 2 a 5 solo se confirman de verdad en la primera ejecución real. |
| `timeout-minutes` | Sin límite (360 min por defecto); 15 min | 15 min (no está en la spec) | Un job colgado que gaste minutos sin aviso. | Un falso fallo si la construcción en frío tarda más de 15 min. Duración típica no medida. |
| Versión de `actions/checkout` | Etiqueta mayor `v7`; SHA fijado | `v7` (lo exige la spec: versión mayor) | Fijar una versión desfasada por un SHA copiado a mano. | Riesgo residual de que una etiqueta mayor se mueva; anotado para la validación. |

## Blast radius
- Código existente tocado: ninguno.
- Se crean un test y el flujo.
- Ningún test existente puede romperse.
- A partir de T1, cualquier cambio de modelos sin migración falla `pytest -q`. Es el efecto buscado.
- Huecos conscientes: las PR hacia `main` y los push a `main` no pasan por esta puerta. Tampoco las ramas que no sean `dev` ni `feature/**`, salvo mediante PR hacia `dev`.

## Riesgos
| Riesgo | Mitigación |
|---|---|
| Choque del 5432 de `db` con un Postgres preinstalado en `ubuntu-latest` | Se verá en la primera ejecución. Si choca, queda como fallo claro en el paso Test; resolverlo exigiría cambiar `docker-compose.yml` y se trataría como cambio de spec. |
| Límites de pull anónimo de Docker Hub sobre `postgis/postgis:18-3.6` | Es un fallo de disponibilidad: se reintenta la ejecución. No se resuelve con credenciales, porque la spec prohíbe los secretos. |
| `run` podría no esperar a `service_healthy` | La red de seguridad es `wait_for_db` del entrypoint. Se confirma en la primera ejecución real. |
| Permisos del bind mount: `./backend` es del UID 1001 del runner y el contenedor corre como 10001 | Compatible con `RUFF_NO_CACHE`, `-p no:cacheprovider` y `PYTHONDONTWRITEBYTECODE`. Se confirma en la primera ejecución real. |
| Forks | Solo `pull_request`. En `validation.md` se anota el ajuste manual de aprobación de workflows de forks y el riesgo residual de la etiqueta mayor. |
| Un evento duplicado (push y PR) consume el doble de minutos | Aceptado por la spec. |
| Cancelación y limpieza: no se ha comprobado cuánto tiempo da GitHub a los pasos `always()` tras cancelar | Si se queda un volumen, el runner es efímero y se destruye igualmente. |
| Sin ensayo local, el primer fallo de sintaxis o de órdenes aparece en GitHub | Se corrige en la rama de la feature antes de abrir la PR de validación; coste: un par de commits de ajuste. |

## Estrategia de tests
| RF | Cómo se verifica |
|---|---|
| RF-1 | `grep` local: el YAML tiene `push.branches: [dev, "feature/**"]`, `pull_request` con `branches: [dev]` y los tres `types`, y no tiene `paths`. Ejecuciones reales: push a `feature/**`, PR abierta hacia `dev`, un nuevo commit (`synchronize`) y una reapertura. Una de las ejecuciones con un cambio solo de documentación. |
| RF-2 | `runs-on: ubuntu-latest`. El log muestra `docker compose build` con el `Dockerfile` de `./backend` y la imagen `postgis/postgis:18-3.6`. El YAML no repite ninguna versión. |
| RF-3 | Pasos 2, 3 y 4 visibles y en orden en la ejecución verde. La ejecución `ci/red-check` con error de formato demuestra que Test no corre. |
| RF-4 | Dos ejecuciones en `ci/red-check`: una con error de formato (falla Lint) y otra con un test roto (falla Test). Cada una muestra el paso en rojo. |
| RF-5 | Dos pushes seguidos a la misma rama: la primera ejecución queda "cancelada". Un push y una PR de la misma rama no se cancelan entre sí. |
| RF-6 | En cada ejecución (verdes, rojas y la cancelada) el paso "Clean up" se ejecuta; el log muestra contenedores, red y volumen eliminados. |
| RF-7 | Test automático `test_migrations.py` en pytest. Prueba de mecanismo en T1: con un modelo temporal sin migración falla con el mensaje esperado, y sin él pasa. Esa prueba se ejecuta en local y no se incluye en el repositorio. |
| RNF seguridad | `grep` local, sobre `.github/workflows/ci.yml`, de que no aparecen `pull_request_target`, `workflow_run`, `secrets.`, `set -x`, `docker compose config`, `env`, `--verbose`, ni `${{` dentro de un `run:`. Hay `permissions: contents: read` y `persist-credentials: false`. |
| RNF Lint sin BD | El log del paso Lint no muestra arranque de `db`. |

Los RF-1 a RF-6 no tienen test de pytest y su evidencia son ejecuciones reales. La constitución (punto 2) lo permite solo si la spec lo prevé, y los criterios de finalización de la 002 lo prevén.

## Validación posterior (no es una tarea)
La evidencia de RF-1 a RF-6 exige subir ramas a GitHub, y eso solo se hace con orden explícita del usuario (AGENTS.md, nunca push sin orden). Una vez cerradas T1 y T2, y con orden del usuario:
1. Push de `feature/002-quality-gates` y PR hacia `dev`. Se registra el enlace de la ejecución verde.
2. Un segundo push inmediato para observar RF-5.
3. Rama `ci/red-check`, creada desde la rama de la feature (porque `dev` aún no tiene `ci.yml`; la PR incluirá el diff completo de la feature). La rama no activa `push`, así que solo se ejecuta por la PR. Dos commits, uno por fallo, empujando el segundo cuando termine la primera ejecución, o la concurrencia la cancelaría. La PR nunca se integra; después se cierra y se borra la rama.
4. Escribir `validation.md` con los enlaces y los ajustes manuales (aprobación de workflows de forks, protección de ramas fuera de alcance).
Cada push y cada borrado de rama requiere confirmación.

## Afirmaciones no verificadas
- `actions/checkout`: la etiqueta mayor `v7` existe (`git ls-remote` encontró v7, v7.0.0 y v7.0.1), pero falta comprobar sus requisitos de runner y que `ubuntu-latest` los cumple. La API de `gh` falló por credenciales.
- `ubuntu-latest` trae Docker Compose v2 con soporte de `--no-deps`, `-T` y `${VAR:?}`. No comprobado.
- `docker compose run` espera a `service_healthy` de `db`. La documentación no lo afirma de forma explícita; la red de seguridad es el entrypoint. No probado.
- `-T` es compatible con `--entrypoint ""` y con `--no-deps` en la misma orden.
- Las órdenes de los pasos 2 a 5 no se ensayan en local: la primera ejecución real las confirma.
- El 5432 está libre en el runner.
- `postgis/postgis:18-3.6` se descarga sin credenciales y sin topar con límites.
- El bind mount del UID 1001 es legible por el UID 10001 y no escribible, sin romper la suite.
- `makemigrations --check` toca la BD hoy por culpa de `django.contrib.sessions`. Deducido de la configuración; T1 lo confirma.
- Los pasos `always()` corren tras una cancelación (documentado), pero no se sabe de cuánto tiempo disponen.
- 15 minutos son suficientes para una construcción en frío.
- El shell por defecto de los pasos aborta ante el primer error (por la documentación de Actions, no probado).

## Skills que aplican
- sdd.
- django-drf, para el test de migraciones y la prueba de mecanismo (migraciones: preguntar antes de crear o aplicar; aquí no se crea ninguna).
