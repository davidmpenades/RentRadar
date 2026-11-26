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

## Rendimiento: después (T6)
Medición de la consulta de la lista pública con los filtros ya en el selector. El código de la medición está en `8c7521d` (`test(assets): measure the real selector with filters`): `backend/apps/assets/tests/test_list_query_plan.py@8c7521d`.

### Condiciones
- Fecha: 26-11-2026.
- Portátil enchufado a la corriente, stack levantado (backend y db) y nada más en marcha, como en T1.
- Orden: `docker compose exec -T backend pytest -q -s --run-measurement --create-db apps/assets/tests/test_list_query_plan.py`, dos veces sobre la BD de test, las dos con `2 passed` (`2 passed in 35.25s` y `2 passed in 34.79s`). La tabla es la de la segunda (`2 passed in 34.79s`).
- Volumen, semilla, zonas, calentamiento y medidas, como en T1 (`specs/008-search-filters/validation.md@8c7521d:24-30`).
- Ahora todas las filas usan el selector real con los `Filters` de `parse_filters`; las réplicas de T1 se borraron (`backend/apps/assets/tests/test_list_query_plan.py@8c7521d:225-240`).

### Sondeo del entorno (literal, segunda ejecución)
```
SHOW server_version: 18.6 (Debian 18.6-1.pgdg13+2)
SELECT datctype FROM pg_database WHERE datname = current_database(): en_US.utf8
SHOW server_encoding: UTF8
translate(text, text, text): provolatile = i
```

### Tabla (literal, segunda ejecución)
```
Consulta                        Zona  Mediana ms  Mín ms  Máx ms  Nodo de acceso    Filas descartadas  Bucles  Buffers
------------------------------  ----  ----------  ------  ------  ----------------  -----------------  ------  -------
sin filtro                      Z1    99.41       99.27   99.56   Seq Scan          23664              2       15403
sin filtro                      Z2    598.89      596.93  599.18  Seq Scan          16718              2       86209
categoría kayak                 Z1    10.90       10.83   11.41   Bitmap Heap Scan  3821               1       2574
categoría kayak                 Z2    49.93       49.46   51.37   Bitmap Heap Scan  2718               1       7105
categoría ski                   Z1    2.90        2.87    2.91    Bitmap Heap Scan  933                1       1001
categoría ski                   Z2    12.89       12.87   13.29   Bitmap Heap Scan  654                1       2144
texto «bici»                    Z1    22.87       22.36   23.56   Seq Scan          24875              2       3163
texto «bici»                    Z2    65.51       65.40   65.90   Seq Scan          24172              2       10368
texto de 1 carácter «a»         Z1    93.18       92.73   93.41   Seq Scan          23771              2       14342
texto de 1 carácter «a»         Z2    555.29      553.29  559.12  Seq Scan          17360              2       79675
texto de 2 caracteres «es»      Z1    37.70       37.29   37.74   Seq Scan          24581              2       6052
texto de 2 caracteres «es»      Z2    185.48      184.92  188.23  Seq Scan          22462              2       27652
texto sin coincidencias «zzzz»  Z1    18.11       17.41   19.37   Seq Scan          25000              2       1822
texto sin coincidencias «zzzz»  Z2    17.99       17.92   18.45   Seq Scan          25000              2       1822
categoría kayak y texto «bici»  Z1    3.21        3.19    3.23    Bitmap Heap Scan  4029               1       1747
categoría kayak y texto «bici»  Z2    7.59        7.58    7.65    Bitmap Heap Scan  3909               1       2251
```
Con 2 bucles, «Filas descartadas» es la media por bucle; el total es filas × bucles, como en T1.

### Estabilidad entre las dos ejecuciones
- La diferencia máxima entre las medianas es del 3,77 % («zzzz», Z1: 18,82 ms en la primera ejecución y 18,11 ms en la segunda). Ocho de las 16 filas pasan del 1 %.
- El nodo de acceso, las filas descartadas y los bucles son idénticos en las 16 filas de las dos ejecuciones.

### Criterios
- Sin filtro no empeora (`specs/008-search-filters/plan.md@af3e128:220`): en Z1, 99.41 ≤ 99.42 × 1,10 + 1 = 110.362; en Z2, 598.89 ≤ 594.82 × 1,10 + 1 = 655.302. En las dos zonas, el mismo nodo de acceso (Seq Scan). Cumple.
- Umbral con filtro (`specs/008-search-filters/plan.md@af3e128:221`): en Z1, kayak 10.90, ski 2.90 y «bici» 22.87 son ≤ 1,5 × 99.41 = 149.115. Cumple.
- Peores casos (`specs/008-search-filters/plan.md@af3e128:222`): se registran sin umbral, son las filas de 1 y 2 caracteres, «zzzz» y las de Z2 de la tabla.
- Índice (`specs/008-search-filters/plan.md@af3e128:224`): en Z2 sin filtro, el plan es un Seq Scan con 16718 × 2 = 33436 filas descartadas de 50 000, un 66,87 %, por debajo del 80 %. La mediana (598.89 ms) supera los 20 ms, pero el criterio pide las dos condiciones. No se recomienda el índice.
- Observación, fuera del criterio: en Z1 sin filtro, 23664 × 2 = 47328 filas descartadas de 50 000 (94,66 %) en 99.41 ms. Se anota para la decisión aparte sobre el índice (`specs/008-search-filters/plan.md@af3e128:224`).

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

