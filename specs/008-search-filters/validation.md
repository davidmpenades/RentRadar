# Validación 008 — Búsqueda y filtros por categoría en el mapa
Spec: specs/008-search-filters/spec.md · Plan: specs/008-search-filters/plan.md · Tareas: specs/008-search-filters/tasks.md
Rama: `feature/008-search-filters`, sobre `dev` (`fe43754`).

## Rendimiento: antes (T1)
Medición de la consulta de la lista pública antes de añadir los filtros. El código de la medición está en `6cd3b3e` (`test(assets): measure public list query plan`): `backend/apps/assets/tests/test_list_query_plan.py@6cd3b3e`.

### Condiciones
- Fecha: 24-11-2026.
- Portátil enchufado a la corriente, stack levantado (backend y db) y nada más en marcha.
- Orden: `docker compose exec backend pytest -q -s --run-measurement apps/assets/tests/test_list_query_plan.py`, dos veces sobre la BD de test: la primera falló en el sondeo (`SHOW lc_ctype`, ver «Desviación del plan») con la medición ya completada; la segunda, tras corregir el sondeo, dio `2 passed in 30.57s`.
- La tabla es la de la segunda ejecución. Las dos coinciden en el nodo de acceso, las filas descartadas, los bucles y los buffers de las 16 filas, y las medianas difieren como máximo un 2,25 % («zzzz», Z2); solo tres filas pasan del 1 % («zzzz» en Z1 y Z2 y «bici» en Z1).
- En T6 se repiten las mismas condiciones.

### Sondeo del entorno (literal)
```
SHOW server_version: 18.6 (Debian 18.6-1.pgdg13+2)
SELECT datctype FROM pg_database WHERE datname = current_database(): en_US.utf8
SHOW server_encoding: UTF8
translate(text, text, text): provolatile = i
```

### Volumen y zonas
- 50 000 bienes y 500 propietarios (5 con la cuenta desactivada), con la semilla 8.
- 80 % de los bienes activos y 20 % pausados. El 40 % cae en un cuadrado de 1°×1° alrededor de Valencia (latitud 39–40, longitud −1–0) y el resto se reparte por la caja de coherencia.
- Las 12 categorías sembradas, con «kayak» en torno al 8 % y «ski» en torno al 2 %.
- Los bienes se crean sin pasar por el servicio de escritura, dentro de la transacción del test, que se revierte al terminar. Después se ejecuta `ANALYZE assets_asset`.
- Z1 = latitud 39.3 a 39.7, longitud -0.6 a -0.2.
- Z2 = latitud 38.5 a 40.5, longitud -2 a 1.
- Por consulta: 1 calentamiento y 5 medidas. «Mediana ms» es la mediana de «Execution Time». El nodo de acceso, las filas descartadas («Rows Removed by Filter»), los bucles y los buffers (shared hit + read del plan completo) son de la ejecución mediana.
- «Sin filtro» usa el selector real. Las demás consultas son réplicas del mismo encadenado con `category__slug` y `title__icontains`, porque la columna plegada y los filtros del selector aún no existen.

### Tabla (literal, segunda ejecución)
```
Consulta                        Zona  Mediana ms  Mín ms  Máx ms  Nodo de acceso    Filas descartadas  Bucles  Buffers
------------------------------  ----  ----------  ------  ------  ----------------  -----------------  ------  -------
sin filtro                      Z1    99.42       99.25   99.71   Seq Scan          23664              2       15200
sin filtro                      Z2    594.82      593.11  597.00  Seq Scan          16718              2       86006
categoría kayak                 Z1    10.73       10.72   10.85   Bitmap Heap Scan  3821               1       2421
categoría kayak                 Z2    49.39       49.35   49.56   Bitmap Heap Scan  2718               1       6952
categoría ski                   Z1    2.90        2.90    2.94    Bitmap Heap Scan  933                1       975
categoría ski                   Z2    12.86       12.83   12.91   Bitmap Heap Scan  654                1       2118
texto «bici»                    Z1    27.45       27.24   27.61   Seq Scan          24875              2       2960
texto «bici»                    Z2    67.28       67.14   67.86   Seq Scan          24172              2       10165
texto de 1 carácter «a»         Z1    94.41       94.27   94.78   Seq Scan          23771              2       14139
texto de 1 carácter «a»         Z2    550.97      548.48  552.61  Seq Scan          17360              2       79472
texto de 2 caracteres «es»      Z1    38.35       38.09   38.41   Seq Scan          24609              2       5545
texto de 2 caracteres «es»      Z2    172.62      171.85  172.73  Seq Scan          22631              2       25701
texto sin coincidencias «zzzz»  Z1    22.71       22.54   23.05   Seq Scan          25000              2       1619
texto sin coincidencias «zzzz»  Z2    22.74       22.57   22.79   Seq Scan          25000              2       1619
categoría kayak y texto «bici»  Z1    4.20        4.17    4.25    Bitmap Heap Scan  4029               1       1594
categoría kayak y texto «bici»  Z2    8.56        8.54    9.14    Bitmap Heap Scan  3909               1       2098
```
Con 2 bucles (ejecución en paralelo), «Filas descartadas» es la media por bucle; el total es filas × bucles. Lo confirma «zzzz»: 25 000 × 2 = 50 000. El criterio del índice de T6 se evalúa sobre el total.

