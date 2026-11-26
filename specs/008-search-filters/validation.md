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

## T7 — comprobaciones
- Commit de código: `9b491f25676620f89a24bb35cefe21eb7ebc040e` `feat(search): add filter state and filtered request`. Nueve ficheros de `frontend/src`: `api/publicAssets.ts`, `api/publicAssets.test.ts`, `i18n/es.ts`, `map/loadAssets.ts`, `map/loadAssets.test.ts` y los cuatro nuevos de `search/` (`filters.ts`, `filters.test.ts`, `categories.ts` y `categories.test.ts`); 252 inserciones y 8 borrados. El diff completo (`git diff 9b491f2~1 9b491f2`) tiene el sha256 `9f407be61a0c8b544bc9a709e1f5e26fdfe81db4ecbd5ded2390f2ab1dfd6935`, el mismo que el diff revisado antes del commit.
- Cambio:
  - `fetchAssets(box, signal, filters = NO_FILTERS)` pega los filtros tras el cuadro con `&`, y sin filtros no queda ningún `&` sobrante (`frontend/src/api/publicAssets.ts@9b491f2:72-85` y `89`).
  - `loadAssetsForView` recibe `filters` como opción y se los pasa al fetcher (`frontend/src/map/loadAssets.ts@9b491f2:18`, `40` y `49`).
  - `es.ts` gana `categories` (`frontend/src/i18n/es.ts@9b491f2:91-104`).
- Test primero, para los tres tests de lo existente, antes de tocar `publicAssets.ts` y `loadAssets.ts` (`npx vitest run src/map/loadAssets.test.ts src/api/publicAssets.test.ts`): `Test Files  2 failed (2)` y `Tests  3 failed | 81 passed (84)`. Los tres fallos son por aserción y ninguno por import:
  - `pide el cuadro calculado con la señal de la petición…` (`frontend/src/map/loadAssets.test.ts@9b491f2:50-63`): el fetcher recibió dos argumentos y faltaba el tercero, `{}`.
  - `pasa al fetcher los filtros que recibe` (`frontend/src/map/loadAssets.test.ts@9b491f2:65-77`): al fetcher le faltaba `{ category: "ski", q: "esqui" }` como tercer argumento.
  - `añade los filtros detrás del cuadro, con & y codificados` (`frontend/src/api/publicAssets.test.ts@9b491f2:159-163`): la URL recibida terminaba en `east=10.55`, sin `&category=ski&q=esqu%C3%AD+%26+botas`.
  - Con el código escrito, esos dos ficheros y `src/search` dieron `Test Files  4 passed (4)` y `Tests  105 passed (105)`.
  - Los 21 tests de `src/search/` se escribieron junto con los módulos nuevos, sin comprobar antes el rojo. Con ellos escritos, `npx vitest run src/search` dio `Test Files  2 passed (2)` y `Tests  21 passed (21)`.
- Inventario de `npx vitest list src/search src/map src/api src/i18n`: de 315 a 338 líneas. Son exactamente 23 ids añadidos y ninguno eliminado ni renombrado (`comm` sobre las dos listas ordenadas, «solo antes» vacío). Los 23 ids, 17 de `filters.test.ts`, 4 de `categories.test.ts`, 1 de `loadAssets.test.ts` y 1 de `publicAssets.test.ts`:
```
src/api/publicAssets.test.ts > fetchPublicAssets: la petición > añade los filtros detrás del cuadro, con & y codificados
src/map/loadAssets.test.ts > loadAssetsForView > pasa al fetcher los filtros que recibe
src/search/categories.test.ts > CATEGORY_CHIPS > da a cada chip un nombre que no está vacío
src/search/categories.test.ts > CATEGORY_CHIPS > deja «Otros» como último chip
src/search/categories.test.ts > CATEGORY_CHIPS > no repite el nombre de ningún chip
src/search/categories.test.ts > CATEGORY_CHIPS > tiene exactamente los identificadores de las categorías con imagen
src/search/filters.test.ts > appliedFilters > no envía nada sin categoría ni texto
src/search/filters.test.ts > appliedFilters > no genera q con un texto de solo espacios o caracteres de control
src/search/filters.test.ts > appliedFilters > recorta el texto por los extremos y respeta los espacios de dentro
src/search/filters.test.ts > appliedFilters > sustituye los caracteres de control por un espacio
src/search/filters.test.ts > clearFilters > devuelve un estado sin categoría y con el texto vacío
src/search/filters.test.ts > filtersQuery > codifica un texto con espacio, &, %, #, ñ y un emoji
src/search/filters.test.ts > filtersQuery > devuelve una cadena vacía sin filtros
src/search/filters.test.ts > filtersQuery > pone category antes que q aunque el objeto traiga q primero
src/search/filters.test.ts > hasActiveFilters > está activo solo con un texto
src/search/filters.test.ts > hasActiveFilters > está activo solo con una categoría
src/search/filters.test.ts > hasActiveFilters > no está activo con un texto de solo espacios o caracteres de control
src/search/filters.test.ts > los cambios de estado > devuelven un estado nuevo y no modifican el anterior
src/search/filters.test.ts > setText > guarda lo escrito tal cual, sin recortar
src/search/filters.test.ts > toggleCategory > activa la categoría pulsada
src/search/filters.test.ts > toggleCategory > conserva el texto al cambiar de categoría
src/search/filters.test.ts > toggleCategory > quita la categoría al pulsar la misma
src/search/filters.test.ts > toggleCategory > sustituye la categoría activa al pulsar otra
```
  El test de `loadAssets.test.ts` que cambia de aserción conserva su id.
- Tanda previa al commit, con la línea de resumen literal de cada orden:
  - `docker compose exec backend ruff check .`: `All checks passed!`
  - `docker compose exec backend ruff format --check .`: `158 files already formatted`
  - `docker compose exec backend pytest -q`: `2697 passed, 2 skipped in 48.37s`
  - `docker compose exec backend pytest -q config/tests/test_migrations.py`: `1 passed in 0.90s`
  - Desfase de `openapi.json` (la orden de la CI, `.github/workflows/ci.yml@9b491f2:44`): `spectacular --validate --fail-on-warn` y `diff /tmp/openapi.json openapi.json` sin diferencias.
  - `manage.py check` en contenedor suelto con `-e DB_HOST=db-inexistente.invalid`: `System check identified no issues (0 silenced).`
  - `npx vitest run`: `Test Files  38 passed (38)` y `Tests  1347 passed (1347)`.
  - `npm run build`: `✓ built in 681ms`.
  - `npx eslint` sobre los nueve ficheros del commit: sin avisos, código de salida 0.
  - `npm run api:check`: código de salida 0 (no imprime línea de resumen).

### Decisiones en T7
1. `CATEGORY_CHIPS` sigue el orden de la siembra, con `ski` antes de `other` (`frontend/src/search/categories.ts@9b491f2:1-15`). Es el orden de `backend/apps/categories/migrations/0002_seed_categories.py@9b491f2:6-16`, que no incluye `ski`, y la 0003 añade Esquí (`backend/apps/categories/migrations/0003_add_ski_category.py@9b491f2:6`). Los nombres de `es.categories` (`frontend/src/i18n/es.ts@9b491f2:91-104`) son los de esas dos migraciones.
2. `NO_FILTERS` y `AppliedFilters` viven en `frontend/src/search/filters.ts@9b491f2:7` y `:4`. El plan nombra `NO_FILTERS` (`specs/008-search-filters/plan.md@b618783:51` y `:169`) pero no lo define ni lo lista entre lo que exporta `filters.ts` (`specs/008-search-filters/plan.md@b618783:48`). Los usan `frontend/src/api/publicAssets.ts@9b491f2:84` y `frontend/src/map/loadAssets.ts@9b491f2:40`.