## T3 — comprobaciones
- Commit de código: `502a50d379f1fc75ef9dc9710cdb6f14bae682b5` `feat(assets): validate public list filters`. Dos ficheros nuevos: `backend/apps/assets/filters.py` y `backend/apps/assets/tests/test_filters.py`. El diff completo (`git diff HEAD~1 HEAD`) tiene el sha256 `8b13c72f4e95fe0a8a1d82804da51edecb612216da5b2742576f98966e1fa6cc`, el mismo que el diff revisado antes del commit. Sin mutaciones: el plan no pide ninguna en esta tarea.
- Prueba en rojo, antes de escribir `filters.py`: `pytest -q apps/assets/tests/test_filters.py` terminó con `ImportError: cannot import name 'filters' from 'apps.assets'` y `1 error in 0.20s` (error de colección, porque el módulo no existía).
- Con `filters.py` escrito y formateado con `ruff format`: `46 passed in 0.12s`.
- Colección de `apps/assets/tests` (`pytest --collect-only -q`): de 1121 a 1167 tests. Diff literal, antes contra después:
```
491a492,537
> apps/assets/tests/test_filters.py::test_no_filter_parameters_return_no_filters[no-parameters]
> apps/assets/tests/test_filters.py::test_no_filter_parameters_return_no_filters[names-are-case-sensitive]
> apps/assets/tests/test_filters.py::test_valid_filters_are_returned_trimmed_and_folded[category-ski]
> apps/assets/tests/test_filters.py::test_valid_filters_are_returned_trimmed_and_folded[category-sports-area]
> apps/assets/tests/test_filters.py::test_valid_filters_are_returned_trimmed_and_folded[category-of-50-characters]
> apps/assets/tests/test_filters.py::test_valid_filters_are_returned_trimmed_and_folded[text-trimmed]
> apps/assets/tests/test_filters.py::test_valid_filters_are_returned_trimmed_and_folded[text-folded]
> apps/assets/tests/test_filters.py::test_valid_filters_are_returned_trimmed_and_folded[category-and-text]
> apps/assets/tests/test_filters.py::test_a_text_in_nfd_is_normalised_before_folding[accent]
> apps/assets/tests/test_filters.py::test_a_repeated_parameter_is_rejected[category-two-values]
> apps/assets/tests/test_filters.py::test_a_repeated_parameter_is_rejected[text-same-value-twice]
> apps/assets/tests/test_filters.py::test_an_empty_value_is_an_error_and_not_a_missing_filter[category]
> apps/assets/tests/test_filters.py::test_an_empty_value_is_an_error_and_not_a_missing_filter[text]
> apps/assets/tests/test_filters.py::test_a_parameter_without_equals_arrives_as_an_empty_value[q]
> apps/assets/tests/test_filters.py::test_a_text_that_is_empty_after_trimming_is_empty[tab-and-newline]
> apps/assets/tests/test_filters.py::test_a_text_that_is_empty_after_trimming_is_empty[no-break-and-ideographic-space]
> apps/assets/tests/test_filters.py::test_a_text_that_is_empty_after_trimming_is_empty[100-spaces]
> apps/assets/tests/test_filters.py::test_a_text_of_up_to_64_characters_is_accepted[64]
> apps/assets/tests/test_filters.py::test_a_text_of_up_to_64_characters_is_accepted[64-surrounded-by-no-break-and-ideographic-spaces]
> apps/assets/tests/test_filters.py::test_a_text_of_up_to_64_characters_is_accepted[65-in-nfd-that-are-64-in-nfc]
> apps/assets/tests/test_filters.py::test_a_text_of_more_than_64_characters_is_too_long[65]
> apps/assets/tests/test_filters.py::test_a_text_of_more_than_64_characters_is_too_long[65-with-a-control-character]
> apps/assets/tests/test_filters.py::test_a_control_character_inside_the_text_is_rejected[tab]
> apps/assets/tests/test_filters.py::test_a_control_character_inside_the_text_is_rejected[delete]
> apps/assets/tests/test_filters.py::test_a_control_character_inside_the_text_is_rejected[c1-control]
> apps/assets/tests/test_filters.py::test_control_characters_at_the_ends_are_trimmed_and_not_rejected[line-break-at-the-end]
> apps/assets/tests/test_filters.py::test_format_and_combining_characters_are_accepted_and_kept[zero-width-space]
> apps/assets/tests/test_filters.py::test_format_and_combining_characters_are_accepted_and_kept[combining-acute]
> apps/assets/tests/test_filters.py::test_a_category_with_a_wrong_format_is_rejected[double-hyphen]
> apps/assets/tests/test_filters.py::test_a_category_with_a_wrong_format_is_rejected[trailing-newline]
> apps/assets/tests/test_filters.py::test_a_category_with_a_wrong_format_is_rejected[uppercase]
> apps/assets/tests/test_filters.py::test_a_category_with_a_wrong_format_is_rejected[leading-space]
> apps/assets/tests/test_filters.py::test_a_category_with_a_wrong_format_is_rejected[arabic-indic-digit]
> apps/assets/tests/test_filters.py::test_a_category_of_more_than_50_characters_is_too_long[51-valid-format]
> apps/assets/tests/test_filters.py::test_a_category_of_more_than_50_characters_is_too_long[51-wrong-format]
> apps/assets/tests/test_filters.py::test_the_category_pattern_is_the_one_of_the_category_model
> apps/assets/tests/test_filters.py::test_both_filters_failing_return_both_codes_in_order
> apps/assets/tests/test_filters.py::test_only_the_failing_filter_is_reported[category-bad-text-ok]
> apps/assets/tests/test_filters.py::test_every_filter_code_returned_belongs_to_the_filter_codes
> apps/assets/tests/test_filters.py::test_zone_and_filter_errors_are_returned_together[south-and-empty-text]
> apps/assets/tests/test_filters.py::test_zone_and_filter_errors_are_returned_together[valid-zone-and-empty-text]
> apps/assets/tests/test_filters.py::test_an_inverted_zone_with_an_invalid_filter_reports_only_the_filter
> apps/assets/tests/test_filters.py::test_once_the_filters_are_valid_the_zone_error_is_reported[inverted-with-valid-filters]
> apps/assets/tests/test_filters.py::test_the_query_carries_the_zone_and_its_filters[without-filters]
> apps/assets/tests/test_filters.py::test_the_query_carries_the_zone_and_its_filters[with-filters]
> apps/assets/tests/test_filters.py::test_filters_module_stays_pure_without_django_drf_or_other_apps
1123c1169
< 1121 tests collected in 0.75s
---
> 1167 tests collected in 0.81s
```
  Son exactamente 46 ids añadidos, todos de `apps/assets/tests/test_filters.py::`, y ninguno eliminado ni renombrado (la única línea que cambia es la del resumen). La colección se repitió tras la corrección de la tanda y es idéntica (`1167 tests collected in 0.75s`).
