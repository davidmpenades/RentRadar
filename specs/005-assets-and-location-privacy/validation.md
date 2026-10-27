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
- `.5` y `5.` se aceptan como precios porque el patrón los admite; la spec no los menciona. Los fijan tests.