### Desviación del plan
El sondeo usa `pg_database.datctype` en lugar de `SHOW lc_ctype`: PostgreSQL 16 eliminó los parámetros de solo lectura `lc_collate` y `lc_ctype` (notas de la versión 16). Comprobado en la 18.6 de la BD de test.

## T1 — comprobaciones
- Commit de código: `6cd3b3e` `test(assets): measure public list query plan` (`backend/conftest.py` y `backend/apps/assets/tests/test_list_query_plan.py`).
- Fichero de medición: `backend/apps/assets/tests/test_list_query_plan.py@6cd3b3e`.
- Colección de toda la suite (`pytest --collect-only -q`): de 2607 a 2609 tests. Diff literal, antes contra después:
```
114a115,116
> apps/assets/tests/test_list_query_plan.py::test_probe_the_test_database_environment
> apps/assets/tests/test_list_query_plan.py::test_measure_the_list_query_plans
2609c2611
< 2607 tests collected in 2.80s
---
> 2609 tests collected in 1.72s
```
- Tanda previa al commit, con la línea de resumen literal de cada orden (repetida tras corregir el sondeo):
  - `docker compose exec backend pytest -q`: `2607 passed, 2 skipped in 43.02s` (los dos saltados son los de medición).
  - `docker compose exec backend sh -c "ruff check . && ruff format --check ."`: `All checks passed!` y `153 files already formatted`.
  - `docker compose exec backend pytest -q config/tests/test_migrations.py`: `1 passed in 0.88s`.
  - Desfase de `openapi.json` (`spectacular --validate --fail-on-warn` y `diff /tmp/openapi.json openapi.json`): sin diferencias, código de salida 0.
  - `docker compose run --rm --no-deps -e DB_HOST=db-inexistente.invalid --entrypoint "" backend python manage.py check`: `System check identified no issues (0 silenced).`
  - `npx vitest run`: `Test Files  36 passed (36)` y `Tests  1324 passed (1324)`.
  - `npm run build`: `✓ built in 648ms`.
  - `npm run api:check`: `✨ openapi-typescript 7.13.0`, código de salida 0.

## T2 — comprobaciones
- Commit de código: `bbe28ba40bd99129de1fe6222e3c53b66dd6b4a9` `feat(assets): add folded title column`. Seis ficheros: `backend/apps/assets/folding.py`, `backend/apps/assets/models.py`, `backend/apps/assets/migrations/0005_asset_title_folded.py`, `backend/apps/assets/tests/test_folding.py`, `backend/apps/assets/tests/test_models.py` y `backend/apps/assets/tests/test_update.py`. El diff completo (`git diff HEAD~1 HEAD`) tiene el sha256 `fea6fe048877791bb370711a6c37dfc5394624b81c40eac51a97f87efeb572ae`, el mismo que el diff revisado antes del commit.
- Prueba en rojo, antes de generar la migración: `test_folding.py` fallaba con `column assets_asset.title_folded does not exist` (2 de los 3 tests; el tercero comprueba solo la tabla).
- Colección de `apps/assets/tests` y `config/tests` (`pytest --collect-only -q`): de 1314 a 1317 tests. Diff literal, antes contra después:
```
102a103,104
> apps/assets/tests/test_folding.py::test_python_and_the_database_fold_every_character_of_the_table_the_same_way
> apps/assets/tests/test_folding.py::test_characters_outside_the_table_stay_the_same_in_python_and_in_the_database
495a498
> apps/assets/tests/test_folding.py::test_the_fold_source_and_target_have_the_same_length_and_no_repeats
1316c1319
< 1314 tests collected in 0.89s
---
> 1317 tests collected in 0.89s
```
  Son exactamente los tres ids previstos; no hay ninguno eliminado ni renombrado.
