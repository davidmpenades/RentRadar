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

## Proyección (T2)
Fecha: 2026-10-26 · Fichero: `backend/apps/core/tests/test_projection_platform.py` · Ningún fichero de producción cambia. Las comprobaciones se hacen con el GDAL y el PROJ del backend (GDAL 3.10.3, PROJ 9.6.0 con `proj-data` 9.6.0); la imagen de PostGIS lleva PROJ 9.8.1 y no interviene.

| Comprobación | Orden | Resultado |
|---|---|---|
| Tests de proyección | `docker compose exec backend pytest -q apps/core/tests/test_projection_platform.py` | 24 passed |
| Suite completa | `docker compose exec backend pytest -q` | 502 passed (478 previos) |
| Estilo y formato | `docker compose exec backend sh -c "ruff check . && ruff format --check ."` | Sin incidencias; 72 ficheros formateados |

### Lo observado
| # | Comprobación | Observado | Cambio de spec que dispara |
|---|---|---|---|
| 1 | Versiones | GDAL 3.10.3 y PROJ 9.6.0, leída esta última con `OSRGetPROJVersion`. El test falla si cambia cualquiera de las dos, parche incluido | Sin cambio |
| 2 | Orden de ejes | Con `AxisOrder.TRADITIONAL`, `Point(lon, lat)` en EPSG:4326 da x = Este e y = Norte en EPSG:3035. Con `AxisOrder.AUTHORITY` los dos ejes salen intercambiados. Referencias al milímetro: Madrid (3159390,356; 2029850,920), Las Palmas (1816110,911; 984556,390), Palma (3686979,431; 1861579,356) | Sin cambio |
| 3 | Contraste con la fórmula LAEA elipsoidal de la guía EPSG 7-2 | La fórmula escrita en el test reproduce el ejemplo publicado (50 N 5 E → 3962799,45; 2999718,85) con diferencia menor de 5 mm. PROJ coincide con ella en 11 puntos de España (Península, Baleares y Canarias) con diferencia menor de 0,000001 mm: PROJ no aplica ningún desplazamiento de datum entre EPSG:4326 y ETRS89 | Sin cambio: no se dispara `/sdd-change` C |
| 4a | Proyectar el antípoda del origen (-52, -170) y su equivalente (-52, 190) y (-52,0000001, -170) | `GDALException("OGR failure.")`. El registro de `django.contrib.gis` recibe un único mensaje de nivel ERROR, `GDAL_ERROR 1: b'Point outside of projection domain'`, sin coordenadas | Sin cambio de spec ni de `test_logging.py`: no hace falta configurar `django.contrib.gis` |
| 4b | Puntos próximos (-51,999, -170), (-52, -169,99) y (-60, -170) | Valores finitos (por ejemplo, norte de 15946597 m en el primero) | Sin cambio |
| 4c | Desproyectar (-10 000 000, 0) | La misma `GDALException` y el mismo mensaje de registro | Sin cambio |
| 4d | ¿Algún valor no finito sin excepción? | No se ha observado ninguno | RF-31 se cubre con el antípoda real (`GDALException` capturada como `projection_failed`) y con la sustitución por infinito, que sigue siendo la única forma de probar el no finito |
| 5 | Coste de NFC y de `Decimal()` | Lineal en todos los casos (tabla siguiente) | D4 (b): sin tope bruto |

### Mediciones (sin commitear)
Una ejecución por tamaño en esta máquina, con cada medida en su propio proceso. Tamaños en puntos de código o dígitos.

| Caso | Tamaño | Tiempo |
|---|---|---|
| NFC, marcas combinantes alternas (U+0301, U+0323) | 8 000 / 160 000 / 2 500 000 | 0,31 ms / 5,89 ms / 95 ms |
| NFC, todas las marcas de una clase y luego de otra (peor caso de reordenación) | 8 000 / 160 000 / 2 500 000 | 0,26 ms / 5,69 ms / 92 ms |
| NFC, «a» más acento que se compone | 8 000 / 625 000 / 2 500 000 | 0,13 ms / 11 ms / 45 ms |
| `Decimal()` de 2 500 000 dígitos | 2 500 000 | 10 ms |
| `Decimal("1." + "0" * n)` | 2 500 000 | 9,9 ms |

### Pruebas de mecanismo
Mutaciones sobre copias del fichero, borradas después. sha256 de `test_projection_platform.py`, `conftest.py` y `test_database_platform.py` idéntico antes y después.

| Mutación | Tests que fallan | Razón |
|---|---|---|
| Falso norte de la fórmula +2 mm | 11 de contraste y el del ejemplo publicado | La diferencia supera 1 mm |
| Meridiano de origen 9 en vez de 10 | 11 de contraste y el del ejemplo publicado | La fórmula se aleja de PROJ y del ejemplo |
| Versión de GDAL 3.10.4 | Versiones | `b'3.10.3' == b'3.10.4'` |
| Referencia de Madrid con este y norte cambiados | Orden de ejes de Madrid y el de AUTHORITY | Los ejes salen intercambiados |
| Orden de ejes por defecto AUTHORITY en el ayudante | 20 de 24 | Todos los resultados salen intercambiados |
| El antípoda en la lista de puntos finitos | Finitos del antípoda | `GDALException: OGR failure.` |

### Límites
- El coste se midió una vez por tamaño; el resultado que importa es la forma (lineal), no los milisegundos.
- La función de aproximación usará el PROJ del backend (9.6.0). Las distancias de los tests de RF-26 y RF-27 las calcula `ST_Distance` sobre geography en PostGIS, que no proyecta a EPSG:3035.