- Ficheros nuevos: en NFC y sin caracteres de formato, combinantes ni de control literales; el Unicode especial de los tests va con `chr()`.
- Tanda previa al commit. La primera falló por un aviso de ruff en mi test y se repitió entera tras corregirlo.
  - Primera tanda (solo backend), con `test_filters.py` todavía con `assert NO_FILTERS == Filters(...)`:
    - `docker compose exec backend pytest -q`: `1 failed, 2655 passed, 2 skipped in 44.64s`. El test rojo era `config/tests/test_tooling.py::test_ruff_accepts_the_backend_code`, consecuencia del aviso de ruff.
    - `docker compose exec backend sh -c "ruff check . && ruff format --check ."`: `Found 1 error.` y «[*] 1 fixable with the --fix option.» El aviso era SIM300 (condición «Yoda») en `backend/apps/assets/tests/test_filters.py@502a50d:61`.
    - `pytest -q config/tests/test_migrations.py`: `1 passed in 0.90s`. Desfase de `openapi.json`: sin diferencias, código 0. `manage.py check`: `System check identified no issues (0 silenced).`
  - Corrección: se invierte el orden de esa aserción (`assert Filters(category_slug=None, title_fragment=None) == NO_FILTERS`). Solo cambia un test, así que la tanda se repitió entera.
  - Repetición entera, con la línea de resumen literal de cada orden:
    - `docker compose exec backend pytest -q`: `2656 passed, 2 skipped in 43.74s` (los dos saltados son los de medición).
    - `docker compose exec backend sh -c "ruff check . && ruff format --check ."`: `All checks passed!` y `158 files already formatted`.
    - `docker compose exec backend pytest -q config/tests/test_migrations.py`: `1 passed in 0.89s`.
    - Desfase de `openapi.json` (`spectacular --validate --fail-on-warn` y `diff /tmp/openapi.json openapi.json`): sin diferencias, código de salida 0.
    - `manage.py check`: `System check identified no issues (0 silenced).`
    - `npx vitest run`: `Test Files  36 passed (36)` y `Tests  1324 passed (1324)`.
    - `npm run build`: `✓ built in 690ms`.
    - `npm run api:check`: `✨ openapi-typescript 7.13.0`, código de salida 0.
    - eslint no aplica: esta tarea no toca `frontend/`.
- Tercer uso: `make_params` y `VALENCIA` aparecen solo en `test_zone.py` y `test_filters.py` (`git grep -n -E "def make_params|^VALENCIA = " -- backend`), así que todavía no se extraen.

### Desviaciones del plan en T3
1. Los tests de B7 se recortaron a un id por fallo distinto: 46 ids en 23 funciones, anclados en `backend/apps/assets/tests/test_filters.py@502a50d:59-329`. Quedaron fuera, cada uno con su motivo:
   - `test_filters_are_immutable_because_no_filters_is_shared`: sin test. Si `Filters` dejase de ser `frozen`, ningún test fallaría (`backend/apps/assets/filters.py@502a50d:26-27` y `32-33`).
   - `64-emoji`: sin test. Medir la longitud en bytes en lugar de en puntos de código no lo detecta ningún otro id.
   - `text-keeps-the-enye` y `nfd-enye`: la distinción de la ñ ya la fija `test_folding.py` de T2, y `nfd-enye` repite el fallo de `accent` (no pasar a NFC antes de plegar).
   - `right-to-left-override`: mismo fallo que `zero-width-space` (rechazar o descartar un carácter de formato).
   - Variantes con el mismo fallo que otro id conservado: `only-the-zone-parameters`, `category-same-value-twice`, `text-two-values`, la variante `category` de «parámetro sin `=`», `spaces`, `no-break-space`, `ideographic-space`, `64-surrounded-by-spaces`, `nul`, `newline`, `tab-and-carriage-return-around`, `category-ok-text-bad`, `all-bounds-and-both-filters`, `too-large-with-wrong-category`, `inverted-without-filters` y `too-large-with-valid-filters`.
   - `leading-hyphen`, `trailing-hyphen`, `underscore`, `trailing-space` y `accented-letter`: el patrón de categoría queda fijado por `test_the_category_pattern_is_the_one_of_the_category_model` (`backend/apps/assets/tests/test_filters.py@502a50d:226`).
   - `never_carry_the_received_value`: se sustituye por `test_every_filter_code_returned_belongs_to_the_filter_codes` (`backend/apps/assets/tests/test_filters.py@502a50d:247`), que exige que los códigos devueltos sean exactamente los cinco del conjunto cerrado.
   - `invalid_filter_with_a_valid_zone`: lo absorbe `valid-zone-and-empty-text` de `test_zone_and_filter_errors_are_returned_together` (`backend/apps/assets/tests/test_filters.py@502a50d:275`).
2. No hay test de `re.match` frente a `fullmatch`. Con el patrón anclado con `\A` y `\Z`, las dos funciones dan el mismo resultado, así que no hay fallo que nombrar. Lo único que cambiaría el resultado es sustituir `\Z` por `$`, y lo detecta `trailing-newline` (`backend/apps/assets/tests/test_filters.py@502a50d:205`) sobre el patrón de `backend/apps/assets/filters.py@502a50d:23` y su uso en `backend/apps/assets/filters.py@502a50d:57`.
3. Test de pureza añadido, que no estaba en B7: `test_filters_module_stays_pure_without_django_drf_or_other_apps` (`backend/apps/assets/tests/test_filters.py@502a50d:315-329`). Impide importar Django, DRF u otra app salvo `apps.assets.folding` y `apps.assets.zone`; la tentación era `apps.core.text`, que importa Django. Por eso `filters.py` lleva su propia comprobación de caracteres de control (`_has_control_character` en `backend/apps/assets/filters.py@502a50d:46-47`).
4. `PublicQuery` se define en `filters.py`: el plan la nombra en `plan.md:153` pero no la define. Es un `dataclass(frozen=True, slots=True)` con `zone` y `filters` (`backend/apps/assets/filters.py@502a50d:32-35`).
5. Un valor `[]` cuenta como parámetro ausente, y no como error (`backend/apps/assets/filters.py@502a50d:79-88`). Un `QueryDict` nunca lo produce, y la comprobación del plan solo cubría `None`.