- Generación de la migración (`makemigrations assets` con `DB_HOST=db-inexistente.invalid`): `Migrations for 'assets':`, `apps/assets/migrations/0005_asset_title_folded.py` y `+ Add field title_folded to asset`. Django la escribe con comillas simples: `ruff format` reformateó tres ficheros (`0005`, `test_folding.py` y `folding.py`) y dejó dos sin cambios.
- `pytest -q --create-db apps/assets config/tests/test_migrations.py`: `1120 passed, 2 skipped in 16.05s`.
- SQL de `sqlmigrate assets 0005` (BD de test), literal:
```
BEGIN;
--
-- Add field title_folded to asset
--
ALTER TABLE "assets_asset" ADD COLUMN "title_folded" text GENERATED ALWAYS AS (translate("title", 'ABCDEFGHIJKLMNOPQRSTUVWXYZÀÁÂÃÄÅàáâãäåÇçÈÉÊËèéêëÌÍÎÏìíîïÒÓÔÕÖòóôõöÙÚÛÜùúûüÝŸýÿÑÆŒØ', 'abcdefghijklmnopqrstuvwxyzaaaaaaaaaaaacceeeeeeeeiiiiiiiioooooooooouuuuuuuuyyyyñæœø')) STORED;
COMMIT;
```
  Los parámetros de `translate` se incrustan bien como literales (supuesto del plan comprobado). No hay `NOT NULL` (ver la desviación 2).
- Tanda previa al commit, con la línea de resumen literal de cada orden:
  - `docker compose exec backend pytest -q`: `2610 passed, 2 skipped in 43.75s` (los dos saltados son los de medición).
  - `docker compose exec backend sh -c "ruff check . && ruff format --check ."`: `All checks passed!` y `156 files already formatted`.
  - `docker compose exec backend pytest -q config/tests/test_migrations.py`: `1 passed in 1.63s`.
  - Desfase de `openapi.json` (`spectacular --validate --fail-on-warn` y `diff /tmp/openapi.json openapi.json`): sin diferencias, código de salida 0.
  - `docker compose run --rm --no-deps -e DB_HOST=db-inexistente.invalid --entrypoint "" backend python manage.py check`: `System check identified no issues (0 silenced).`
  - La última edición cambió el comentario de un test (`test_models.py`), así que la tanda se repitió entera. `pytest -q` y ruff, arriba, ya se ejecutaron después de ella. Las demás se ejecutaron después del commit sobre el mismo código de `bbe28ba` (sin cambios en `backend/` ni en `frontend/` respecto a `HEAD`):
    - `docker compose exec backend pytest -q config/tests/test_migrations.py`: `1 passed in 0.89s`.
    - Desfase de `openapi.json` (`spectacular --validate --fail-on-warn` y `diff /tmp/openapi.json openapi.json`): sin diferencias, código de salida 0.
    - `manage.py check`: `System check identified no issues (0 silenced).`
    - `npx vitest run`: `Test Files  36 passed (36)` y `Tests  1324 passed (1324)`.
    - `npm run build`: `✓ built in 674ms`.
    - `npm run api:check`: `✨ openapi-typescript 7.13.0`, código de salida 0.
    - eslint no aplica: esta tarea no toca `frontend/`.