## Aproximación (T4)
Fecha: 2026-10-27 · Ficheros: `backend/apps/assets/location.py` y `backend/apps/assets/tests/` (`conftest.py`, `test_location.py`, `test_location_reference.py`, `test_location_geodesic.py`).

| Comprobación | Orden | Resultado |
|---|---|---|
| Rojo previo | `docker compose exec backend pytest -q apps/assets` sin `location.py` | `ModuleNotFoundError: No module named 'apps.assets.location'` al cargar `conftest.py` |
| Recuento previo | `docker compose exec backend pytest -q --ignore=apps/assets` | 513 passed |
| Tests de la función | `docker compose exec backend pytest -q apps/assets` | 75 passed |
| Suite completa | `docker compose exec backend pytest -q` | 588 passed (513 previos) |
| Estilo y formato | `docker compose exec backend sh -c "ruff check . && ruff format --check ."` | Sin incidencias; 82 ficheros formateados |
| Django | `manage.py check` y `manage.py makemigrations --check --dry-run` | Sin incidencias; no hay cambios |

### Lo observado
| Comprobación | Observado |
|---|---|
| Límites de la coordenada | (90, 0), (−90, 0), (0, 180) y (0, −180) dan un valor finito; ninguno da `projection_failed` |
| Un ulp fuera de cada límite | Se rechazan con `coordinate_invalid` |
| Coste de una llamada | 0,448 ms de media en 200 llamadas (Madrid, radio 1000), con sus dos transformaciones y sus SRS creadas en cada una; cierra la afirmación «del orden del milisegundo» del plan |
| Contraste de los 9 centros literales con la fórmula LAEA | Desviación máxima 0,0438 m (Madrid, 2000); el resto entre 0,0119 m y 0,0425 m |

Detalle del contraste: la desviación es la distancia, en la proyección, entre la fórmula LAEA aplicada al centro publicado (ya redondeado a 6 decimales) y el centro de la celda localizada con la misma fórmula, sin GDAL. Los centros se calcularon una vez con GDAL en un script fuera del repositorio.

| Punto | 500 m | 1000 m | 2000 m |
|---|---|---|---|
| Madrid | 0,0119 | 0,0386 | 0,0438 |
| Las Palmas | 0,0312 | 0,0425 | 0,0422 |
| Palma | 0,0142 | 0,0147 | 0,0377 |

### Pruebas de mecanismo
Mutaciones sobre `location.py`, que es un fichero nuevo de la tarea, restauradas en el mismo comando. sha256 de `location.py`, de los ficheros de `tests/` y de `base.py` idéntico antes y después.

| Mutación | Tests que fallan |
|---|---|
| `PUBLIC_DECIMALS = 5` | `test_the_cell_centre_matches_its_reference` (9) |
| `(ceil(x / r) - 0.5) * r` en vez de `(floor(x / r) + 0.5) * r` | `test_a_point_on_the_lower_left_border_belongs_to_the_upper_right_cell` (3), y ningún otro |
| Quitar la comprobación de finito de `_transform_or_none` | `test_a_non_finite_projection_fails_without_a_value` (2: el de `_project` y el de `_unproject`) |
| Quitar la exclusión de `bool` en la coordenada | `test_an_invalid_coordinate_fails_without_a_value` (2: `True` y `False`) |
| Quitar `isinstance(radius, int)` | `test_an_invalid_radius_fails_without_a_value` (1: `500.0`) |
| Quitar el `try` del `OverflowError` | `test_an_invalid_coordinate_fails_without_a_value` (2: `10**400` en latitud y en longitud) |
| `<` en vez de `<=` en el rango de la coordenada | `test_the_coordinate_limits_are_included` (4) |

### Límites
- Los tests de propiedades usan la propia proyección para localizar la celda del punto. La independencia la dan los 9 centros literales, contrastados con la fórmula LAEA, y las comprobaciones de plataforma.
- RF-26 y RF-27 se verifican por muestreo (9 puntos de referencia, las 4 esquinas de la caja, 24 puntos junto a bordes de celda y 200 aleatorios), no se demuestran para todos los puntos de la caja.
- Margen medido con la misma muestra (237 puntos) y la misma consulta de los tests, con un `SELECT` de solo lectura sobre literales y sin cambiar ningún test. Los tres radios dan prácticamente lo mismo:

| Radio | RF-26: máximo de distancia / radio | RF-27: mínimo de lado / radio | RF-27: máximo de lado / radio |
|---|---|---|---|
| 500 m | 0,7324 en (28,141589; −15,421745), junto a una esquina de celda en Las Palmas | 0,9788 en la esquina (27,5; 5,0), lado inferior | 1,0218 en la misma esquina, lado izquierdo |
| 1000 m | 0,7323 en (28,118337; −15,435930), junto a una esquina de celda en Las Palmas | 0,9788 en la esquina (27,5; 5,0), lado inferior | 1,0218 en la misma esquina, lado izquierdo |
| 2000 m | 0,7324 en (28,118337; −15,435930), junto a una esquina de celda en Las Palmas | 0,9788 en la esquina (27,5; 5,0), lado inferior | 1,0218 en la misma esquina, lado izquierdo |

  Los márgenes sobre la muestra son de 2,9 puntos porcentuales frente al límite inferior de RF-27 (95 %) y de 2,8 frente al superior (105 %), y de 0,27 × radio frente al límite de RF-26. Son los de estos 237 puntos, no los de toda la caja.