## T4 — comprobaciones
- Commit de código: `d13fbad548b909d7ab5531e770ee434314ef46aa` `feat(assets): filter public assets by category and title`. Dos ficheros: `backend/apps/assets/selectors.py` y `backend/apps/assets/tests/test_selectors.py`. El diff completo (`git diff d13fbad~1 d13fbad`) tiene el sha256 `41651a0ba39574e28c5d92f687bc854d8a3d5476f0d949ba26bfecf2dac1bf70`, el mismo que el diff revisado antes del commit.
- Cambio del selector (`backend/apps/assets/selectors.py@d13fbad:24-45`): `visible_assets_in_zone(*, zone, limit, filters=NO_FILTERS)`. Los dos `.filter` nuevos (`category__slug` y `title_folded__contains`) van tras el filtro de la zona y antes de `order_by` y del tope (líneas 41-44), en la misma consulta. Sin `regex`, `icontains`, `extra` ni SQL a mano.
- Prueba en rojo, antes de tocar el selector: `pytest -q apps/assets/tests/test_selectors.py` dio `29 failed, 51 passed in 2.45s`, y los 29 fallos eran `TypeError: visible_assets_in_zone() got an unexpected keyword argument 'filters'`. Con el selector escrito: `80 passed in 2.35s`.
- Colección de `apps/assets/tests` (`pytest --collect-only -q`): de 1167 a 1196 tests. Diff literal, antes contra después:
```
324a325,353
> apps/assets/tests/test_selectors.py::test_a_paused_asset_is_not_returned_with_a_matching_filter
> apps/assets/tests/test_selectors.py::test_an_asset_of_a_deactivated_account_is_not_returned_with_a_matching_filter
> apps/assets/tests/test_selectors.py::test_a_text_and_category_match_outside_the_zone_is_not_returned
> apps/assets/tests/test_selectors.py::test_the_category_filter_returns_only_that_category
> apps/assets/tests/test_selectors.py::test_category_and_text_return_only_the_assets_that_meet_both
> apps/assets/tests/test_selectors.py::test_a_well_formed_unknown_category_returns_nothing_and_is_complete
> apps/assets/tests/test_selectors.py::test_the_wildcards_and_quotes_of_the_text_are_literal[percent]
> apps/assets/tests/test_selectors.py::test_the_wildcards_and_quotes_of_the_text_are_literal[underscore]
> apps/assets/tests/test_selectors.py::test_the_wildcards_and_quotes_of_the_text_are_literal[backslash]
> apps/assets/tests/test_selectors.py::test_the_wildcards_and_quotes_of_the_text_are_literal[dot-star]
> apps/assets/tests/test_selectors.py::test_the_wildcards_and_quotes_of_the_text_are_literal[quote]
> apps/assets/tests/test_selectors.py::test_the_text_is_searched_only_in_the_title[description]
> apps/assets/tests/test_selectors.py::test_the_text_is_searched_only_in_the_title[owner-email]
> apps/assets/tests/test_selectors.py::test_the_text_is_searched_only_in_the_title[coordinate]
> apps/assets/tests/test_selectors.py::test_the_text_is_searched_only_in_the_title[category-name]
> apps/assets/tests/test_selectors.py::test_a_text_of_only_combining_characters_does_not_return_every_asset
> apps/assets/tests/test_selectors.py::test_the_text_ignores_case_and_accents_but_not_the_enye[esqui-finds-accented-title]
> apps/assets/tests/test_selectors.py::test_the_text_ignores_case_and_accents_but_not_the_enye[upper-accented-text-finds-plain-title]
> apps/assets/tests/test_selectors.py::test_the_text_ignores_case_and_accents_but_not_the_enye[upper-bici-finds-lowercase-title]
> apps/assets/tests/test_selectors.py::test_the_text_ignores_case_and_accents_but_not_the_enye[start-middle-and-end]
> apps/assets/tests/test_selectors.py::test_the_text_ignores_case_and_accents_but_not_the_enye[ano-does-not-find-enye]
> apps/assets/tests/test_selectors.py::test_the_text_ignores_case_and_accents_but_not_the_enye[upper-enye-finds-enye]
> apps/assets/tests/test_selectors.py::test_the_limit_applies_after_the_filter[more-than-the-limit-match]
> apps/assets/tests/test_selectors.py::test_the_limit_applies_after_the_filter[few-match-among-many]
> apps/assets/tests/test_selectors.py::test_a_row_has_exactly_the_whitelisted_keys_with_filters
> apps/assets/tests/test_selectors.py::test_the_selector_runs_exactly_one_query_with_filters
> apps/assets/tests/test_selectors.py::test_the_exact_location_appears_nowhere_in_the_query_with_filters
> apps/assets/tests/test_selectors.py::test_the_select_clause_has_no_user_or_owner_columns_with_filters
> apps/assets/tests/test_selectors.py::test_the_select_clause_has_no_columns_outside_the_whitelist_with_filters
1169c1198
< 1167 tests collected in 0.77s
---
> 1196 tests collected in 0.77s
```
  Son exactamente 29 ids añadidos, todos de `apps/assets/tests/test_selectors.py::`, y ninguno eliminado ni renombrado. La colección se repitió tras el cambio de nombres de tres tests y es la que figura arriba.
- Tanda previa al commit. Se ejecutó dos veces: la segunda, entera, porque cambiaron tres nombres de test y se quitaron dos `# noqa: E501` de nombres demasiado largos. La segunda, con la línea de resumen literal de cada orden:
  - `docker compose exec backend pytest -q`: `2685 passed, 2 skipped in 45.67s` (los dos saltados son los de medición; incluye `test_architecture`).
  - `docker compose exec backend sh -c "ruff check . && ruff format --check ."`: `All checks passed!` y `158 files already formatted`.
  - `docker compose exec backend pytest -q config/tests/test_migrations.py`: `1 passed in 0.89s`.
  - Desfase de `openapi.json` (`spectacular --validate --fail-on-warn` y `diff /tmp/openapi.json openapi.json`): sin diferencias, código de salida 0.
  - `manage.py check`: `System check identified no issues (0 silenced).`
  - `npx vitest run`: `Test Files  36 passed (36)` y `Tests  1324 passed (1324)`.
  - `npm run build`: `✓ built in 738ms`.
  - `npm run api:check`: `✨ openapi-typescript 7.13.0`, código de salida 0.
  - eslint no aplica: esta tarea no toca `frontend/`.
  - La primera tanda dio las mismas líneas, salvo `2685 passed, 2 skipped in 45.30s`, `1 passed in 0.91s` y `✓ built in 757ms`.
- `git grep -n "noqa" -- backend/apps` no encuentra nada.