### Desviaciones del plan en T7
1. `frontend/src/api/publicAssets.test.ts` gana un `it` nuevo (`frontend/src/api/publicAssets.test.ts@9b491f2:159-163`), contra «`publicAssets.test.ts` no cambia» (`specs/008-search-filters/tasks.md@b618783:194`). Entre los tests de T7 es el único que ve la URL real con filtros: `filters.test.ts` solo prueba `filtersQuery` y el de `loadAssets` usa un fetcher falso.
2. El inventario de `specs/008-search-filters/tasks.md@b618783:192` está desactualizado. La aserción estaba en `frontend/src/map/loadAssets.test.ts@b618783:55`, no en la línea 58. El rango 152-221 de `publicAssets.test.ts` (también en `specs/008-search-filters/plan.md@b618783:169`) no corresponde a los bloques del fichero: «la petición» empieza en la línea 149 y «tiempo máximo» en la 198 ya antes de T5 (`frontend/src/api/publicAssets.test.ts@860c698:149` y `:198`), y esa segunda empieza ahora en la 210 (`frontend/src/api/publicAssets.test.ts@9b491f2:210`).
3. F5 queda cubierto solo en parte (`specs/008-search-filters/plan.md@b618783:344-345`). El test de `loadAssets` comprueba que reenvía los filtros que recibe (`frontend/src/map/loadAssets.test.ts@9b491f2:65-77`); que «Reintentar» use los filtros vigentes depende de la ref de `MapPage` (`specs/008-search-filters/plan.md@b618783:171` y `specs/008-search-filters/tasks.md@b618783:205`) y se verifica en el navegador (`specs/008-search-filters/tasks.md@b618783:241`).

## T8 — comprobaciones
- Commit de código: `58dbfc1e166f2cf6f2e202dd83c45f49e30ec88b` `feat(map): add category chips and search box`. Diez ficheros y 420 inserciones y 18 borrados: `docs/architecture.md`, `frontend/src/i18n/es.ts`, `frontend/src/map/loadAssets.ts`, `frontend/src/map/loadAssets.test.ts`, `frontend/src/pages/MapPage.tsx`, `frontend/src/search/FilterBar.tsx`, `frontend/src/search/FilterBar.test.ts`, `frontend/src/state/zone.test.ts`, `frontend/src/styles/buttons.css` y `frontend/src/styles/fields.css`. El diff completo (`git diff 58dbfc1~1 58dbfc1`) tiene el sha256 `e8a37997feafa5465bd47eaa4780ce9f8f61c746dc59b58de3b871cf51a475ad`, el mismo que el diff de 596 líneas revisado antes del commit.
- Cambio:
  - `FilterBar` es un `form role="search"` con la etiqueta «Buscar por título» (`sr-only`), un campo `type="search"` con la lupa decorativa, el botón «Borrar texto» (solo con texto), «Quitar filtros» (solo con algún filtro activo) y un grupo «Categorías» con 12 chips con `aria-pressed` (`frontend/src/search/FilterBar.tsx@58dbfc1:65-99` y `101-123`).
  - `MapPage` guarda los filtros en estado y en una ref, y la petición lee la ref; la barra va en columna encima del mapa y no se pinta con el estilo fallido (`frontend/src/pages/MapPage.tsx@58dbfc1:29`, `32`, `51`, `93-102` y `105-115`).
  - `filters` es obligatorio en `loadAssetsForView` (`frontend/src/map/loadAssets.ts@58dbfc1:18` y `40`).
  - Los textos de la barra, en `es.search` (`frontend/src/i18n/es.ts@58dbfc1:105-111`).
  - Estilos: `.chip` (`frontend/src/styles/buttons.css@58dbfc1:93-165`) y, en el campo de búsqueda, el color del placeholder y la cruz nativa oculta (`frontend/src/styles/fields.css@58dbfc1:21-23` y `34-37`).
  - La estructura nueva, en `docs/architecture.md@58dbfc1:163`, `168` y `175-178`.
- Tests: 17 ids nuevos en `frontend/src/search/FilterBar.test.ts` (marcado con `react-dom/server`, `frontend/src/search/FilterBar.test.ts@58dbfc1:30-141`), los de F6 más el de `spellcheck`. Al ser un módulo nuevo no se comprobó antes el rojo.
- Tanda previa al commit, con la línea de resumen literal de cada orden (las órdenes, en `specs/008-search-filters/tasks.md@58dbfc1:15`, `17`, `18`, `33`, `34` y `35`):
  - D1: `backend` y `db`.
  - D3: `2697 passed, 2 skipped in 54.63s`
  - D4: `All checks passed!` y `158 files already formatted`
  - D12: `1 passed in 1.16s`
  - D13: código de salida 0.
  - D14: `System check identified no issues (0 silenced).`
  - `npx vitest run`: `Test Files  39 passed (39)` y `Tests  1366 passed (1366)`.
  - `npm run build`: `✓ built in 856ms`.
  - `npx eslint` sobre `FilterBar.tsx`: código de salida 0 (ver desviación 9).
  - `npm run api:check`: código de salida 0.

### Rojo de tipos
Al hacer `filters` obligatorio en `loadAssetsForView`, antes de arreglar a los que lo llaman, `npx tsc -b` dio tres errores y ningún otro. Las posiciones son las del árbol de ese momento, no las de `58dbfc1`:
```
src/map/loadAssets.test.ts(40,7): error TS2322: Type 'Readonly<{ category?: string | undefined; q?: string | undefined; }> | undefined' is not assignable to type 'Readonly<{ category?: string | undefined; q?: string | undefined; }>'.
src/pages/MapPage.tsx(34,32): error TS2345: Argument of type '{ bounds: VisibleBounds; request: ScheduledRequest; fetchAssets: (box: RequestBox, signal: AbortSignal, filters?: Readonly<{ category?: string | undefined; q?: string | undefined; }>) => Promise<...>; report: Dispatch<...>; logError: (error: unknown) => void; }' is not assignable to parameter of type 'LoadAssetsOptions'.
src/state/zone.test.ts(37,29): error TS2345: Argument of type '{ bounds: { south: number; west: number; north: number; east: number; }; request: { signal: AbortSignal; isCurrent: () => true; }; fetchAssets: () => Promise<{ results: { public_id: string; title: string; ... 7 more ...; longitude: -0.375; }[]; incomplete: false; }>; report: (reported: RequestOutcome) => void; logEr...' is not assignable to parameter of type 'LoadAssetsOptions'.
```
- El tercer texto se anota como lo imprimió `tsc`: acaba truncado en `logEr...`.
- El de `MapPage.tsx` es el que se buscaba: `tsc` avisa de que `MapPage` no pasa `filters`.