## Reglas de campos (T5)
Fecha: 2026-10-27 · Ficheros: `backend/apps/assets/rules.py` y `backend/apps/assets/tests/test_rules.py`.

| Comprobación | Orden | Resultado |
|---|---|---|
| Rojo previo | `docker compose exec backend pytest -q apps/assets/tests/test_rules.py` sin `rules.py` | `ModuleNotFoundError: No module named 'apps.assets.rules'` al recoger el fichero |
| Recuento previo | `docker compose exec backend pytest -q --ignore=apps/assets/tests/test_rules.py` | 588 passed |
| Tests de las reglas | `docker compose exec backend pytest -q apps/assets/tests/test_rules.py` | 212 passed |
| Suite completa | `docker compose exec backend pytest -q` | 800 passed (588 previos) |
| Estilo y formato | `docker compose exec backend sh -c "ruff check . && ruff format --check ."` | Sin incidencias; 84 ficheros formateados |
| Django | `manage.py check` y `manage.py makemigrations --check --dry-run` | Sin incidencias; no hay cambios |

### Lo observado
| Comprobación | Observado |
|---|---|
| Independencia | `rules.py` solo importa `apps.assets.location` (radios y límites de latitud y longitud) y `apps.core.text`; no importa modelos y sus tests no llevan `django_db` |
| Caracteres invisibles en los tests | Un escaneo por categoría Unicode de `test_rules.py` no encuentra ningún carácter no ASCII ni invisible literal; todos se escriben con `chr()` |
| Precio canónico | `12.340` da `12.34`, `+5` da `5.00` y `007.50` da `7.50`; `.5` da `0.50` y `5.` da `5.00` |
| Control que es espacio en el borde | `chr(0x1F)` y `chr(0x0B)` al principio o al final se recortan y no se rechazan; en medio del texto sí se rechazan |
| Códigos acumulados | `0.001` y `100000.123` llevan `price_out_of_range` y `price_too_precise`; un título con varios problemas los lleva todos, en el orden control, formato, corto y largo |

### Pruebas de mecanismo
Mutaciones sobre `rules.py`, que es un fichero nuevo de la tarea, restauradas en el mismo comando. sha256 de `rules.py` (`7c9680fdc0b1`), de `location.py` y de los ficheros de `tests/` idéntico antes y después.

| Mutación | Tests que fallan |
|---|---|
| La unión de ancho cero cuenta como visible (el predicado de formato en `_visible_length`) | `test_a_title_with_one_problem_gets_that_code` (2: solo uniones y «a» más dos uniones) |
| `\d` en vez de `[0-9]` en `PRICE_PATTERN` | `test_a_price_that_is_not_a_plain_decimal_is_invalid` (1: el dígito `chr(0x661)`) |
| Contar los ceros finales (sin `rstrip("0")`) | `test_a_valid_price_is_returned_with_two_decimals` (2: `12.340` como texto y como `Decimal`) |
| Devolver el precio sin `quantize` | `test_a_valid_price_is_returned_with_two_decimals` (7) |
| `<` en vez de `<=` en `_inside` | `test_a_point_inside_the_coherence_box_is_accepted` (4) y `test_the_range_limits_are_included_and_fall_to_the_box_check` (4) |
| Radio sin `isinstance(int)` | `test_any_other_privacy_radius_is_invalid` (2: `500.0` y `Decimal(500)`) |
| Referencia sin excluir `bool` | `test_an_invalid_reference_gets_the_code_of_its_field` (3: `True`, uno por campo) |
| Coordenada sin excluir `bool` | `test_a_coordinate_that_is_not_a_finite_number_is_invalid` (2: `True` y `False`) |
| La descripción cuenta visibles en lugar de puntos de código | `test_a_description_counts_code_points_and_not_visible_characters` (1) |
| Sin normalizar a NFC | `test_a_title_is_normalised_before_it_is_measured` (1) y `test_a_description_is_returned_trimmed_and_normalised` (1) |
| La unión de ancho cero cuenta como carácter de formato | `test_a_composed_emoji_counts_each_emoji_and_not_the_joiners` (1), `test_a_description_admits_a_composed_emoji` (1) y `test_a_title_with_one_problem_gets_that_code` (2) |
| La descripción no admite sus controles (`_without`) | `test_a_description_admits_line_breaks_and_tabs` (2) |
| Sin la comprobación de sustitutos sueltos en `_clean_text` | `test_a_title_that_is_not_valid_text_is_invalid` (1) y `test_a_description_that_is_not_valid_text_is_invalid` (1) |
| Sin la comprobación de tipo en `clean_price` | `test_a_price_that_is_not_a_plain_decimal_is_invalid` (2: el `float` `0.1` y el `int` `5`, porque `str()` de ambos pasaría el patrón) |

### Límites
- Las reglas dejan fuera lo que decide el servicio: qué significa «no indicado» (`*_required`), la existencia del propietario y de la categoría, y RF-39. Esas partes se cubren en T7 y T8.
- Un carácter invisible que no es espacio, ni de control ni de formato (por ejemplo U+3164 o U+2800) cuenta como visible en el título. Es un riesgo aceptado de la spec.
- `.5` y `5.` se aceptan como precios porque el patrón los admite. Son un riesgo aceptado de la spec, junto a `+5` y `007.50`, y los fijan tests.

## Modelo de bien (T6)
Fecha: 2026-10-27 · Ficheros: `backend/apps/assets/models.py`, `backend/apps/assets/migrations/0001_initial.py` y, en `backend/apps/assets/tests/`, `conftest.py` (fixtures `owner`, `category` y `make_asset`), `test_models.py` y `test_architecture.py`.