### SQL capturado con categoría `ski` y texto «esqui»
Literal, de la consulta del selector con los dos filtros sobre una zona de Madrid:
```
SELECT "assets_asset"."public_id" AS "public_id", "assets_asset"."title" AS "title", "categories_category"."slug" AS "category__slug", "categories_category"."name" AS "category__name", "assets_asset"."price" AS "price", "assets_asset"."currency" AS "currency", "assets_asset"."price_unit" AS "price_unit", "assets_asset"."privacy_radius" AS "privacy_radius", ST_Y(("assets_asset"."public_location")::geometry(GEOMETRY,4326)) AS "latitude", ST_X(("assets_asset"."public_location")::geometry(GEOMETRY,4326)) AS "longitude" FROM "assets_asset" INNER JOIN "users_user" ON ("assets_asset"."owner_id" = "users_user"."id") INNER JOIN "categories_category" ON ("assets_asset"."category_id" = "categories_category"."id") WHERE ("users_user"."is_active" AND "assets_asset"."status" = 'active' AND ST_Y(("assets_asset"."public_location")::geometry(GEOMETRY,4326)) BETWEEN 40.3 AND 40.5 AND ST_X(("assets_asset"."public_location")::geometry(GEOMETRY,4326)) BETWEEN  -3.8 AND  -3.6 AND "categories_category"."slug" = 'ski' AND "assets_asset"."title_folded"::text LIKE '%esqui%') ORDER BY "assets_asset"."created_at" DESC, "assets_asset"."id" DESC LIMIT 201
```
- Hay dos `INNER JOIN`: `users_user` (por `is_active`) y `categories_category`, que ya existía por `category__slug` y `category__name`.
- Los dos filtros van en el mismo `WHERE`, tras la zona: `"categories_category"."slug" = 'ski'` y `"assets_asset"."title_folded"::text LIKE '%esqui%'`. Después van `ORDER BY` y `LIMIT 201`.
- `title_folded` no está en el `SELECT` y `exact_location` no aparece en ningún sitio.
- Cómo se obtuvo: se añadió un `print` temporal a `test_the_exact_location_appears_nowhere_in_the_query_with_filters`, se ejecutó ese test con `-s` y se restauró el fichero. El sha256 de `test_selectors.py` fue el mismo antes y después del `print`: `ebc0b3e1b5ce94be06250c6992628daff04e1f58fdda6697fa84d37abc84905d` (versión anterior al cambio de nombres).

### Pruebas de mecanismo (M1a, M1b, M2 y M3)
- Procedimiento, como M4 en T2: una mutación por ejecución sobre `selectors.py` con la suite completa y `-rfE`, con la copia del fichero fuera del repo, sin `sed -i`, con sha256 antes y después y restauración en `finally`. Stack en marcha (backend y db, `healthy`) y portátil enchufado antes de cada una.
- Antes de ejecutar ninguna, se escribieron el texto literal de cada mutación y los ids esperados de cada una (ordenados con `LC_ALL=C`), y se sellaron las cuatro predicciones con sha256. No se modificaron después.
- Comprobación previa de ruff por stdin sobre cada fichero mutado (`ruff check` y `ruff format --check`): código 0 y sin diferencias en las cuatro (sin I001 ni F401 con el `Q` de M2), así que `test_ruff_accepts_the_backend_code` no entra en ninguna predicción.
- Qué más usa el selector, buscado en toda la suite: `test_selectors.py`, `test_public_list_api.py` (el endpoint llama al selector), `test_demo_command.py` (`test_the_public_selector_returns_the_24_active_assets_and_not_the_paused_one`) y `test_list_query_plan.py` (saltado sin `--run-measurement`). `test_public_list_session.py` crea bienes activos y `test_architecture.py` solo prohíbe métodos de escritura (`extra` no lo es).
- Base de la suite sin mutar: `2685 passed, 2 skipped`.

#### M1a — quitar `status="active"`
Sustitución en `backend/apps/assets/selectors.py@d13fbad:30`:
```
        Asset.objects.filter(status="active", owner__is_active=True)
```
pasa a
```
        Asset.objects.filter(owner__is_active=True)
```
- Predicción sellada: `7 failed, 2678 passed, 2 skipped`.
- Resultado, línea de resumen literal: `7 failed, 2678 passed, 2 skipped in 46.68s`.
- Ids fallidos (orden `LC_ALL=C`), idénticos a los predichos:
```
apps/assets/tests/test_demo_command.py::test_the_public_selector_returns_the_24_active_assets_and_not_the_paused_one
apps/assets/tests/test_public_list_api.py::test_a_paused_asset_never_appears_not_even_for_its_owner_with_a_session
apps/assets/tests/test_public_list_api.py::test_every_kind_of_visitor_receives_the_same_body_without_hidden_assets[anonymous]
apps/assets/tests/test_public_list_api.py::test_every_kind_of_visitor_receives_the_same_body_without_hidden_assets[owner]
apps/assets/tests/test_public_list_api.py::test_every_kind_of_visitor_receives_the_same_body_without_hidden_assets[staff]
apps/assets/tests/test_selectors.py::test_a_paused_asset_is_not_returned_even_if_its_owner_is_active
apps/assets/tests/test_selectors.py::test_a_paused_asset_is_not_returned_with_a_matching_filter
```
- Mensaje de la demostración: `assert 25 == 24` (el pausado entra en la lista).
- ERROR: 0 líneas `^ERROR ` y ninguna aparición de «error» en la línea de resumen.

#### M1b — quitar `owner__is_active=True`
Sustitución en `backend/apps/assets/selectors.py@d13fbad:30`:
```
        Asset.objects.filter(status="active", owner__is_active=True)
```
pasa a
```
        Asset.objects.filter(status="active")
```
- Predicción sellada: `7 failed, 2678 passed, 2 skipped`.
- Resultado: `7 failed, 2678 passed, 2 skipped in 46.65s`.
- Ids fallidos, idénticos a los predichos (`test_the_where_clause_filters_by_the_public_location_in_both_axes` lo ve porque exige `is_active` en el `WHERE`):
```
apps/assets/tests/test_public_list_api.py::test_an_active_asset_of_a_deactivated_account_is_hidden
apps/assets/tests/test_public_list_api.py::test_every_kind_of_visitor_receives_the_same_body_without_hidden_assets[anonymous]
apps/assets/tests/test_public_list_api.py::test_every_kind_of_visitor_receives_the_same_body_without_hidden_assets[owner]
apps/assets/tests/test_public_list_api.py::test_every_kind_of_visitor_receives_the_same_body_without_hidden_assets[staff]
apps/assets/tests/test_selectors.py::test_an_active_asset_of_an_owner_with_a_deactivated_account_is_not_returned
apps/assets/tests/test_selectors.py::test_an_asset_of_a_deactivated_account_is_not_returned_with_a_matching_filter
apps/assets/tests/test_selectors.py::test_the_where_clause_filters_by_the_public_location_in_both_axes
```
- ERROR: 0 líneas `^ERROR ` y ninguna aparición de «error» en la línea de resumen.