### M4 — Tabla de Python y tabla de la BD desincronizadas
- Definición (cambia respecto a `tasks.md` anterior): quitar una pareja de `FOLD_SOURCE` y de `FOLD_TARGET` en `folding.py` sin generar migración, de modo que Python cambia y la BD no. La definición anterior (quitar la pareja solo en Python o solo en la expresión del modelo) no podía poner B5 en rojo en la segunda forma: los tests crean la BD aplicando la migración, que congela la tabla como literales; cambiar la expresión del modelo no cambia la columna, solo deja una migración pendiente.
- Mutación: pareja Ç → c. `"Çç"` pasa a `"ç"` en `FOLD_SOURCE` y `"cc"` a `"c"` en `FOLD_TARGET`.
- Procedimiento: script de Python ejecutado con `python3 -I -B`, copia previa del fichero fuera del repo, sin `sed -i`, sha256 antes y después y restauración en `finally`. Stack en marcha (backend y db, `healthy`) y portátil enchufado.
- Antes de ejecutar, `ruff check` y `ruff format --check` por stdin sobre el fichero mutado: código 0 y sin diferencias, así que `test_ruff_accepts_the_backend_code` no se ve afectado.
- Predicción, sellada con sha256 antes de ejecutar y nunca modificada:
  - fallan exactamente `apps/assets/tests/test_folding.py::test_python_and_the_database_fold_every_character_of_the_table_the_same_way` (Python deja la Ç y la BD la pliega a c) y `config/tests/test_migrations.py::test_models_have_no_pending_migrations` (la expresión de `title_folded` cambia y `makemigrations` detecta una migración pendiente);
  - línea de resumen: `2 failed, 2608 passed, 2 skipped`;
  - ninguna línea `ERROR`.
- Orden: `docker compose exec -T backend pytest -q -rfE` (suite completa).
- Resultado, línea de resumen literal: `2 failed, 2608 passed, 2 skipped in 43.09s`.
  - Ids fallidos (orden `LC_ALL=C`), idénticos a los predichos:
```
apps/assets/tests/test_folding.py::test_python_and_the_database_fold_every_character_of_the_table_the_same_way
config/tests/test_migrations.py::test_models_have_no_pending_migrations
```
  - Mensajes: `{'Ç': 'Ç'} != {'Ç': 'c'}` y `Hay cambios de modelos sin migración: ejecuta makemigrations.`
  - ERROR: 0 líneas `^ERROR ` y ninguna aparición de «error» en la línea de resumen.
- Restauración: sha256 de `folding.py` antes `dd1ae1517b6236dd629659686c2d214b6b55364caf8e7ee9eeb340c541d5ec57`, con la mutación `99d3cbc45298b1b5dac5c1a2c4e23e6146f38831765413739d02edfaea00fda5` y restaurado `dd1ae1517b6236dd629659686c2d214b6b55364caf8e7ee9eeb340c541d5ec57`. Coincide con `git show bbe28ba:backend/apps/assets/folding.py | sha256sum`, y `git status --short` salió vacío.
- Veredicto: B5 detecta una tabla de Python desincronizada de la de la BD (con la forma de B5 de la desviación 3) y `test_models_have_no_pending_migrations` detecta la misma desincronización por el lado del modelo.

### Desviaciones del plan en T2
1. Un test existente de edición compara la fila completa y tuvo que incluir la columna plegada; no estaba previsto en el plan. El id no cambia y solo cambia la aserción: `backend/apps/assets/tests/test_update.py@bbe28ba:218-223` (`"title_folded": "martillo"`), que de paso comprueba que la BD recalcula la columna al editar el título.
2. La columna generada es nullable en la BD: Django no emite `NOT NULL` en una columna generada (ver el SQL de arriba), aunque nunca será nula porque `title` no lo es. El plan suponía `NOT NULL`. La regla «ninguna columna es nullable» excluye `title_folded` y afirma que es `YES`: `backend/apps/assets/tests/test_models.py@bbe28ba:321-324`; `EXPECTED_FIELDS` y `EXPECTED_COLUMNS` en `backend/apps/assets/tests/test_models.py@bbe28ba:74` y `backend/apps/assets/tests/test_models.py@bbe28ba:93`.
3. B5 no itera sobre `FOLD_SOURCE`, como decía el plan: así una pareja quitada solo en Python no se probaría. El test recorre los puntos de código U+0020 a U+024F (latín básico, Latin-1 y ampliados A y B) y afirma que `FOLD_SOURCE` está contenido en ese rango: `backend/apps/assets/tests/test_folding.py@bbe28ba:9` y `backend/apps/assets/tests/test_folding.py@bbe28ba:30-38`. Si la tabla se amplía fuera de ese rango, el propio test falla y obliga a ampliarlo.
4. `ruff format` fundía `FOLD_TARGET` en una sola línea ilegible. Las dos tablas llevan un comentario por grupo, para ver la correspondencia y evitar que ruff las una: `backend/apps/assets/folding.py@bbe28ba:4-35`.