| Comprobación | Orden | Resultado |
|---|---|---|
| Rojo previo | `docker compose exec backend pytest -q apps/assets/tests/test_models.py apps/assets/tests/test_architecture.py` sin `models.py` | `ModuleNotFoundError: No module named 'apps.assets.models'` al cargar `conftest.py` |
| Recuento previo | `docker compose exec backend pytest -q` | 800 passed |
| Sin migración | las mismas dos rutas con `models.py` y sin migración | 1 failed, 11 passed y 28 errors: los tests de BD no encuentran la tabla y el de arquitectura no encuentra la migración |
| Dry-run | `docker compose exec backend python manage.py makemigrations assets --dry-run -v 3` | Una sola operación, `Create model Asset`, con 9 CHECK, 2 FK y los dos campos de ubicación; ninguna otra app |
| Tests de `apps/assets` | `docker compose exec backend pytest -q --create-db apps/assets` | 327 passed (75 de ubicación, 212 de reglas y 40 nuevos) |
| Suite completa, BD de test recreada | `docker compose exec backend pytest -q --create-db` | 840 passed (800 previos) |
| Estilo y formato | `docker compose exec backend sh -c "ruff check . && ruff format --check ."` | Sin incidencias; 89 ficheros formateados |
| Django | `manage.py check` y `manage.py makemigrations --check --dry-run` | Sin incidencias; no hay cambios |
| Dependencias | `git diff dev --stat -- backend/requirements*.txt` | Vacío |

### Migración
La migración se generó con `docker compose exec -u "$(id -u)" backend python manage.py makemigrations assets`. Se corrigió a mano la dependencia `("categories", "0002_seed_categories")` por `("categories", "0001_initial")`, conservando `swappable_dependency(settings.AUTH_USER_MODEL)`, y se pasó `ruff format`. `migrate` no se ha ejecutado en la BD de desarrollo.

`sqlmigrate assets 0001` (solo lectura) muestra:
- `CREATE TABLE "assets_asset"` con todas las columnas `NOT NULL`, `price numeric(8, 2)`, `exact_location` y `public_location` como `geography(POINT,4326)` y los nueve CHECK con su nombre;
- `LENGTH("title") BETWEEN 3 AND 100`, `LENGTH("description") BETWEEN 20 AND 2000` y `"price" BETWEEN 0.01 AND 99999.99`;
- los CHECK de ubicación como `NOT (ST_IsEmpty((col)::geometry(GEOMETRY,4326))) AND ST_X(…) BETWEEN -180.0 AND 180.0 AND ST_Y(…) BETWEEN -90.0 AND 90.0`, que son «coordenadas finitas» y no un rango;
- las dos FK `DEFERRABLE INITIALLY DEFERRED`: `assets_asset_owner_id_23c9aaf7_fk_users_user_id` y `assets_asset_category_id_b30c6baf_fk_categories_category_id` (nombres anotados para `CONSTRAINT_CODES`);
- un índice GiST solo sobre `public_location` (`assets_asset_public_location_bccabc5d_id`) y los dos índices B-tree que Django crea por defecto sobre `category_id` y `owner_id`.

### Lo cerrado de las afirmaciones no verificadas
| Afirmación | Observado |
|---|---|
| La forma de la expresión del CHECK | `Cast`, `IsEmpty`, `Func` y `Range` compilan y se serializan en la migración; `title__length` no existe en `TextField`, así que el CHECK usa `Length("title")` |
| `char_length` cuenta puntos de código | Un título de 100 emojis (400 bytes) se acepta y uno de 101 se rechaza con `assets_asset_title_length` |
| NaN y ubicación vacía a través del adaptador de GEOS de Django | El ORM los envía sin rechazarlos y los CHECK los rechazan por su nombre, en la exacta y en la pública; no hizo falta el SQL crudo |
| Latitud 91 y longitud 181 a través del ORM | No dan error y se leen ajustadas a (−179, 89), en las dos ubicaciones |

### Pruebas de mecanismo
Mutaciones sobre `models.py` y sobre `0001_initial.py`, ficheros nuevos de la tarea, restauradas en el mismo comando. Las dos de la migración se ejecutaron con `--create-db`, y se hizo una pasada final de la suite completa con `--create-db` tras restaurar. sha256 de `models.py` (`34c1ce00fcb6`) y de la migración (`107d46d41a45`), y de `location.py`, `rules.py` y los ficheros de `tests/`, idéntico antes y después.

| Mutación | Tests que fallan |
|---|---|
| `__str__` que añade la ubicación exacta | `test_str_and_repr_show_the_title_and_the_id_and_no_coordinates` (1) |
| `on_delete=CASCADE` en el propietario | `test_deleting_an_owner_with_assets_is_protected` y `test_foreign_keys_protect_and_have_no_reverse_accessor[owner-User]` |
| `on_delete=CASCADE` en la categoría | `test_deleting_a_category_with_assets_is_protected` y `test_foreign_keys_protect_and_have_no_reverse_accessor[category-Category]` |
| Sin `NOT ST_IsEmpty` en el CHECK de la exacta (migración) | `test_a_non_finite_or_empty_location_is_rejected_by_name[empty-exact_location-…]` (1) |
| Sin el rango de `ST_X` y `ST_Y` en el CHECK de la pública (migración) | `test_a_non_finite_or_empty_location_is_rejected_by_name[nan_latitude-public_location-…]` y `[nan_longitude-public_location-…]` |