### Inventario
- `npx vitest list src/search src/pages src/map src/state src/i18n`: de 178 a 195 líneas. Con `LC_ALL=C sort` son 17 líneas añadidas, todas de `src/search/FilterBar.test.ts`, y ninguna quitada ni renombrada. Los 17 ids:
```
src/search/FilterBar.test.ts > FilterBar > agrupa los chips bajo la etiqueta «Categorías»
src/search/FilterBar.test.ts > FilterBar > asocia al campo su etiqueta «Buscar por título»
src/search/FilterBar.test.ts > FilterBar > desactiva el autocompletado del campo
src/search/FilterBar.test.ts > FilterBar > desactiva la corrección ortográfica del campo
src/search/FilterBar.test.ts > FilterBar > limita el texto del campo a 64 caracteres
src/search/FilterBar.test.ts > FilterBar > marca el formulario como búsqueda
src/search/FilterBar.test.ts > FilterBar > muestra en el campo el texto del estado
src/search/FilterBar.test.ts > FilterBar > no ofrece «Borrar texto» con el campo vacío
src/search/FilterBar.test.ts > FilterBar > no ofrece «Quitar filtros» sin filtro activo (%s)
src/search/FilterBar.test.ts > FilterBar > no pone name a ningún control ni action al formulario
src/search/FilterBar.test.ts > FilterBar > ofrece «Borrar texto» con texto escrito
src/search/FilterBar.test.ts > FilterBar > ofrece «Quitar filtros» con %s
src/search/FilterBar.test.ts > FilterBar > pinta un chip por categoría, en orden y con su nombre
src/search/FilterBar.test.ts > FilterBar > pone aria-pressed a cada chip
src/search/FilterBar.test.ts > FilterBar > pone la marca de verificación solo en el chip activo
src/search/FilterBar.test.ts > FilterBar > pone type=button a todos los botones
src/search/FilterBar.test.ts > FilterBar > pulsa solo el chip de la categoría activa
```
- Tests existentes con el mismo id y el cuerpo cambiado:
  - el ayudante `run` de `frontend/src/map/loadAssets.test.ts` (`filters` pasa a valer `NO_FILTERS` por defecto, `frontend/src/map/loadAssets.test.ts@58dbfc1:37`);
  - `frontend/src/state/zone.test.ts` (el import, `frontend/src/state/zone.test.ts@58dbfc1:6`, y `filters: NO_FILTERS`, `:40`).

### Navegador
Chrome DevTools MCP en un contexto aislado, con el viewport emulado y sin táctil, contra `http://localhost:5173/map` y los datos de demostración de la BD de desarrollo.