#### M2 — el filtro de texto busca también en `description`
Dos sustituciones. En `backend/apps/assets/selectors.py@d13fbad:2`:
```
from django.db.models import FloatField, Func
```
pasa a
```
from django.db.models import FloatField, Func, Q
```
Y en `backend/apps/assets/selectors.py@d13fbad:44`:
```
        queryset = queryset.filter(title_folded__contains=filters.title_fragment)
```
pasa a
```
        queryset = queryset.filter(
            Q(title_folded__contains=filters.title_fragment)
            | Q(description__contains=filters.title_fragment)
        )
```
- Predicción sellada: `1 failed, 2684 passed, 2 skipped`.
- Resultado: `1 failed, 2684 passed, 2 skipped in 46.01s`.
- Id fallido, idéntico al predicho:
```
apps/assets/tests/test_selectors.py::test_the_text_is_searched_only_in_the_title[description]
```
- Mensaje: `assert ([{'public_id... ...}], False) == ([], False)` (el bien se encuentra por su descripción).
- Por qué solo falla uno: la descripción por defecto de `make_asset` («Taladro de percusion en buen estado») no contiene ningún fragmento de los demás tests de texto, y solo `[description]` crea una descripción propia.
- ERROR: 0 líneas `^ERROR ` y ninguna aparición de «error» en la línea de resumen.

#### M3 — LIKE sin escapar con `.extra`
Sustitución en `backend/apps/assets/selectors.py@d13fbad:44`:
```
        queryset = queryset.filter(title_folded__contains=filters.title_fragment)
```
pasa a
```
        queryset = queryset.extra(
            where=["title_folded LIKE %s"], params=[f"%{filters.title_fragment}%"]
        )
```
(la forma de `tasks.md`, con `filters.title_fragment` en lugar de `fragment`, que es el nombre real en el código).
- Predicción sellada: `3 failed, 2682 passed, 2 skipped`.
- Resultado: `3 failed, 2682 passed, 2 skipped in 44.45s`.
- Ids fallidos, idénticos a los predichos:
```
apps/assets/tests/test_selectors.py::test_the_wildcards_and_quotes_of_the_text_are_literal[backslash]
apps/assets/tests/test_selectors.py::test_the_wildcards_and_quotes_of_the_text_are_literal[percent]
apps/assets/tests/test_selectors.py::test_the_wildcards_and_quotes_of_the_text_are_literal[underscore]
```
- `[dot-star]` y `[quote]` siguen en verde por diseño: en un `LIKE`, `.*` es un texto literal, y la comilla viaja como parámetro ligado. Esos dos casos protegen contra otras mutaciones (expresión regular y SQL concatenado), que no son esta.
- Mensajes: `[percent]` y `[underscore]` devuelven un bien de más (el señuelo), y `[backslash]` devuelve el señuelo en lugar del título literal.
- ERROR: 0 líneas `^ERROR ` y ninguna aparición de «error» en la línea de resumen.

#### Restauración de las cuatro
- sha256 de `selectors.py` antes de cada mutación, con la mutación puesta y tras restaurar:
  - M1a, mutado `1d36d5e15ee1b9e0c125be6c4db47b8f706e3c32bb2d24677bc25d3bb8e754eb`.
  - M1b, mutado `046f558afa21f54f55ba2e87463ae3e33d674b9fa1ea2d1d144ef712ef355362`.
  - M2, mutado `3460aa279bb3423482ff50ceefd0acaa5b2f18871e15c431f845585f80987d9a`.
  - M3, mutado `7fa678b34ea1b3789e45381b0deca3a830da9d4c6a1725d98fa7db454ad701a6`.
  - Antes y después de cada una: `a56e6c9ae4cd3c582d370f4046777d268afc39f13846f005fc7791b658bf0a0a`.
- Ese valor coincide con `git show d13fbad:backend/apps/assets/selectors.py | sha256sum`, y `git status --short` salió vacío tras cada ejecución.
- Veredicto: M1a, M1b, M2 y M3 ponen en rojo exactamente los tests previstos; ninguna sobrevive.

### Desviaciones del plan en T4
1. 29 ids en lugar de los 45 de `tasks.md`, anclados en `backend/apps/assets/tests/test_selectors.py@d13fbad:532-834`: un id por fallo distinto, y se renombraron tres tests: dos para que quepan en 88 columnas sin `noqa` y el del pausado por simetría con el de la cuenta desactivada. Qué se quitó, con su motivo:
   - Pausado y cuenta desactivada con `[category|text|both]` (6 ids) pasan a un id cada uno, con los dos filtros a la vez (`test_a_paused_asset_is_not_returned_with_a_matching_filter`, línea 601, y `test_an_asset_of_a_deactivated_account_is_not_returned_with_a_matching_filter`, línea 612): comparten el queryset base y, con los dos filtros, se ejecutan las dos ramas.
   - Coincidencia fuera de la zona `[text|both]` (2) pasa a uno (línea 624), por el mismo motivo.
   - `[zero-width-space|right-to-left-override|combining-acute]` (3) pasa a `test_a_text_of_only_combining_characters_does_not_return_every_asset` (línea 712): el fallo realista es quitar las marcas y dejar `%%`; que el parseo no rechace ni descarte los caracteres de formato lo fija `test_filters.py` de T3.
   - En la comparación de texto (8 ids) quedan 6 (línea 764): `start`, `middle` y `end` pasan a un solo id con tres bienes (`start-middle-and-end`); `nfd` se quita porque lo cubre `a_text_in_nfd_is_normalised_before_folding[accent]` de T3; la ñ pasa de un id a dos, `ano-does-not-find-enye` y `upper-enye-finds-enye`, porque son dos fallos distintos de la tabla; y `esqui`, `bici` y `upper-esqui` pasan a `esqui-finds-accented-title`, `upper-bici-finds-lowercase-title` y `upper-accented-text-finds-plain-title`.
   - Las cuatro familias de fugas con `[category|text|both]` (12 ids) pasan a un id cada una con los dos filtros (líneas 802, 813, 819 y 828), y se añade `test_the_selector_runs_exactly_one_query_with_filters` (línea 809), que no estaba en la lista: el fallo es resolver la categoría o el texto en una segunda consulta.
   - `test_the_limit_applies_after_the_filter` conserva dos ids pero con otros nombres (`more-than-the-limit-match` y `few-match-among-many`, línea 780) y otro montaje: los bienes que no cumplen son más recientes que los que cumplen, porque con `201-match` y `5-of-201-match` un filtro aplicado después del tope daba el mismo resultado.
   - `test_the_text_is_not_searched_in_the_description_the_owner_the_coordinates_or_the_category_name` pasa a `test_the_text_is_searched_only_in_the_title` (línea 696), con los mismos cuatro ids; con el nombre original, la línea del `def` medía 100 columnas. Los tests de texto construyen el filtro con `parse_filters`, no con `Filters` a mano, para que el plegado del texto y el de la columna se prueben juntos.