### Límites
- Los tests de BD no usan `full_clean`: los bienes no pasan por la validación de modelos de Django, que consultaría la BD para cada CHECK. La validación es la de `rules.py` (T5) y, después, el servicio (T7).
- Los CHECK no repiten el mínimo de caracteres visibles del título: la BD solo cuenta puntos de código.
- La migración congela los límites como literales. Cambiar una constante de `rules.py` o `location.py` exige una migración nueva, y `makemigrations --check` lo detecta.

## Alta de bienes (T7)
Fecha: 2026-10-27 · Ficheros: `backend/apps/assets/services.py`, y en `backend/apps/assets/tests/` `conftest.py` (fixture `creation_arguments`) y `test_create.py`.

| Comprobación | Orden | Resultado |
|---|---|---|
| Rojo previo | `docker compose exec backend pytest -q apps/assets/tests/test_create.py` sin `services.py` | `ModuleNotFoundError: No module named 'apps.assets.services'` al recoger el fichero |
| Recuento previo | `docker compose exec backend pytest -q` | 840 passed |
| Tests del alta | `docker compose exec backend pytest -q apps/assets/tests/test_create.py` | 67 passed |
| Suite completa, BD de test recreada | `docker compose exec backend pytest -q --create-db` | 907 passed (840 previos) |
| Estilo y formato | `docker compose exec backend sh -c "ruff check . && ruff format --check ."` | Sin incidencias; 91 ficheros formateados |
| Django | `manage.py check` y `manage.py makemigrations --check --dry-run` | Sin incidencias; no hay cambios |
| Dependencias | `git diff dev --stat -- backend/requirements*.txt` | Vacío |

### Lo observado
| Comprobación | Observado |
|---|---|
| Ubicación pública | Para los tres radios, la pública guardada es igual a `approximate_location(exacta, radio)` y distinta de la exacta, tanto en el bien devuelto como en el leído de la BD |
| Fechas | Con `now` en UTC+2, `created_at` y `updated_at` valen `now` y llegan con desplazamiento UTC 0 en el bien devuelto y en el leído |
| Errores de forma | Se devuelven todos a la vez, sin ninguna consulta a la BD (`django_assert_num_queries(0)`) y sin crear filas |
| Existencia | Un propietario o una categoría inexistentes, o los dos, dan `owner_not_found` y `category_not_found` y no crean filas |
| FK con la comprobación de existencia anulada | La violación de la FK llega como `owner_not_found` o `category_not_found` por la comprobación forzada de `run_guarded`, con `__cause__` y `__context__` a `None` |
| CHECK con una regla parcheada | `assets_asset_price_range` llega como `price_out_of_range`, sin causa ni contexto, y la conexión sigue usable |
| Restricción de la pública | No se traduce a propósito: sale `{"__all__": ["constraint_violated"]}` |
| Aproximación fallida | Sale `{"__all__": ["approximation_failed"]}`, sin fila y sin causa ni contexto |
| Errores de programación | `public_location=`, `exact_location=`, `id=`, `pk=`, `created_at=`, `updated_at=`, un objeto `owner=` o `category=` y los argumentos posicionales dan `TypeError`; el mensaje nombra el argumento y no contiene las coordenadas. `now` ausente da `TypeError`; `now` naive, `None`, texto o número dan `ValueError("now_not_aware")` sin consultar la BD |
| Catálogo | `ERROR_CODES` es el conjunto de 33 códigos de la tabla del plan que puede lanzar el alta; los tres de la modificación (`privacy_radius_locked`, `location_locked` y `asset_not_found`) los añade T8 |

### Pruebas de mecanismo
Seis mutaciones sobre `services.py`, que es un fichero nuevo de la tarea, restauradas en el mismo comando. Las dos que afectan a `run_guarded` (`apps/core/db.py`, de T3 y fuera del alcance) se hicieron sin editar nada del repositorio: con un plugin de pytest de usar y tirar escrito en el `/tmp` del contenedor, cargado con `pytest -p` y borrado después. sha256 de `services.py` (`0569632373e8`), de `core/db.py` (`c2099e7bed17`), de `models.py`, `rules.py`, `location.py`, la migración y los ficheros de `tests/` idéntico antes y después.

| Mutación | Tests que fallan |
|---|---|
| La pública es la exacta | `test_the_public_location_is_derived_from_the_exact_one` (3) y `test_a_violation_of_the_public_location_is_an_unmapped_constraint` (1) |
| `raise` dentro del `except` en `_public_location` | `test_a_failed_approximation_is_reported_and_nothing_is_created` (1: la causa y el contexto) |
| El valor por defecto también para `None` | `test_an_explicit_none_does_not_take_the_default` (3: moneda, radio y estado) |
| Sin la comprobación de zona horaria de `now` | `test_a_now_without_a_time_zone_is_a_programming_error` (1: el naive) |
| Estado permitido al crear como al modificar | `test_an_invalid_field_gets_its_code_without_touching_the_database` (1: `active` al crear) y `test_several_invalid_fields_are_reported_together` (1) |
| Título sin validar ni normalizar | `test_text_and_price_are_stored_normalised` (1), `test_an_invalid_field_gets_its_code_without_touching_the_database` (2) y `test_several_invalid_fields_are_reported_together` (1) |
| `run_guarded` sin la comprobación forzada (plugin) | `test_a_foreign_key_violation_is_translated_by_the_forced_check` (2), más 2 errores de limpieza de pytest-django por las FK que quedan pendientes |
| `run_guarded` que lanza con `from exc` dentro del `except` (plugin) | `test_a_foreign_key_violation_is_translated_by_the_forced_check` (2), `test_a_check_violation_is_translated_without_the_original_error` (1) y `test_a_violation_of_the_public_location_is_an_unmapped_constraint` (1) |