#### 375×667
- Barra y campo (medidos con la etiqueta «Buscar por título»):
  - Barra de 56 a 164 (108 px de alto), formulario de 48 px y caja del campo con left 12, right 363, ancho 351 y alto 48.
  - Lupa: left 24, right 44, top 74, bottom 94, 20×20; `aria-hidden` "true", `focusable` "false" y `pointer-events` none.
  - Campo: `padding-left` 44px, `padding-right` 52px y borde de 2px; el texto empieza en x=58.
  - Placeholder «Buscar…»: color rgb(66, 75, 90), igual a `--color-muted` (#424b5a), con opacidad 1.
  - Etiqueta: clase `sr-only`, texto «Buscar por título», 1×1 px.
  - Con texto escrito y «Quitar filtros» visible: «Borrar texto» left 185.2, right 229.2, top 62, bottom 106 (44×44); «Quitar filtros» left 239.2, right 363, top 62, bottom 106 (123.8×44); campo de ancho 219.2 y alto 48; barra de 108 de alto; `scrollWidth` del documento 375 con `innerWidth` 375.
  - Con «esqui» escrito se ve una sola cruz (la del botón) y la lupa a la izquierda; la cruz nativa no aparece.
- Grupo de chips, mapa, panel y controles de MapLibre (solo se midieron con la etiqueta «Qué», con la barra también de 108 px):
  - Grupo de 108 a 160 (52 px) con `scrollWidth` 1568, `clientWidth` 375, `scrollHeight` 52, `clientHeight` 52 y `scrollbar-width: none`. Los 12 chips miden 44 px de alto.
  - Mapa de 164 a 667 (503 px). Panel de 400.2 a 667 (266.8 px), con `--panel-height` igual a `max(40dvh, 15rem)`.
  - Controles de MapLibre de 164 a 282. Atribución: top 164, bottom 184, left 50.4, ancho 324.6, alto 20. Zoom: top 194, bottom 282, left 321, right 365, 44×88.
  - `elementFromPoint` en el centro de la atribución, de «acercar» y de «alejar» devuelve sus propios elementos (`A`, `maplibregl-ctrl-icon`, `maplibregl-ctrl-icon`).
  - `--free-top`: 234px (la fórmula `ceil(282 − 56) + 8` da 234).
  - Campo: `maxlength` 64 y `autocomplete` off.
- Tras los ajustes de la desviación 4, la 8 y la marca del chip (ronda final):
  - Anchos de los 12 chips, en su orden: 185.3, 120.8, 155.3, 127.3, 103.5, 122, 164.2, 93.4, 95.8, 106.8, 90.6 y 90.9.
  - Chip activo («Kayak»): marca de 14×14 de 6 a 20 px, texto desde 24 px (4 px entre ambos), ancho 95.84 y alto 44.
  - Margen del chip enfocado dentro del grupo (de 0 a 375, con `scroll-px-3`), izquierdo y derecho en px, medido en dos `requestAnimationFrame` tras cada tecla; mínimo exigido 11.5.
    - Ida con Tab desde el campo: Bicicleta eléctrica 12 y 177.719; Caravana 205.281 y 48.969; Autocaravana 208.031 y 11.672; Furgoneta 124.328 y 123.359; Piscina 259.641 y 11.844; Barbacoa 126.156 y 126.875; Zona deportiva 199.125 y 11.703; Barco 140.297 y 141.297; Kayak 241.703 y 37.453; Piragua 256.547 y 11.641; Esquí 173.359 y 111.078; Otros 271.922 y 12.188.
    - Vuelta con Shift+Tab desde «Otros» (se parte de él; su medida es la de la llegada con Tab): Esquí 173.359 y 111.078; Piragua 58.547 y 209.641; Kayak 11.703 y 267.453; Barco 140.297 y 141.297; Zona deportiva 12.125 y 198.703; Barbacoa 126.156 y 126.875; Piscina 14.641 y 256.844; Furgoneta 124.328 y 123.359; Autocaravana 12.031 y 207.672; Caravana 127.281 y 126.969; Bicicleta eléctrica 12 y 177.719.
    - Menor margen de las dos pasadas: 11.641 («Piragua», derecha, ida); el siguiente, 11.672 («Autocaravana»).
  - Anillo de foco:
    - Chip inactivo («Bicicleta eléctrica»): `outline-offset` -5px, `outline-color` rgb(22, 71, 184), `outline-width` 2px, solid y `:focus-visible` verdadero; chipTop 112, ringOuterTop 115 y formBottom 108; borde del chip de 2px rgb(66, 75, 90).
    - Chip activo («Kayak», pulsado con Espacio): `outline-offset` -5px, `outline-color` rgb(255, 255, 255) y `outline-width` 2px; chipTop 112, ringOuterTop 115 y formBottom 108; fondo rgb(22, 71, 184) y borde rgb(18, 63, 159).
    - `forced-colors: active`, «Kayak» activo y enfocado: `outline` solid 2px rgba(0, 230, 255, 0.8) con offset -5px, borde de 2px solid rgba(0, 230, 255, 0.8), fondo rgb(0, 0, 0) y texto rgb(255, 255, 255).
  - Con «esqui» escrito, el campo lleva `spellcheck="false"` (la propiedad vale false) y no hay subrayado rojo.
- Teclado, «Borrar texto» y «Quitar filtros» (solo se midieron antes de los ajustes de la desviación 4, la 8 y la marca del chip):
  - «Borrar texto» en [185, 229], de 44 px de alto, con contorno solid de 2px rgb(22, 71, 184); «Quitar filtros» en [239, 363].
- Otros:
  - Campo: `type` search, `enterkeyhint` search y sin `name`.
  - Transiciones del chip: sin emulación, `background-color, border-color, color / 0.14s, 0.14s, 0.14s`; con `prefers-reduced-motion: reduce`, `all / 0s`. Con `forced-colors` y sin él, el chip activo lleva la marca.
- `location.href` sin cambios (`http://localhost:5173/map`); `localStorage.length` y `sessionStorage.length` valen 0.

#### 1280×800
- Medidas con la etiqueta «Buscar por título»; no consta si se tomaron antes o después de los ajustes de la desviación 4, la 8 y la marca del chip.
- Barra de 56 a 120 (64 px de alto). Formulario de 0 a 400 (400×48) y campo de 12 a 388 (376×48).
- Grupo de chips: left 412, right 1280, top 57, bottom 119; ancho 868, alto 62 (`clientHeight` 52 y `offsetHeight` 62); `scrollWidth` 1568, `clientWidth` 868, `scrollHeight` 52; `scrollbar-width: thin`; `overflow-x` auto y `overflow-y` auto. Los 12 chips miden 44 px de alto.
- Panel de 400×680 (de 120 a 800) y mapa de 1280×680.
- Controles de MapLibre: left 955.4, top 120, bottom 238. Atribución: left 955.4, top 120, bottom 140, alto 20. Zoom: left 1226, right 1270, top 150, bottom 238 (44×88). `elementFromPoint` en la atribución, «acercar» y «alejar» devuelve sus propios elementos (true los tres).
- `--free-top`: 190px (esperado 190). `scrollWidth` del documento 1280.
- Con el texto «ab» y dos Tab: «Quitar filtros» en [264, 388], de 44 px de alto; formulario de 400 de ancho y barra de 64 de alto.
- Tab hasta «Zona deportiva» (el séptimo chip): [764, 928] dentro del grupo [412, 1280]; `scrollLeft` 522 de 700; `scrollHeight` 52, igual que `clientHeight`.

### Red
Peticiones de la lista pública, vistas en el panel de red del navegador.
- Carga: 1 petición.
- «Kayak» pulsado: 1 petición con `category=kayak`. «Kayak» otra vez: 1 sin `category`.
- Escribir «esqui»: 1 petición con `q=esqui`. Intro: 1 más. Un espacio final: ninguna.
- «Borrar texto»: 1 sin `q`, con el foco en el campo.
- «Kayak» y luego «Quitar filtros»: 1 y 1; la cabecera dice «24 bienes en esta zona», hay 24 tarjetas y el foco queda en el campo.
- Esas medidas se tomaron con una versión del código anterior a los ajustes de foco y de marca.
- Ráfagas de pulsaciones, repetidas en condiciones limpias con el código final y desde la vista inicial sin filtros (una primera ronda de ráfagas se repitió así):
  - Ráfaga de 2, Kayak y Esquí: 2 peticiones (`category=kayak` y `category=ski`) tras la de carga.
  - Ráfaga de 4, Esquí, Esquí, Kayak y Esquí: 4 peticiones (`category=ski`, sin filtro, `category=kayak` y `category=ski`) tras la de carga. Al final queda «Esquí» pulsado.
- Cancelación (Slow 3G, clics con `.click()` separados 51 ms): `category=pool` acaba en `net::ERR_ABORTED` y `category=boat` en 200 (2012 ms). La cabecera dice «2 bienes en esta zona», las tarjetas son «Velero de recreo de nueve metros» y «Lancha neumática con motor», y «Barco» es el único chip pulsado.
  - El primer intento se perdió: la red del equipo cambió durante una pausa de unas 5,9 horas y la consola dio `net::ERR_NETWORK_CHANGED`. Se repitió desde cero.
- Espera de 300 ms (`REQUEST_DELAY_MS`, `frontend/src/map/scheduler.ts@58dbfc1:1`) al escribir «bici», una letra cada 100 ms con el setter nativo y un evento `input` con `bubbles`. Cada `dispatchEvent` tarda entre 23.6 y 31.9 ms y se tomó un sello antes y otro después de cada uno (última letra: 7161.4 antes y 7185 después). Resultado: una sola petición con `q=bici`, que empieza en 7462.4, es decir 301.0 ms después del sello previo a la última letra y 277.4 ms después del posterior.
- Observado: las peticiones con `q` reciben un 500 del servidor. La causa no se ha investigado; se comprueba en T10.

### Privacidad, accesibilidad y consola
- Privacidad, en todas las comprobaciones: `location.href` sin cambios (`http://localhost:5173/map`) y `localStorage.length` y `sessionStorage.length` valen 0. La página carga recursos de `http://localhost:5173` (91) y de `https://tiles.openfreemap.org` (7).
- Accesibilidad:
  - Árbol de accesibilidad: `search` → `searchbox "Buscar por título"` y 12 `button` en el orden Bicicleta eléctrica, Caravana, Autocaravana, Furgoneta, Piscina, Barbacoa, Zona deportiva, Barco, Kayak, Piragua, Esquí y Otros.
  - Todos los controles miden 44 px de alto como mínimo («Borrar texto» 44×44) y se alcanzan con Tab; el foco se ve con el anillo medido arriba.
- Sin conexión: recargar deja `chrome-error://chromewebdata/`, es decir, el propio documento no carga; el estilo fallido no se pudo comprobar así (desviación 7).
- Consola (literal):
  - `[error] Failed to load resource: the server responded with a status of 500 (Internal Server Error)`: peticiones con `q`; causa no investigada, se comprueba en T10.
  - `[error] Failed to load resource: net::ERR_INTERNET_DISCONNECTED`: provocado por la prueba sin conexión.
  - `[error] Failed to load resource: net::ERR_NETWORK_CHANGED`: observado durante un cambio de red del equipo en una pausa.
  - `[warn] layers[highway-shield-non-us].filter[1]: Expected value to be of type number, but found null instead. Falling back to false.`
  - `[warn] layers[highway-shield-us-interstate].filter[1]: Expected value to be of type number, but found null instead. Falling back to false.`
  - Además, `[debug] [vite] connecting...`, `[debug] [vite] connected.` y `[info] Download the React DevTools for a better development experience: https://react.dev/link/react-devtools`.

### Decisiones en T8
1. `specs/008-search-filters/tasks.md` no se enmienda: lo que difiere de él va como desviación.
2. «Borrar texto» reutiliza `.field-box` y `.eye`, y solo sale con texto (`frontend/src/search/FilterBar.tsx@58dbfc1:73` y `88-92`).
3. El foco vuelve al campo tras «Borrar texto» y tras «Quitar filtros» (`frontend/src/search/FilterBar.tsx@58dbfc1:54-57`, `89` y `95`).
4. Solo se pide de nuevo si `filtersQuery` cambia frente a la ref: un espacio final no pide (`frontend/src/pages/MapPage.tsx@58dbfc1:96-99`).
5. Intro lanza la petición siempre, con `runNow` (`frontend/src/pages/MapPage.tsx@58dbfc1:111`).
6. La barra de desplazamiento de los chips va oculta por debajo de 900 px y fina desde 900 px (`frontend/src/search/FilterBar.tsx@58dbfc1:104`), porque a 1280 px no caben (`scrollWidth` 1568 frente a 868).
7. El formulario mide 400 px, con la etiqueta y «Quitar filtros», alineado con el panel (`frontend/src/search/FilterBar.tsx@58dbfc1:68`).
8. `spellCheck` es false (`frontend/src/search/FilterBar.tsx@58dbfc1:83`): con la revisión ortográfica mejorada, Chrome envía a Google el texto que se escribe en el navegador; la básica no (https://support.google.com/chrome/answer/12027911).
9. El placeholder usa `--color-muted` (`frontend/src/styles/fields.css@58dbfc1:21-23`); medido: rgb(66, 75, 90) con opacidad 1.
10. La marca del chip activo mide 14 px y queda a 4 px del texto, sin cambiar el ancho del chip (`frontend/src/styles/buttons.css@58dbfc1:130-137`).

### Desviaciones del plan en T8
1. Cuatro ficheros fuera de la lista de T8 (`specs/008-search-filters/tasks.md@58dbfc1:204-208`): `frontend/src/map/loadAssets.ts`, `frontend/src/map/loadAssets.test.ts` y `frontend/src/state/zone.test.ts` (`filters` obligatorio, para que TypeScript detecte que `MapPage` lo olvide) y `frontend/src/styles/fields.css` (cruz nativa del campo de búsqueda y color del placeholder).
2. «Riesgo: ninguno sobre tests existentes.» (`specs/008-search-filters/tasks.md@58dbfc1:212`) no se cumple del todo: cambian el ayudante `run` de `frontend/src/map/loadAssets.test.ts` (`filters = NO_FILTERS`) y `frontend/src/state/zone.test.ts` (`filters: NO_FILTERS`), con los mismos ids. El rojo se vio con `tsc -b`: los tres errores de arriba.
3. La etiqueta «Qué» pasa a «Buscar por título» (`sr-only`), con una lupa decorativa y el placeholder «Buscar…»; aprobado por el responsable el 26-11. Motivo: «Qué» solo, sin «Dónde», no se entendía, y un placeholder no sirve como única etiqueta.
   - Literal: «El buscador tiene una etiqueta accesible «Qué».» (`specs/008-search-filters/spec.md@58dbfc1:101`); «`form role="search"` con la etiqueta visible «Qué»» (`specs/008-search-filters/plan.md@58dbfc1:176`); «el foco va al campo «Qué»» (`specs/008-search-filters/plan.md@58dbfc1:186`); «campo con etiqueta «Qué»» (`specs/008-search-filters/plan.md@58dbfc1:346`).
   - Otras líneas que usan «Qué» como nombre del buscador, sin citar: `specs/008-search-filters/spec.md@58dbfc1:6`, `11`, `36`, `68` y `70`; `specs/008-search-filters/plan.md@58dbfc1:13`, `49`, `57` y `396`; `specs/008-search-filters/tasks.md@58dbfc1:201`.
4. «el navegador lo desplaza a la vista al enfocarlo» (`specs/008-search-filters/plan.md@58dbfc1:177`) no se cumple: Chrome no desplaza un chip que ya se ve en parte. Antes del arreglo, «Barbacoa» enfocado con Tab quedaba en [371, 493] con 4 px visibles en un grupo de 375. Arreglo: `onFocus` con `scrollIntoView` y `scroll-px-3` (`frontend/src/search/FilterBar.tsx@58dbfc1:115` y `104`); el margen mínimo medido es 11.641 px.
5. Cobertura de los tests: son 17 en `frontend/src/search/FilterBar.test.ts` (los de F6, `specs/008-search-filters/plan.md@58dbfc1:346`, más el de `spellcheck`) y no se comprobó antes el rojo, por ser un módulo nuevo. `type="search"` y `enterKeyHint` no tienen test y se comprobaron en el navegador. El cableado de eventos solo se comprueba en el navegador, porque vitest corre en node.
6. `specs/008-search-filters/tasks.md@58dbfc1:213` pide listar `src/search src/pages` antes y después; se listaron además `src/map`, `src/state` y `src/i18n`.
7. El estilo fallido (la barra no pintada, `frontend/src/pages/MapPage.tsx@58dbfc1:106`) no se comprobó en el navegador: sin conexión no carga ni el documento. Se comprueba en T9 (`specs/008-search-filters/tasks.md@58dbfc1:241`).
8. El anillo de foco del chip va por dentro (`outline-offset: -5px`) con `!important`, porque la regla global de `:focus-visible` no va en capa y gana sin él (`frontend/src/styles/buttons.css@58dbfc1:122-127`). Antes: `outline-offset` de 2px y el anillo por fuera, con su borde superior en y=108 tocando el formulario.
9. La tanda previa al commit pasó `eslint` solo sobre `FilterBar.tsx`, y la regla pide pasarlo sobre todo lo tocado. Tras el commit, `npx eslint` sobre los siete ficheros .ts y .tsx de `frontend/` que toca `58dbfc1`: código de salida 0.

## T9 — comprobaciones
- Commit de código: `57eec8ef4af427f7ff98421bc0635cd277aa91f3` `feat(panel): add filtered states and headings`. Nueve ficheros de `frontend/src` y 190 inserciones y 59 borrados: `i18n/es.ts`, `pages/MapPage.tsx`, `panel/ResultsPanel.tsx`, `panel/ResultsPanel.test.ts`, `panel/header.ts`, `panel/header.test.ts`, `state/viewState.ts`, `state/viewState.test.ts` y `state/zone.test.ts`. El diff completo (`git diff 57eec8e~1 57eec8e`) tiene el sha256 `39f972cc46712ac258864dd43bd9cebf55ecbbda5405d447aa44587fec5a7426`, el mismo que el diff de 551 líneas revisado antes del commit.
- Cambio:
  - `viewState` recibe `filtersActive` y `empty` y `results` llevan `filtered` (`frontend/src/state/viewState.ts@57eec8e:29-30`, `39`, `53` y `66-67`).
  - `headerText(count, incomplete, filtered)` elige la clave de `es.panel` por plantilla y `statusText` lee `view.filtered` (`frontend/src/panel/header.ts@57eec8e:5-8`, `17` y `19`).
  - `ResultsPanel` pinta la cabecera como `<h2>` dentro de la región de estado (`frontend/src/panel/ResultsPanel.tsx@57eec8e:66`) y, en el vacío con filtros, «Quitar filtros» y, si se puede, «Volver a la zona inicial», los dos con `btn btn-primary` y en ese orden (`frontend/src/panel/ResultsPanel.tsx@57eec8e:12`, `19-20`, `31-32` y `35-44`).
  - «Quitar filtros» del panel pasa la acción por `run` y deja el foco en la cabecera con el `focusHeader` que ya existía (`frontend/src/panel/ResultsPanel.tsx@57eec8e:20-23`, `53`, `63` y `73`).
  - `MapPage` pasa `onClearFilters`, lleva un `h1` `sr-only` como primer hijo de `main` y calcula `filtersActive` con los filtros de la petición lanzada (`frontend/src/pages/MapPage.tsx@57eec8e:32`, `38-43`, `55-56`, `115` y `141`).
  - Textos nuevos: cinco claves en `es.panel` y `es.map.heading` (`frontend/src/i18n/es.ts@57eec8e:76-81` y `118`).
- Tests: 8 ids nuevos y 17 casos más en la colección (`npx vitest run` pasa de 1366 a 1383 tests); cada uno lleva encima un comentario `// Rojo si: …` con el fallo concreto:
  - `frontend/src/state/viewState.test.ts@57eec8e:98`, `108` y `122` (V1, V2 y «no añade filtered a %s»).
  - `frontend/src/panel/header.test.ts@57eec8e:28` y `72` (`headerText` y `statusText` con filtros).
  - `frontend/src/panel/ResultsPanel.test.ts@57eec8e:158`, `163` y `174` (cabecera `h2`, «Quitar filtros» y volver a la zona inicial).
- Tanda previa al commit (la de la segunda ronda), con la línea de resumen literal de cada orden (las órdenes, en `specs/008-search-filters/tasks.md@57eec8e:15`, `17`, `18`, `33`, `34` y `35`):
  - D1: `backend` y `db`.
  - D3: `2697 passed, 2 skipped in 49.14s`
  - D4: `All checks passed!` y `158 files already formatted`
  - D12: `1 passed in 1.02s`
  - D13: código de salida 0.
  - D14: `System check identified no issues (0 silenced).`
  - `npx vitest run`: `Test Files  39 passed (39)` y `Tests  1383 passed (1383)`.
  - `npm run build`: `✓ built in 708ms`.
  - `npx eslint` sobre los nueve ficheros .ts y .tsx del commit: código de salida 0.
  - `npm run api:check`: código de salida 0.

### Rojo
Se tomó con los tests escritos antes del código, antes de los comentarios «Rojo si» y antes del cambio de `MapPage` de la segunda ronda (filtros de la petición lanzada).
- `npx vitest run src/state/viewState.test.ts src/panel/header.test.ts src/panel/ResultsPanel.test.ts`:
  - ` Test Files  3 failed (3)`
  - `      Tests  19 failed | 79 passed (98)`
- Las 19 líneas, todas por `AssertionError` y ninguna por import:
```
 FAIL  src/panel/ResultsPanel.test.ts > ResultsPanel > pinta la cabecera como h2 dentro de la región de estado (carga)
 FAIL  src/panel/ResultsPanel.test.ts > ResultsPanel > pinta la cabecera como h2 dentro de la región de estado (resultados)
 FAIL  src/panel/ResultsPanel.test.ts > ResultsPanel > pinta la cabecera como h2 dentro de la región de estado (vacío)
 FAIL  src/panel/ResultsPanel.test.ts > ResultsPanel > pinta la cabecera como h2 dentro de la región de estado (acerca el mapa)
 FAIL  src/panel/ResultsPanel.test.ts > ResultsPanel > pinta la cabecera como h2 dentro de la región de estado (error)
 FAIL  src/panel/ResultsPanel.test.ts > ResultsPanel > pinta «Quitar filtros» solo en el vacío con filtros
 FAIL  src/panel/ResultsPanel.test.ts > ResultsPanel > en el vacío con filtros ofrece volver a la zona inicial solo si se puede
 FAIL  src/panel/header.test.ts > headerText > con filtros, 1 con la lista incompleta false dice «1 bien en esta zona con estos filtros»
 FAIL  src/panel/header.test.ts > headerText > con filtros, 24 con la lista incompleta false dice «24 bienes en esta zona con estos filtros»
 FAIL  src/panel/header.test.ts > headerText > con filtros, 1 con la lista incompleta true dice «Mostrando 1 bien con estos filtros. Puede haber más: acerca el mapa para verlos todos»
 FAIL  src/panel/header.test.ts > headerText > con filtros, 40 con la lista incompleta true dice «Mostrando 40 bienes con estos filtros. Puede haber más: acerca el mapa para verlos todos»
 FAIL  src/panel/header.test.ts > statusText > con filtros, el vacío dice «No hay bienes en esta zona con estos filtros»
 FAIL  src/panel/header.test.ts > statusText > con filtros, los resultados dice «1 bien en esta zona con estos filtros»
 FAIL  src/state/viewState.test.ts > viewState > es results con las tarjetas en el orden de la respuesta
 FAIL  src/state/viewState.test.ts > viewState > es empty con una respuesta válida sin bienes
 FAIL  src/state/viewState.test.ts > viewState > es empty si hay bienes pero ninguno se ve en la zona visible
 FAIL  src/state/viewState.test.ts > viewState > no ofrece volver a la zona inicial si ya está en ella, ni en vacío ni en zoomIn
 FAIL  src/state/viewState.test.ts > viewState > marca como filtrado el vacío cuando hay filtros activos
 FAIL  src/state/viewState.test.ts > viewState > marca como filtrados los resultados cuando hay filtros activos
```
- Verde desde el principio: «no añade filtered a %s aunque haya filtros activos». De «pinta «Quitar filtros» solo en el vacío con filtros» falla la primera aserción; la mitad sin filtros ya era verde.

### Rojo de tipos
Al cambiar solo los tipos (`ViewState`, `ViewStateInput`, la firma de `headerText` y las props de `ResultsPanel`), antes de arreglar a quienes los usan y con las mismas salvedades de arriba, `npx tsc -b` dio seis errores, solo en `MapPage.tsx`, `ResultsPanel.tsx`, `header.ts` y `viewState.ts`, y ninguno en tests. Las posiciones son las del árbol de ese momento, no las de `57eec8e`:
```
src/pages/MapPage.tsx(35,26): error TS2345: Argument of type '{ styleFailed: boolean; request: RequestState; atInitialView: boolean; }' is not assignable to parameter of type 'ViewStateInput'.
  Property 'filtersActive' is missing in type '{ styleFailed: boolean; request: RequestState; atInitialView: boolean; }' but required in type 'ViewStateInput'.
src/pages/MapPage.tsx(127,10): error TS2741: Property 'onClearFilters' is missing in type '{ view: ViewState; onRetry: () => void | undefined; onReset: () => void; }' but required in type 'ResultsPanelProps'.
src/panel/ResultsPanel.tsx(60,12): error TS2741: Property 'onClearFilters' is missing in type '{ view: { kind: "loading"; } | { kind: "results"; cards: readonly { readonly public_id: string; readonly title: string; readonly category_slug: string; readonly category_name: string; readonly price: string; ... 4 more ...; readonly longitude: number; }[]; incomplete: boolean; filtered: boolean; } | { ...; } | { ......' but required in type 'ResultsPanelProps'.
src/panel/header.ts(22,14): error TS2554: Expected 3 arguments, but got 2.
src/state/viewState.ts(66,11): error TS2322: Type '{ kind: "empty"; canReset: boolean; }' is not assignable to type 'ViewState'.
  Property 'filtered' is missing in type '{ kind: "empty"; canReset: boolean; }' but required in type '{ kind: "empty"; canReset: boolean; filtered: boolean; }'.
src/state/viewState.ts(67,11): error TS2322: Type '{ kind: "results"; cards: { readonly public_id: string; readonly title: string; readonly category_slug: string; readonly category_name: string; readonly price: string; readonly currency: string; readonly price_unit: string; readonly privacy_radius: number; readonly latitude: number; readonly longitude: number; }[]; ...' is not assignable to type 'ViewState'.
  Property 'filtered' is missing in type '{ kind: "results"; cards: { readonly public_id: string; readonly title: string; readonly category_slug: string; readonly category_name: string; readonly price: string; readonly currency: string; readonly price_unit: string; readonly privacy_radius: number; readonly latitude: number; readonly longitude: number; }[]; ...' but required in type '{ kind: "results"; cards: readonly { readonly public_id: string; readonly title: string; readonly category_slug: string; readonly category_name: string; readonly price: string; readonly currency: string; readonly price_unit: string; readonly privacy_radius: number; readonly latitude: number; readonly longitude: numb...'.
```
- Con la implementación hecha, `npx tsc -b` dio código de salida 0.

### Inventario
- `npx vitest list src/state src/panel src/i18n src/pages`: de 77 a 85 líneas. Con `LC_ALL=C sort` son 8 líneas añadidas y ninguna quitada ni renombrada. La lista de después es la misma antes y después del cambio de `MapPage`. Los ids con `%j`, `%s` o `%d` no se expanden en la lista, así que añadir `filtered: false` a las filas de las tablas no cambia ningún id. Los 8 ids:
```
src/panel/ResultsPanel.test.ts > ResultsPanel > en el vacío con filtros ofrece volver a la zona inicial solo si se puede
src/panel/ResultsPanel.test.ts > ResultsPanel > pinta la cabecera como h2 dentro de la región de estado (%s)
src/panel/ResultsPanel.test.ts > ResultsPanel > pinta «Quitar filtros» solo en el vacío con filtros
src/panel/header.test.ts > headerText > con filtros, %d con la lista incompleta %s dice «%s»
src/panel/header.test.ts > statusText > con filtros, %s dice «%s»
src/state/viewState.test.ts > viewState > marca como filtrado el vacío cuando hay filtros activos
src/state/viewState.test.ts > viewState > marca como filtrados los resultados cuando hay filtros activos
src/state/viewState.test.ts > viewState > no añade filtered a %s aunque haya filtros activos
```
- Tests existentes con el mismo id y el cuerpo cambiado:
  - `frontend/src/state/viewState.test.ts`: el ayudante `view`, que pasa `filtersActive: false` por defecto (`frontend/src/state/viewState.test.ts@57eec8e:34-37`), y cuatro `toEqual` con `filtered: false` (`:56`, `:71`, `:75` y `:83`).
  - `frontend/src/panel/header.test.ts`: cuatro llamadas a `headerText` con un tercer argumento `false` (`frontend/src/panel/header.test.ts@57eec8e:7`, `11`, `15` y `19`) y tres filas de la tabla de `statusText` con `filtered: false` (`:49-51`).
  - `frontend/src/panel/ResultsPanel.test.ts`: el ayudante `panel`, con `onClearFilters: noop` (`frontend/src/panel/ResultsPanel.test.ts@57eec8e:35-36`), y trece literales de `ViewState` con `filtered: false` (`:100`, `:111-112`, `:126-127`, `:145-146`, `:198`, `:200`, `:218-219`, `:242` y `:251`).
  - `frontend/src/state/zone.test.ts`: la llamada a `viewState` con `filtersActive: false` (`frontend/src/state/zone.test.ts@57eec8e:50`).

### Navegador
Chrome DevTools MCP en un contexto aislado, con el viewport emulado y sin táctil, contra `http://localhost:5173/map` y los datos de demostración de la BD de desarrollo.

#### Primera ronda (375×667 y 1280×800)
Se tomó con la versión anterior de `MapPage`, que calculaba `filtersActive` con lo tecleado (`hasActiveFilters(filters)`). La única diferencia con el commit es ese cálculo y los comentarios de los tests.
- Árbol de accesibilidad con datos reales, a las dos anchuras: `banner`; `main` con `heading "Bienes en alquiler en el mapa" level="1"`, `search` (`searchbox "Buscar por título"`), 12 `button` de chips, `region "Mapa de bienes en alquiler"`, y `complementary "Bienes en esta zona"` con `status` y `heading "24 bienes en esta zona" level="2"`.
- 375×667:
  - Encabezados en el DOM: `["H1:Bienes en alquiler en el mapa:sr-only","H2:24 bienes en esta zona:text-lg leading-snug font-semibold"]`. `scrollWidth` del documento 375 con `innerWidth` 375.
  - Vacío con filtros, «Kayak» pulsado (lista vacía simulada): `h2` «No hay bienes en esta zona con estos filtros». En la vista inicial solo sale «Quitar filtros», con clase `btn btn-primary mt-3`, left 17, right 168.8, top 474.7, bottom 518.7 (151.8×44). Panel: top 400.2, bottom 667, left 0, right 375, `scrollWidth` 373 y `clientWidth` 373.
  - Los dos botones, tras «Acercar» (fuera de la vista inicial), en este orden y los dos con clase `btn btn-primary mt-3`:
    - «Quitar filtros»: left 17, right 168.8, top 474.7, bottom 518.7 (151.8×44).
    - «Volver a la zona inicial»: left 17, right 239.7, top 530.7, bottom 574.7 (222.7×44).
    - Panel: `scrollWidth` 373, `clientWidth` 373, `scrollHeight` 265 y `clientHeight` 265. Documento: `scrollWidth` 375 con `innerWidth` 375. Ningún botón desborda.
  - Foco tras «Quitar filtros» del panel: `document.activeElement` es el `DIV` con `tabindex="-1"` de la cabecera del panel. Ningún chip pulsado, campo vacío, `h2` «24 bienes en esta zona» y la barra sin «Quitar filtros».
  - Error con filtros, con datos reales: con `Offline` y «Kayak», `h2` «No hay conexión. Comprueba tu red y vuelve a intentarlo.» y «Reintentar» con clase `btn btn-primary mt-3`, left 17, right 152.5 y alto 44; «Kayak» sigue pulsado. En línea, «Reintentar» repite `GET /api/v1/public/assets/?south=39.35&west=-0.50&north=39.60&east=-0.25&category=kayak`: `[net::ERR_INTERNET_DISCONNECTED]` (reqid 449) y después `[200]` (reqid 450). Después: `h2` «2 bienes en esta zona con estos filtros», «Kayak» pulsado y el foco en la cabecera del panel.
  - Estilo bloqueado: `main` con `heading "Bienes en alquiler en el mapa" level="1"` y `alert` con «No se ha podido cargar el mapa.» y `button "Reintentar"`. DOM: encabezados `["H1:Bienes en alquiler en el mapa"]`, un solo `role="alert"`, sin `form[role=search]`, 0 elementos con `aria-pressed`, sin panel; `scrollWidth` del documento 375.
- 1280×800:
  - Vacío con filtros, «Kayak» y «Acercar» (lista vacía simulada): `h2` «No hay bienes en esta zona con estos filtros». «Quitar filtros»: `btn btn-primary mt-3`, left 17, right 168.8, top 194.5, bottom 238.5 (151.8×44). «Volver a la zona inicial»: `btn btn-primary mt-3`, left 17, right 239.7, top 250.5, bottom 294.5 (222.7×44). Panel: left 0, right 400, top 120, bottom 800, `scrollWidth` 398 y `clientWidth` 398. Documento: `scrollWidth` 1280 con `innerWidth` 1280.
  - Foco tras «Quitar filtros» del panel: la cabecera del panel (`DIV`); ningún chip pulsado; `h2` «24 bienes en esta zona».
  - Error con filtros, con datos reales: con `Offline` y «Kayak», `h2` «No hay conexión. Comprueba tu red y vuelve a intentarlo.» y «Reintentar» de 135.5×44; «Kayak» pulsado. En línea, «Reintentar» repite `GET /api/v1/public/assets/?south=39.35&west=-0.65&north=39.60&east=-0.10&category=kayak`: `[net::ERR_INTERNET_DISCONNECTED]` (reqid 765) y después `[200]` (reqid 766). Después: `h2` «2 bienes en esta zona con estos filtros», «Kayak» pulsado y el foco en la cabecera del panel.
  - Estilo bloqueado: igual que a 375 (un `h1`, un `role="alert"`, ni barra, ni chips ni panel); `scrollWidth` del documento 1280.

#### Segunda ronda (375×667, con el código del commit)
Medidas de tiempo sobre el `h2` de la región de estado del panel, con el setter nativo y un evento `input` con `bubbles`, y un `MutationObserver` sobre esa región. Los tiempos se cuentan desde el momento del evento.
- Escribir una letra desde la vista inicial:
  - `h2` antes y justo tras el evento: «24 bienes en esta zona».
  - `h2` a los 130.1 ms: «24 bienes en esta zona» (no dice «con estos filtros»).
  - Cambios observados: a 309.8 ms «Buscando bienes…» y a 322.4 ms «1 bien en esta zona con estos filtros».
  - Al final: campo «a», `location.href` sin cambios, `localStorage.length` 0 y `sessionStorage.length` 0.
- Borrar el texto con el filtro aplicado:
  - `h2` antes y justo tras el evento: «1 bien en esta zona con estos filtros».
  - `h2` a los 105.3 ms: «1 bien en esta zona con estos filtros» (siguen siendo resultados pedidos con el filtro).
  - Cambios observados: a 306 ms «Buscando bienes…» y a 345.7 ms «24 bienes en esta zona».
  - Al final: campo vacío y la barra sin «Quitar filtros». Red de la lista: la carga y, al borrar, `GET /api/v1/public/assets/?south=39.35&west=-0.50&north=39.60&east=-0.25 [200]` (reqid 215 y 227).

#### Simulaciones y sus límites
- Lista vacía para `category=`: no hay ninguna categoría sin bienes en la vista inicial (los 24 bienes cubren las 12), así que un `initScript` sirvió `{ "results": [], "incomplete": false }` a las peticiones de la lista con `category=`. Vale para el estado de la interfaz con una respuesta vacía; no prueba el servidor.
- Un resultado para `q=`: las peticiones con texto dan 500 en esta BD de desarrollo (observado; se comprueba en T10, sin causa). Un `initScript` sirvió `{ results: [un bien], incomplete: false }` a las peticiones con `q=`; la única servida fue `/api/v1/public/assets/?south=39.35&west=-0.50&north=39.60&east=-0.25&q=a`, que no sale a la red. Vale para la secuencia de textos del panel; no prueba el filtro de texto del servidor.
- Estilo bloqueado: un `initScript` rechaza con `TypeError` el `fetch` a `https://tiles.openfreemap.org` dentro de la página (rechazó `https://tiles.openfreemap.org/styles/positron`, dos veces). La petición no sale y no se ve en la red; con el estilo rechazado no hay petición a la lista.
- Cada `initScript` vale para una sola navegación.

### Privacidad y consola
- Privacidad, en todas las comprobaciones: `location.href` sin cambios (`http://localhost:5173/map`) y `localStorage.length` y `sessionStorage.length` valen 0.
- Consola (literal):
  - `[error] Failed to load resource: net::ERR_INTERNET_DISCONNECTED`: una vez a 375 y una a 1280, provocado por la prueba sin conexión.
  - `[warn] layers[highway-shield-non-us].filter[1]: Expected value to be of type number, but found null instead. Falling back to false.`
  - `[warn] layers[highway-shield-us-interstate].filter[1]: Expected value to be of type number, but found null instead. Falling back to false.`
  - `[warn] layers[road_shield_us].filter[1]: Expected value to be of type number, but found null instead. Falling back to false.`: observado en la primera carga de cada anchura de la primera ronda, sin causa; no aparecía en T8.
  - Además, `[debug] [vite] connecting...`, `[debug] [vite] connected.` y `[info] Download the React DevTools for a better development experience: https://react.dev/link/react-devtools`.
  - La segunda ronda no dio errores.

### Decisiones en T9
1. `filtered` y `filtersActive` son obligatorios: `tsc` avisó en los seis sitios del rojo de tipos (`frontend/src/state/viewState.ts@57eec8e:29-30` y `39`).
2. Los dos botones del vacío con filtros son `btn btn-primary` y «Quitar filtros» va primero (`frontend/src/panel/ResultsPanel.tsx@57eec8e:35-44`); el plan dice «con «Quitar filtros» (y además «Volver a la zona inicial» si no está en la vista inicial)» (`specs/008-search-filters/plan.md@57eec8e:190`).
3. `incompleteOneFiltered` es el simétrico de `incompleteOne` y no es literal en el plan, que solo da «Mostrando N bienes con estos filtros. Puede haber más: acerca el mapa para verlos todos» (`specs/008-search-filters/plan.md@57eec8e:189`; `frontend/src/i18n/es.ts@57eec8e:78`).
4. La clave de `headerText` se arma por plantilla, así que el compilador avisa si falta alguna de las ocho (`frontend/src/panel/header.ts@57eec8e:6-8`).
5. `filtersActive` se calcula con los filtros de la petición lanzada, fijados en `run` junto al cambio a «Buscando» (`frontend/src/pages/MapPage.tsx@57eec8e:32`, `42` y `55-56`), y no con lo tecleado: el plan nombra la entrada pero no dice de dónde sale («Entrada `filtersActive`», `specs/008-search-filters/plan.md@57eec8e:53`; `viewState({ styleFailed, request, atInitialView, filtersActive })`, `:172`). Se usa `filtersQuery(...) !== ""` porque `filters.ts` no tiene una función para `AppliedFilters`: `hasActiveFilters` recibe `FilterState` (`frontend/src/search/filters.ts@57eec8e:32`; `filtersQuery`, `:38-43`).
6. Tras «Quitar filtros» del panel, el foco va a la cabecera con el `focusHeader` que ya existía (`frontend/src/panel/ResultsPanel.tsx@57eec8e:20-23`, `53` y `73`).

### Desviaciones del plan en T9
1. `frontend/src/state/zone.test.ts` queda fuera de la lista de T9 (`specs/008-search-filters/tasks.md@57eec8e:225-229`): solo gana `filtersActive: false` en la llamada a `viewState` (`frontend/src/state/zone.test.ts@57eec8e:50`).
2. «`src/panel/ResultsPanel.test.ts`: los de la región de estado y la cabecera (107-121, 139-148), por el cambio de `<p>` a `<h2>`.» (`specs/008-search-filters/tasks.md@57eec8e:237`) no se cumple: ningún test existente comprobaba `<p>`; solo ganan `filtered: false` y `onClearFilters: noop`.
3. «`npx vitest list src/state src/panel`, antes y después.» (`specs/008-search-filters/tasks.md@57eec8e:238`): se listaron además `src/i18n` y `src/pages`.
4. El fallo de «con estos filtros» durante la espera se dedujo del código (`frontend/src/pages/MapPage.tsx@5bf1719:49` y `frontend/src/map/scheduler.ts@5bf1719:39-46`) y no se midió antes del arreglo; después del arreglo sí (segunda ronda).
5. F4, «con un error, los filtros no cambian» (`specs/008-search-filters/plan.md@57eec8e:342`), y el arreglo de `MapPage` no tienen test unitario, porque `MapPage` no se prueba en node. Se comprobaron en el navegador: «Reintentar» con `category=kayak` (primera ronda) y las dos medidas de tiempo (segunda ronda).
6. A 1280 px no se midió el vacío con un solo botón.