2. `title_folded` no lo cubría el test existente: `plan.md:333` decía que `test_the_select_clause_has_no_columns_outside_the_whitelist` lo cubría, pero ese test solo recorre seis columnas (`id`, `description`, `status`, `created_at`, `updated_at` y `category_id`; `backend/apps/assets/tests/test_selectors.py@d13fbad:503-517`). Lo cubre el test nuevo `test_the_select_clause_has_no_columns_outside_the_whitelist_with_filters` (`backend/apps/assets/tests/test_selectors.py@d13fbad:828-834`), cuya lista de columnas (`backend/apps/assets/tests/test_selectors.py@d13fbad:537-545`) empieza por `title_folded`. El test existente no se tocó.
3. M1 se parte en M1a (quitar `status="active"`) y M1b (quitar `owner__is_active=True`), porque `tasks.md` dice «`status` u `owner`» y son dos condiciones distintas de la misma consulta, cada una con tests distintos que la ven. Las dos mutaciones tocan la misma línea (`backend/apps/assets/selectors.py@d13fbad:30`), pero una por ejecución y con su propia predicción sellada.

## T5 — comprobaciones
- Commit de código: `1346356541da6c5c0ea9744e03a278a567d460fe` `feat(api): accept category and text filters`. Seis ficheros: `backend/apps/assets/views.py`, `backend/apps/assets/tests/test_public_list_api.py`, `backend/openapi.json`, `frontend/src/api/schema.gen.ts`, `frontend/src/api/publicAssets.test.ts` y `docs/architecture.md`. El diff completo (`git diff 1346356~1 1346356`) tiene el sha256 `3e9c1f61a20c1f60d1165de0c993a7c9f161c36abd024d191de60e5d562704bb`, el mismo que el diff revisado antes del commit.
- Cambio de la vista (`backend/apps/assets/views.py@1346356:86-93`): `get` valida con `parse_public_query`, lanza `ApiError` con el `ZoneError` que devuelve y pasa `zone`, `limit` y `filters` al selector. La respuesta, la caché y `Vary` no cambian (`backend/apps/assets/views.py@1346356:100-101`). Los dos parámetros nuevos salen de `_filter_parameter`, con `required=False` (`backend/apps/assets/views.py@1346356:37-44` y `62-77`).
- Tanda previa al commit. Se repitió entera tras cada cambio: la primera dio `Test Files  1 failed | 35 passed (36)` y `Tests  1 failed | 1323 passed (1324)` en `src/api/publicAssets.test.ts` (ver la desviación 2); la última, tras los dos retoques de los tests, con la línea de resumen literal de cada orden:
  - `docker compose exec backend ruff check .`: `All checks passed!`
  - `docker compose exec backend ruff format --check .`: `158 files already formatted`
  - `docker compose exec backend pytest -q`: `2697 passed, 2 skipped in 54.33s`.
  - `docker compose exec backend pytest -q config/tests/test_migrations.py`: `1 passed in 1.09s`
  - Desfase de `openapi.json` (la orden de la CI, `.github/workflows/ci.yml@1346356:44`): `spectacular --validate --fail-on-warn` y `diff /tmp/openapi.json openapi.json` sin diferencias.
  - `manage.py check` en contenedor suelto con `-e DB_HOST=db-inexistente.invalid`: `System check identified no issues (0 silenced).`
  - `npx vitest run`: `Test Files  36 passed (36)` y `Tests  1324 passed (1324)`.
  - `npm run build`: `✓ built in 782ms`.
  - `npx eslint src/api/publicAssets.test.ts`: sin avisos, código de salida 0.
  - `npm run api:check`: código de salida 0 (no imprime línea de resumen).
- Suites, tras el commit: `pytest --collect-only -q apps/assets/tests` da `1208 tests collected in 1.70s` (1196 al cerrar T4, más los 12 de esta tarea). El total de `pytest -q` es `2697 passed, 2 skipped`.
- D6, `pytest --collect-only -q` sobre `apps/assets/tests/test_public_list_api.py`, `apps/assets/tests/test_public_list_session.py` y `config/tests`: de 302 a 314 tests. Son exactamente 12 ids añadidos, todos de `apps/assets/tests/test_public_list_api.py::`, y ninguno eliminado ni renombrado:
```
test_category_and_text_together_return_only_the_assets_that_meet_both
test_a_well_formed_unknown_category_returns_200_and_an_empty_complete_list
test_the_limit_applies_after_the_filter[more-than-the-limit-match]
test_the_limit_applies_after_the_filter[few-match-among-many]
test_every_kind_of_visitor_receives_the_same_body_with_filters[anonymous]
test_every_kind_of_visitor_receives_the_same_body_with_filters[owner]
test_every_kind_of_visitor_receives_the_same_body_with_filters[staff]
test_the_root_and_every_asset_have_exactly_the_planned_keys_with_filters
test_the_body_never_contains_the_exact_location_with_filters
test_with_the_limit_exceeded_invalid_filters_are_still_429
test_a_successful_request_with_a_text_does_not_leave_it_in_the_logs
test_invalid_filters_return_400_with_only_their_own_codes
```
  Tras los dos retoques de los tests, la colección se repitió y dio 314 ids, ninguno distinto de la anterior.
- Tests que cambian de aserciones, con el mismo id: `test_input_errors_are_not_stored_and_do_not_echo_the_values_or_log_them` (`backend/apps/assets/tests/test_public_list_api.py@1346356:364`), `test_unknown_parameters_are_ignored` (`backend/apps/assets/tests/test_public_list_api.py@1346356:386`) y `test_the_openapi_description_is_valid_and_documents_the_list` (`backend/apps/assets/tests/test_public_list_api.py@1346356:1022`). Los cinco de fugas que `tasks.md` manda no tocar no cambian.
- Contrato: `openapi.json` y `schema.gen.ts` solo añaden `category` y `q`, opcionales y de tipo `string`, sin `pattern` ni `maxLength` (`backend/openapi.json@1346356:317` y `343`; `frontend/src/api/schema.gen.ts@1346356:361` y `367`). Los cuatro límites siguen con `required: true`.