### Límites
- La mutación «título sin validar ni normalizar» es más amplia que «sin normalizar»: el título solo se normaliza dentro de su regla (`clean_title`), así que la forma de romper la normalización desde el servicio es saltarse la regla entera.
- La restricción de la ubicación pública no se traduce: si salta, es un fallo del servicio y no una entrada del usuario.
- `ERROR_CODES` crece por tarea: T8 añade los códigos de la modificación y su test.
- Los errores de la capa de reglas, las coordenadas de los mensajes y los registros de log se prueban en T9 (`test_leaks.py`); aquí solo se comprueba que ni el `TypeError` ni el `DomainValidationError` incluyen coordenadas.

## Modificación de bienes (T8)
Fecha: 2026-10-27 · Ficheros: `backend/apps/assets/services.py`, y en `backend/apps/assets/tests/` `conftest.py` (fixture `stored_asset`), `test_update.py`, `test_concurrency.py` y `test_create.py` (catálogo).

| Comprobación | Orden | Resultado |
|---|---|---|
| Rojo previo | `docker compose exec backend pytest -q apps/assets/tests/test_update.py apps/assets/tests/test_concurrency.py` sin `update_asset` | `ImportError: cannot import name 'update_asset' from 'apps.assets.services'` al recoger los dos ficheros |
| Rojo previo del catálogo | `docker compose exec backend pytest -q apps/assets/tests/test_create.py` | 1 failed, 66 passed: faltan `asset_not_found`, `location_locked` y `privacy_radius_locked` |
| Recuento previo | `docker compose exec backend pytest -q` | 907 passed |
| Tests de la modificación | `docker compose exec backend pytest -q apps/assets/tests/test_update.py apps/assets/tests/test_concurrency.py apps/assets/tests/test_create.py` | 157 passed |
| Suite completa | `docker compose exec backend pytest -q` | 997 passed (907 previos y 90 nuevos: 86 de `test_update.py` y 4 de `test_concurrency.py`) |
| Estilo y formato | `docker compose exec backend sh -c "ruff check . && ruff format --check ."` | Sin incidencias; 93 ficheros formateados |
| Django | `manage.py check` y `manage.py makemigrations --check --dry-run` | Sin incidencias; no hay cambios |
| Dependencias | `git diff dev --stat -- backend/requirements*.txt` | Vacío |

### Lo observado
| Comprobación | Observado |
|---|---|
| Fechas | Un cambio guarda `updated_at = now` en UTC (con `now` en UTC+2 llega con desplazamiento 0) y conserva `created_at` |
| Sin cambios | Sin argumentos, o con valores iguales a los guardados (`"12.340"`, `"  Taladro  "`, las mismas coordenadas, el mismo radio, el mismo estado), no se captura ningún `UPDATE` y la fila queda igual; activar un bien activo o pausar uno pausado tampoco escribe |
| Lo no indicado | Con el título cambiado, un bien activo de 2000 m conserva radio, estado y el resto de columnas |
| Errores de forma | Cada campo inválido da su código con 0 consultas y la fila intacta; `None` en un obligatorio da `*_required`, y en moneda, radio o estado `*_invalid`; una sola coordenada da `location_required`; los errores salen juntos |
| Estado | `deleted`, `Active` y `None` dan `status_invalid`; activar y pausar funcionan |
| Propietario y categoría | `owner_id=` da `TypeError` y el propietario no cambia; la categoría cambia a `kayak`; una inexistente da `category_not_found` y nada cambia |
| Errores de programación | `owner_id`, `public_location`, `exact_location`, `id`, `pk`, `created_at`, `updated_at`, `owner` y `category` dan `TypeError` sin coordenadas en el mensaje; los argumentos posicionales y la falta de `asset_id` o `now` también; `now` naive, `None`, texto o número dan `ValueError("now_not_aware")` con 0 consultas |
| `asset_not_found` | Un id inexistente lo da sin cambios; `True`, `"5"` y `0` lo dan con 0 consultas |
| Ubicación pública | Con el bien pausado, cambiar el radio (los tres) o mover la exacta deja la pública igual a `approximate_location(exacta, radio)`; tras una secuencia de seis modificaciones, cada pública guardada coincide con la derivada |
| Misma celda y D6 | Mover la exacta al centro de su celda no cambia la pública; cambiar título, precio y estado no llama a `approximate_location` (espía), y cambiar el radio sí, una vez |
| RF-39 y D7 | Con la fila intacta tras cada rechazo: activo y movido da `location_locked`; activo y otro radio, `privacy_radius_locked`; las dos cosas, los dos códigos; activo que se pausa y se mueve o cambia el radio, activado y movido o con otro radio, rechazados; con categoría inexistente salen `category_not_found` y `location_locked` juntos. Activo con los mismos valores y pausado con cambio se aceptan |
| Columnas | El `UPDATE` nombra solo lo cambiado más `updated_at`: título, precio, estado y categoría solos; `exact_location` y `public_location` al mover; `privacy_radius` y `public_location` al cambiar el radio |
| CHECK con una regla parcheada | `assets_asset_price_range` llega como `price_out_of_range`, sin causa ni contexto y sin cambios |
| Aproximación fallida | Sale `{"__all__": ["approximation_failed"]}`, sin causa ni contexto y sin cambios |
| Bloqueo (RF-35, D10 b) | Con `CaptureQueriesContext`, tanto al cambiar el título como al mover la exacta, la primera consulta sobre `assets_asset` es un `SELECT … FOR UPDATE` y va en orden `SAVEPOINT` < bloqueo < `UPDATE` < `RELEASE SAVEPOINT` |
| Catálogo | `ERROR_CODES` es ahora el conjunto de 36 códigos: los 33 del alta y los tres de la modificación |

