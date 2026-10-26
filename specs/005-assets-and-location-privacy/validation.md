# Validación — 005-assets-and-location-privacy
Rama: `feature/005-assets-and-location-privacy` · Entorno: Docker Compose, `postgis/postgis:18-3.6` (PostgreSQL 18.6, PostGIS 3.6.4, GEOS 3.14.1, PROJ 9.8.1), Django 5.2.18, psycopg 3.3.6, Python 3.13.16, pytest 9.1.1, pytest-django 4.14.0, ruff 0.16.10

## Plataforma (T1)
Fecha: 2026-10-26 · Fichero: `backend/apps/core/tests/test_database_platform.py` · Ningún fichero de producción cambia.

| Comprobación | Orden | Resultado |
|---|---|---|
| Tests de plataforma | `docker compose exec backend pytest -q apps/core/tests/test_database_platform.py` | 32 passed |
| Suite completa | `docker compose exec backend pytest -q` | 478 passed (446 previos) |
| Estilo y formato | `docker compose exec backend sh -c "ruff check . && ruff format --check ."` | Sin incidencias; 71 ficheros formateados |

### Lo observado
| # | Comprobación | Observado | Cambio de spec que dispara |
|---|---|---|---|
| 1a | Geography con latitud o longitud fuera de rango, por texto y por WKB | No falla. Ajusta: (181, 91) → (-179, 89), (-181, -91) → (179, -89), (3, 91) → (3, 89), (181, 3) → (-179, 3). Emite un NOTICE de texto fijo («Coordinate values were coerced into range…») sin coordenadas | `/sdd-change` A: el rango lo garantiza el tipo, que ajusta; el CHECK se mantiene como coordenadas finitas (ver 1c) |
| 1b | Geography con NaN, por texto y por WKB | No falla ni avisa: guarda el NaN tal cual | Ninguno por sí solo: lo cubre 1c |
| 1c | CHECK `ST_X` entre -180 y 180 y `ST_Y` entre -90 y 90 sobre una columna geography, con NaN en cada coordenada | Lo rechaza con `CheckViolation` (23514) y el nombre de la restricción, porque en PostgreSQL NaN es mayor que cualquier número. Admite las coordenadas finitas, también las ya ajustadas | `/sdd-change` A: el CHECK se describe como «coordenadas finitas», no como «rango» |
| 2 | `POINT EMPTY` en geography | Lo acepta. Tras el cast a geometry, `ST_IsEmpty` es verdadero y `ST_Y` es `NULL` | Sin cambio: la BD necesita el CHECK de ubicación no vacía |
| 3 | `numeric(7,2)` con 100000 y `numeric(8,2)` | `DataError` (sqlstate 22003) cuyo mensaje no contiene el valor; `numeric(8,2)` lo admite | Sin cambio: D3 (a) |
| 4 | Claves ajenas de Django | `DEFERRABLE INITIALLY DEFERRED` (`auth_group_permissions`, `users_user_groups`) | Sin cambio: D3 |
| 5 | Ida y vuelta por geography de `double` con 17 cifras | Mismo `float` en 206 valores, por EWKB y por texto de 17 cifras | Sin cambio |
| 6 | Segunda conexión con `connections.create_connection("default")` | Falla con `NetworkBlockedError`: psycopg resuelve el nombre del servidor en Python y el fixture de red lo corta | RF-35 se queda en D10 (b), solo con `CaptureQueriesContext` |
| 7 | `migrate categories 0001_initial` dentro de `atomic` con `set_rollback(True)` | Dentro: 0 categorías y `0002` sin registrar. Al salir: 11 categorías y `0002` registrada | Sin cambio: RF-22 no necesita `transaction=True` |
| 8a | Violación de FK diferida | Salta en `SET CONSTRAINTS ALL IMMEDIATE` con `ForeignKeyViolation` (23503) | Sin cambio |
| 8b | `SET CONSTRAINTS` en un savepoint revertido | Las restricciones vuelven al modo con el que se entró: diferidas si entraron diferidas, inmediatas si entraron inmediatas | Sin cambio: `run_guarded` no necesita `ALL DEFERRED` tras la reversión |
| 8c | `SET CONSTRAINTS ALL IMMEDIATE` en un savepoint que termina bien | El modo inmediato sobrevive al savepoint; `ALL DEFERRED` lo devuelve a diferidas | Sin cambio: `run_guarded` necesita `ALL DEFERRED` en el camino correcto |

### Pruebas de mecanismo
Mutaciones sobre copias del fichero, borradas después. sha256 de `test_database_platform.py`, `conftest.py` y `test_postgis.py` idéntico antes y después.

| Mutación | Test que falla | Razón |
|---|---|---|
| Esperar (181, 91) sin ajuste | 1a | `assert (-179.0, 89.0) == (181, 91)` |
| `numeric(8,2)` en el desbordamiento | 3 | `DID NOT RAISE DataError` |
| Quitar `ALL DEFERRED` tras `ALL IMMEDIATE` | 8c | `assert not True` |
| Quitar `set_rollback(True)` en la semilla | 7 | `assert (0, False) == (11, True)` |
| Deshacer el bloqueo de red en el test | 6 | `DID NOT RAISE NetworkBlockedError` |
| Redondear a 6 decimales en la vuelta | 5 | Las listas de `float` difieren |
| Invertir el modo esperado tras la reversión | 8b | Falla en las dos variantes |
| Esperar `ST_IsEmpty` falso | 2 | `assert (True, None) == (False, None)` |
| Quitar el CHECK de la tabla | 1c | `DID NOT RAISE IntegrityError` en los 4 casos con NaN |
| Quitar solo el CHECK de `ST_Y` | 1c | `DID NOT RAISE IntegrityError` en los 2 casos con NaN en la latitud |

### Límites
- Los tests usan cursores crudos con texto y WKB en parámetro. El adaptador de GEOS de Django solo funciona a través del ORM, así que el camino por modelo se cubre en T6 (`test_models.py`).
- Con el bloqueo de red levantado (sondeo sin commitear), la segunda conexión abre, ve `rentradar_test`, solo ve las filas confirmadas y se cierra; con `serialized_rollback=True` las once categorías siguen en el test posterior.
