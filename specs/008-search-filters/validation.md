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