### Pruebas de mecanismo
Seis mutaciones sobre `services.py`, que es un fichero nuevo de la tarea, aplicadas sobre el propio fichero y restauradas desde una copia en el mismo comando. sha256 de `services.py` (`05f4ef3e4e15`) idéntico antes y después; `core/db.py` y el resto de ficheros no se tocaron.

| Mutación | Tests que fallan |
|---|---|
| Sin `select_for_update` | `test_the_row_is_locked_before_anything_else_reads_the_asset` (2) y `test_the_update_comes_after_the_lock_in_the_same_transaction` (2) |
| Una lectura del bien antes del bloqueo | `test_the_row_is_locked_before_anything_else_reads_the_asset` (2) |
| La condición de bloqueo con el estado recibido en vez del guardado | `test_an_active_or_activated_asset_cannot_change_location_or_radius` (2: pausar y mover, pausar y cambiar el radio) |
| `save()` sin `update_fields` | `test_only_the_changed_columns_are_written` (6) |
| Sin la rama de D7 (solo el estado guardado) | `test_an_active_or_activated_asset_cannot_change_location_or_radius` (3: los activados) |
| Derivar la pública en cada modificación | `test_changing_something_else_does_not_derive_the_public_location` (1) y `test_only_the_changed_columns_are_written` (4: título, precio, estado y categoría) |

### Límites
- El bloqueo se verifica por el orden del SQL y no por su efecto con dos conexiones (D10 b): los tests no prueban que una segunda modificación espere de verdad.
- Un bien borrado mientras otra modificación espera el bloqueo da `asset_not_found` por la misma ruta que un id inexistente (`first()` devuelve `None`); no hay un test con el borrado concurrente.
- La mutación «derivar en cada modificación» también hace fallar el test de columnas, porque `public_location` entraría en el `UPDATE` de cambios que no tocan la ubicación.
- La parte de fugas de coordenadas en errores y registros (RF-37) se prueba en T9.

## Borrado, fugas y vía de escritura (T9)
Fecha: 2026-10-27 · Ficheros: en `backend/apps/assets/tests/`, `test_deletion.py`, `test_leaks.py` y `test_architecture.py` (ampliado), más `conftest.py` (`SENTINEL_LATITUDE`, `SENTINEL_LONGITUDE` y `coordinate_forms`, movidos desde `test_models.py`) y el import de `test_models.py`. Ningún fichero de producción cambia.

| Comprobación | Orden | Resultado |
|---|---|---|
| Rojo previo | No existe: la tarea solo añade tests y el código ya cumple. Lo que demuestra que los tests pueden fallar son las pruebas de mecanismo de más abajo | n/a |
| Recuento previo | `docker compose exec backend pytest -q` | 997 passed |
| Tests nuevos | `docker compose exec backend pytest -q apps/assets/tests/test_deletion.py apps/assets/tests/test_leaks.py apps/assets/tests/test_architecture.py` | 88 passed (3 de borrado, 59 de fugas y 26 de arquitectura, uno de ellos el del grafo de T6) |
| Suite completa, BD de test recreada | `docker compose exec backend pytest -q --create-db` | 1084 passed (997 previos y 87 nuevos) |
| Estilo y formato | `docker compose exec backend sh -c "ruff check . && ruff format --check ."` | Sin incidencias; 95 ficheros formateados |
| Django | `manage.py check` y `manage.py makemigrations --check --dry-run` | Sin incidencias; no hay cambios |
| Dependencias | `git diff dev --stat -- backend/requirements*.txt` | Vacío |
| Producción | `git diff --stat` sobre `services.py`, `models.py`, `location.py` y `rules.py` | Vacío |

