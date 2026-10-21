# Tareas 002 — Integración continua mínima
Antes de cada commit: `docker compose exec backend pytest -q` y `docker compose exec backend sh -c "ruff check . && ruff format --check ."` en verde. Test primero, fallando por la razón esperada. Sin `migrate` ni pushes sin orden explícita.

- [x] **T1. El test de migraciones pendientes.** RF-7
  - Qué (ficheros): crea `backend/config/tests/test_migrations.py`. No toca nada más.
  - Por qué: la constitución (punto 4) exige que el test falle antes de pasar. Se hace en proceso con `call_command` y no por subproceso con `manage.py`, que usaría `DJANGO_ENV=development` y la BD de desarrollo, saltándose la guarda de `conftest.py`. Se marca `django_db` ya, porque `sessions` ya provoca acceso a BD. Alternativa descartada: marcarlo después y arriesgar un `RuntimeError`.
  - RF que cubre: RF-7.
  - Cómo se prueba:
    1. Escribe el test: captura `SystemExit` y llama a `pytest.fail` con un mensaje en castellano.
    2. Para ver que falla por la razón esperada, crea un `backend/apps/core/models.py` temporal y sin commitear con un modelo mínimo, sin migración. Ejecuta `docker compose exec backend pytest -q config/tests/test_migrations.py`. Debe fallar con el mensaje propio, y no con `RuntimeError`, `TypeError` ni `CommandError`.
    3. Borra el fichero temporal con `rm` (nunca con git), comprueba con `git status` que solo queda el test nuevo y que pasa en vacío.
    4. Sin `makemigrations` real ni `migrate`.
  - Qué toca revisar: que el kwarg es `check_changes`, que se captura `SystemExit`, que lleva `django_db` y que el mensaje de fallo no filtra datos. Se explica línea a línea antes de que lo aceptes (regla local).
  - Commit: `test(core): fail the suite on missing migrations`
  - Hecho cuando: el modelo temporal hace fallar el test con el mensaje propio; sin él, el test pasa; `pytest -q` completo y `ruff check . && ruff format --check .` en verde; el modelo temporal ya no está en el árbol de trabajo y `git status` solo muestra el test nuevo.

- [x] **T2. El flujo de CI con tres pasos de verificación y limpieza.** RF-1, RF-2, RF-3, RF-4, RF-5, RF-6
  - Qué (ficheros): crea `.github/workflows/ci.yml`, con el orden de pasos literal del plan (Checkout, Prepare, Lint, Test, Clean up) y la cabecera descrita.
  - Por qué: es el único artefacto que exige la spec. Se elige `run` y no `up -d` + `exec`, por las razones del plan. La limpieza es un paso propio con `if: always()` y `if [ -f .env ]`, para que ni la limpieza oculte el fallo real ni falle por falta de `.env`. Alternativas descartadas: `|| true`, `hashFiles`, un test que lea el YAML (el backend no monta `.github/` y PyYAML sería una dependencia nueva), `actionlint` (dependencia nueva), ensayo local en copia limpia (lo sustituye la primera ejecución real en GitHub).
  - RF que cubre: RF-1 a RF-6, más los RNF de seguridad y coherencia. RF-7 ya está en T1.
  - Cómo se prueba (sin push ni contenedores): `grep -nE` sobre el fichero: no aparecen `pull_request_target`, `workflow_run`, `secrets\.`, `set -x`, `docker compose config`, `--verbose`, `paths`, ni `env:`. Solo hay una expresión `${{ }}`, la de `concurrency`, y no dentro de `run:`. La sintaxis real del YAML y las ejecuciones se confirman en la validación posterior.
  - Qué toca revisar: el orden de los pasos y sus nombres en inglés; que `permissions`, `persist-credentials: false` y el grupo de concurrencia son los del plan; `timeout-minutes: 15`; y que no se ha añadido nada que no esté en la spec.
  - Commit: `ci: add backend lint and test workflow`
  - Hecho cuando: el fichero cumple todos los `grep`; `pytest -q` y el lint del repositorio siguen en verde. La evidencia de ejecuciones reales queda pendiente de `validation.md` y de tus órdenes de push.