### Desviaciones del plan en T5
1. 12 tests nuevos en lugar de los 28 de `tasks.md` (`specs/008-search-filters/tasks.md@1346356:147`), anclados en `backend/apps/assets/tests/test_public_list_api.py@1346356:871-1007`: un id por fallo distinto. Once de los 12 salen de la lista de 28; el duodécimo, `test_invalid_filters_return_400_with_only_their_own_codes` (línea 999), no estaba en ella. Qué se quitó o cambió:
   - `test_the_category_filter_returns_only_that_category` (1) no se escribió. Lo que lo cubre son `test_category_and_text_together_return_only_the_assets_that_meet_both` (línea 882) y `test_a_well_formed_unknown_category_returns_200_and_an_empty_complete_list` (línea 896).
   - Los 9 de visitantes con `[category|text|both]` pasan a 3, uno por visitante, con los dos filtros a la vez (línea 930).
   - Los de pausado y de cuenta desactivada con cada filtro (6 ids) no se escribieron: los cubre el de visitantes, que incluye un bien pausado y otro de una cuenta desactivada que coinciden con los dos filtros.
   - Claves y ubicación exacta con cada filtro (3 + 3) pasan a un id cada una, con los dos filtros (líneas 951 y 965).
   - Los ids de los dos tests con nombre distinto: `test_the_limit_applies_after_the_filter[more-than-the-limit-match|few-match-among-many]` (línea 908), como en T4 (antes `[201-match|5-of-201-match]`), y `test_every_kind_of_visitor_receives_the_same_body_with_filters` (línea 930), antes `..._with_any_filter`.
2. `frontend/src/api/publicAssets.test.ts` no estaba previsto: su test «la ruta y los cuatro nombres de parámetro son los de la descripción OpenAPI» comparaba los parámetros declarados con los cuatro límites y falló al ganar el contrato dos parámetros. Ahora se llama «la ruta y los parámetros de la petición son los de la descripción OpenAPI» (`frontend/src/api/publicAssets.test.ts@1346356:159`) y comprueba que hay 6 declarados (línea 171), que los obligatorios son exactamente los cuatro límites (línea 172) y que la petición sin filtros manda exactamente los obligatorios (línea 175). El cliente no se tocó.
3. Los tests se escribieron después de la vista (`backend/apps/assets/views.py@1346356:86-93`) y no se comprobó que fallaran sin ella (`backend/apps/assets/tests/test_public_list_api.py@1346356:871-1007`).

### Decisiones en T5
1. Las descripciones OpenAPI de `category` y `q` están en castellano, como la del plan (`specs/008-search-filters/plan.md@1346356:137`) y las de los cuatro límites (`backend/apps/assets/views.py@1346356:58-61`).
2. El test del tope usa `PUBLIC_LIST_LIMIT` y no un 200 literal (`backend/apps/assets/tests/test_public_list_api.py@1346356:911`, `913`, `924` y `926`). El 200 literal lo fija `test_the_max_age_and_the_limit_are_the_planned_ones` (`backend/apps/assets/tests/test_public_list_api.py@1346356:623-625`).

## T6 — comprobaciones
- Commit de código: `8c7521d92e422d41901422dd5638b1e051d64007` `test(assets): measure the real selector with filters`. Un solo fichero: `backend/apps/assets/tests/test_list_query_plan.py`. El diff completo (`git diff 8c7521d~1 8c7521d`) tiene el sha256 `bd5d2d45daeb027dd6ab00011b8a3c85927b4fa59d77edf3c9d38573b5d7c32f`, el mismo que el diff revisado antes del commit.
- Cambio (`backend/apps/assets/tests/test_list_query_plan.py@8c7521d:225-240` y `355`): `_filters_of(case)` arma `category` y `q` con `parse_filters` y comprueba que devuelve `Filters`; `_selector_sql(zone, filters)` pasa los filtros al selector real, y el bucle de medición llama a `_measure(*_selector_sql(zone, _filters_of(case)))`. `_candidate_sql`, `_query_of` y `PUBLIC_FIELDS` ya no están en el módulo (`git grep -n -E "_candidate_sql|_query_of|PUBLIC_FIELDS" 8c7521d -- backend/apps/assets/tests/test_list_query_plan.py` no encuentra nada). `Case`, el volumen, las zonas y el formato de la tabla no cambian.
- Colección (`pytest --collect-only -q apps/assets/tests/test_list_query_plan.py`): antes y después, `2 tests collected`, con los mismos dos ids (`test_probe_the_test_database_environment` y `test_measure_the_list_query_plans`). `comm` sale vacío en los dos sentidos. Es lo previsto en `specs/008-search-filters/tasks.md@af3e128:174`.
- `ruff format` sobre el módulo: `1 file left unchanged`.
- Mediciones: la orden de «Rendimiento: después (T6)», dos veces, `2 passed in 35.25s` y `2 passed in 34.79s`.
- Tanda previa al commit, con la línea de resumen literal de cada orden:
  - `docker compose exec backend ruff check .`: `All checks passed!`
  - `docker compose exec backend ruff format --check .`: `158 files already formatted`
  - `docker compose exec backend pytest -q`: `2697 passed, 2 skipped in 43.70s`
  - `docker compose exec backend pytest -q config/tests/test_migrations.py`: `1 passed in 0.89s`
  - Desfase de `openapi.json` (la orden de la CI, `.github/workflows/ci.yml@8c7521d:44`): `spectacular --validate --fail-on-warn` y `diff /tmp/openapi.json openapi.json` sin diferencias.
  - `manage.py check` en contenedor suelto con `-e DB_HOST=db-inexistente.invalid`: `System check identified no issues (0 silenced).`
  - `npx vitest run`: `Test Files  36 passed (36)` y `Tests  1324 passed (1324)`.
  - `npm run build`: `✓ built in 747ms`.
  - `npm run api:check`: código de salida 0 (no imprime línea de resumen).
  - eslint no aplica: esta tarea no toca `frontend/`.

### Desviaciones del plan en T6
Ninguna.