### Lo observado
| Comprobación | Observado |
|---|---|
| RF-21 por SQL | `DELETE` del propietario o de la categoría de un bien, tras `SET CONSTRAINTS ALL IMMEDIATE` y dentro de `atomic`, da `IntegrityError` cuya causa nombra la FK del bien (`assets_asset_owner_id_…` y `assets_asset_category_id_…`); la fila y el bien siguen existiendo |
| RF-22 | Con un bien de `pool`, `migrate categories 0001_initial` dentro de `atomic` con `set_rollback(True)` da `ProtectedError`; quedan las once categorías, `0002` sigue registrada y el bien existe, dentro y fuera del bloque. Es la afirmación [NV] del plan: el estado histórico incluye `Asset` y `PROTECT` actúa |
| Formas buscadas (RF-37) | `coordinate_forms` da 22 formas por punto (18 si no se proyecta): repr, 3, 4, 5 y 6 decimales, EWKT, WKT, EWKB en mayúsculas y minúsculas, el hexadecimal little y big endian de cada `double`, y el este y el norte de EPSG:3035 en repr y al metro. Con 3 decimales una coordenada ya es más precisa que la celda de 500 m. Las formas cortas no chocan con ningún texto legítimo de los tests: la suite sigue en verde al añadirlas. La búsqueda no distingue mayúsculas |
| Control del detector | `assert_no_leak` falla con cada una de las 22 formas del centinela, tanto en el mensaje del error como en el log (44 casos), y no falla con un error y un log limpios (1). Con esto una forma que quedara vacía o no se buscara en un sitio no pasa en vacío |
| Sitios buscados | `str()`, `repr()`, `traceback.format_exception()`, `message_dict` y `caplog.text`, con el log a DEBUG en la raíz, en `django.contrib.gis` y en `psycopg`, y `connection.force_debug_cursor` activo. Se buscan la exacta, la pública derivada y, según el caso, la exacta de destino o la intercambiada |
| Casos sin fuga | Validación del alta y de la modificación, coordenadas intercambiadas, latitud fuera de rango, aproximación fallida en el servicio, `location_locked`, CHECK de la BD, la función por radio, por coordenada y por proyección (antípoda, con el `GDAL_ERROR` en el log), y el `ProtectedError` de propietario, categoría y reversión de la semilla |
| Causa y contexto | `DomainValidationError` y `ApproximationError` los tienen a `None` en todos los casos |
| Conexión usable | Tras el CHECK de la BD, `Asset.objects.count()` responde y vale 0 |
| RF-32 (AST) | Sobre `apps` y `config`, sin `migrations/` ni `tests/`: solo `services.py` obtiene `Asset` (por nombre o por el módulo `models`) y solo `services.py` obtiene `approximate_location` (por nombre o por el módulo `location`); nadie busca un modelo de `assets` con `get_model`; `models.py` no llama a ningún método de escritura (`selectors.py` aún no existe, y el test lo comprobaría si existiera); las funciones públicas de `services.py` son exactamente `create_asset` y `update_asset` |
| El detector | Tiene sus propios tests: ve `from … import Asset` (con alias y con `*`), `from apps.assets import models` (con y sin alias), `import apps.assets.models` (con y sin alias), y las dos formas relativas; no ve `AssetStatus` solo, otro módulo de `assets` ni `models` de otra app. Lo mismo para `location`. El escaneo comprueba que ve `models.py` y más de diez ficheros, y que detecta a `services.py` como importador conocido |

### Pruebas de mecanismo
Cinco mutaciones. Las cuatro primeras no editan ningún fichero versionado: tres con un plugin de pytest de usar y tirar en el `/tmp` del contenedor (`PYTHONPATH=/tmp/x:/app` y `-p`), borrado después, y la 3 con un módulo temporal sin versionar, borrado en el mismo comando. La 5 edita `test_leaks.py`, fichero nuevo de la tarea, con una copia aparte y restauración desde ella en el mismo comando. sha256 de los 11 ficheros implicados (`conftest.py`, los cuatro de tests, `models.py`, `services.py`, `location.py`, `assets.0001`, `categories.0002` y `settings/base.py`) idéntico antes y después. Tras la 4, `pytest -q --create-db` sin plugin: 1084 passed.

| Mutación | Tests que fallan |
|---|---|
| 1. `Asset.__str__` con la exacta | `test_str_and_repr_show_the_title_and_the_id_and_no_coordinates` (RF-17), y en `test_leaks.py` `test_the_text_of_an_asset_does_not_leak`, `test_deleting_the_owner_of_an_asset_does_not_leak` y `test_deleting_the_category_of_an_asset_does_not_leak` |
| 2. `django.db.backends` a DEBUG | `test_a_check_violation_does_not_leak_and_leaves_the_connection_usable` (1) |
| 3a. Módulo temporal con `from apps.assets.models import Asset` | `test_only_the_asset_modules_get_the_asset_model` (1) |
| 3b. Módulo temporal con `from apps.assets import models` | `test_only_the_asset_modules_get_the_asset_model` (1) |
| 3c. Módulo temporal con `from apps.assets import location` | `test_only_the_service_gets_the_approximation` (1) |
| 4. `assets.0001` depende de `categories.0002` (plugin, `--create-db`) | `test_the_asset_migration_does_not_depend_on_the_category_seed`, `test_reverting_the_seed_with_an_asset_is_rejected_and_deletes_nothing` (sin `ProtectedError`) y `test_reverting_the_seed_with_an_asset_does_not_leak` |
| 5. `assert_no_leak` sin mirar `caplog.text` | `test_the_detector_catches_every_form_in_every_place_it_looks` en su variante del log (22, una por forma) |

### Límites
- Mutación 2: solo falla el caso del CHECK porque es el único que llega a escribir coordenadas en un SQL; en los demás rechazos el servicio corta antes de la BD, o la consulta solo lleva identificadores.
- Mutación 1: la reversión de la semilla no falla, porque usa los modelos históricos de las migraciones, que no tienen el `__str__` del modelo real.
- El caso de proyección usa `projected=False`: el este y el norte del antípoda no se pueden calcular, porque `_project` falla.
- El AST no ve `importlib.import_module("…")` con un texto, ni `import apps.assets` seguido de acceso por atributo. Es el mismo tipo de riesgo aceptado que `RunSQL` y `loaddata` en D10.
- Regla de `approximate_location`: no figuraba en la Estrategia de tests de `plan.md`; sale de la segunda mitad de RF-32 («solo ellas calculan la ubicación pública») y se añadió con la aprobación del plan de T9.
- `related_name="+"` de `owner` y `category` ya lo vigila `test_models.py` desde T6, y no se repite aquí.
- El control del detector comprueba que `assert_no_leak` mira donde debe y que ninguna forma pasa en vacío, pero no que cada forma esté bien calculada: una forma incorrecta pero no vacía se detectaría a sí misma. Que las formas coincidan con lo que PostgreSQL escribe de verdad (`ST_AsHEXEWKB`, `ST_AsEWKT`) no se comprueba.
