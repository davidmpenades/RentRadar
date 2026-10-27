# Tareas 005 — Bienes y privacidad de la ubicación
Requisitos previos:
- Rama `feature/005-assets-and-location-privacy`, creada desde `dev`.
- Spec aprobada; plan aprobado con D1 a D10 elegidas, D3 y D10 con los cambios de la aprobación.
- Puerta antes de T4:
  - `/sdd-change` aplicado con D1, D4 (b), D5, D6, D7, el cambio A de T1 (CHECK de coordenadas finitas) y D10 (b), con los resultados de T1 y T2;
  - si un resultado contradice el plan, el plan y estas tareas se corrigen antes de T4.
- La spec no se parte (decidido tras T2).

Antes de cada commit:
- `docker compose exec backend pytest -q` y `docker compose exec backend sh -c "ruff check . && ruff format --check ."` en verde.
- Si cambian modelos, también `docker compose exec backend python manage.py check` y `docker compose exec backend python manage.py makemigrations --check --dry-run`.
- El test se escribe primero y debe fallar por la razón esperada, que se anota.
- Las pruebas de mecanismo se hacen con mutaciones o tests temporales sin commitear, con el sha256 de los ficheros antes y después.

Prohibido sin OK explícito en ese momento: `migrate` en la BD de desarrollo, órdenes de git que descarten o reescriban cambios, push. Se pregunta antes de crear la migración de T6.

- [x] **T1. Comportamiento de PostgreSQL y PostGIS que el plan supone.** RF-5, RF-13, RF-36 (parte de BD); prepara RF-2, RF-22, RF-34, RF-35
  - Cómo se prueba (`apps/core/tests/test_database_platform.py`; cada test fija lo observado):
    1. Geography con latitud 91, longitud 181 y NaN, por texto y por WKB en parámetro: ¿falla (y con qué clase de error), ajusta con un NOTICE o guarda tal cual?
    2. `POINT EMPTY` en geography; `ST_IsEmpty` y `ST_Y` tras el cast a geometry.
    3. `100000::numeric(7,2)` da `DataError` sin el valor en el mensaje; `numeric(8,2)` lo admite.
    4. Las FK de Django son `DEFERRABLE INITIALLY DEFERRED` (`pg_constraint` de una FK existente de auth).
    5. Ida y vuelta EWKB por geography de `double` con 17 cifras: devuelve el mismo `float`.
    6. `connections.create_connection("default")` dentro de un test con `transaction=True` abre con el bloqueo de red, `current_database()` es la de test, solo ve las filas confirmadas y se cierra.
    7. `call_command("migrate", "categories", "0001_initial", verbosity=0)` dentro de `transaction.atomic()` con `set_rollback(True)`: dentro no queda la semilla, y al salir hay once categorías y `0002` registrada.
    8. `SET CONSTRAINTS ALL IMMEDIATE` seguido de `SET CONSTRAINTS ALL DEFERRED` dentro de un `atomic` anidado cuya FK violada lo revierte: ¿las restricciones quedan en diferidas al salir del savepoint?
  - Qué cambio dispara cada resultado:
    - 1 ajusta: `/sdd-change` A. En la BD, el rango lo garantiza el tipo geography, que ajusta; la BD solo exige ubicación no vacía y se quitan los CHECK de rango.
    - 1 falla con error de datos: `/sdd-change` A'. Rechazo de datos, no de integridad.
    - 1 guarda tal cual: sin cambio.
    - 2 rechaza EMPTY: `/sdd-change` B. El tipo garantiza la ubicación no vacía.
    - 5 no exacta: el plan compara tras la misma conversión, sin cambio de spec.
    - 6 falla: RF-35 se queda en D10 (b), solo con `CaptureQueriesContext`.
    - 7 falla: RF-22 pasa a `transaction=True`, `serialized_rollback` y `migrate` hacia delante en `finally`.
    - 8 no quedan en diferidas: `run_guarded` ejecuta `SET CONSTRAINTS ALL DEFERRED` tras la reversión, dentro de la transacción exterior.
  - Qué toca revisar: la tabla de resultados y el cambio de spec que propone cada uno.
  - Commit: `test(core): pin postgis behaviour assumed by assets`
  - Hecho cuando: los tests pasan y describen lo observado; `validation.md` tiene la sección "Plataforma" con fecha, orden y resultado; ningún fichero de producción cambia.

- [x] **T2. Comportamiento de GDAL y PROJ que el plan supone.** RF-24, RF-27, RF-31, RF-37 (preparación)
  - Cómo se prueba (`apps/core/tests/test_projection_platform.py`):
    1. Fija las versiones de GDAL y PROJ (avisan si cambia la imagen).
    2. Orden de ejes: Madrid en EPSG:4326 da x = Este e y = Norte en EPSG:3035, con valores de referencia para Madrid, Las Palmas y Palma calculados una vez.
    3. Contraste con la fórmula LAEA elipsoidal de la guía EPSG 7-2 (GRS80, φ0 = 52°, λ0 = 10°, FE = 4321000, FN = 3210000), escrita en el test: diferencia menor de 1 mm.
    4. (−52, −170) y puntos próximos: si dan una excepción, cuál es; si dan un valor, si es finito; y si el texto que GDAL escribe en `django.contrib.gis` contiene coordenadas.
    5. Medición sin commitear: tiempo de NFC sobre 8000 caracteres y sobre 2,5 MB de marcas combinantes alternas, y de `Decimal()` sobre 2,5 MB de dígitos.
  - Qué cambio dispara cada resultado:
    - 3 difiere: `/sdd-change` C. La entrada se toma como ETRS89 (EPSG:4258).
    - 4 con coordenadas en el log: sin cambio de spec; el plan decide entre una comprobación previa del dominio de la proyección o configurar `django.contrib.gis`, cambiando `test_logging.py`.
    - 4 sin fallo en ningún punto: RF-31 se cubre solo con la sustitución por infinito.
    - 5 superlineal: D4 (a), con tope en el `/sdd-change`; lineal: D4 (b).
  - Qué toca revisar: la fórmula de contraste y la tabla de resultados.
  - Commit: `test(core): pin gdal projection behaviour`
  - Hecho cuando: los tests pasan; `validation.md` recoge los resultados y las mediciones; está redactado el `/sdd-change` de la puerta; se ha decidido si la spec se parte en 005a y 005b.

- [x] **T3. Guardado protegido en `apps/core`.** RF-38
  - Cómo se prueba:
    - Se anota el recuento de la suite antes del cambio.
    - `core/tests/test_db.py`:
      - el bloque entero va en atomic;
      - nombre conocido da su código; desconocido o vacío da `constraint_violated`;
      - el `DatabaseError` se propaga;
      - un `DomainValidationError` lanzado dentro hace rollback y sale con `__context__` a `None`;
      - se devuelve el resultado del bloque;
      - una FK violada dentro del bloque salta dentro del `try` y se traduce;
      - tras el bloque, una FK violada posterior en la misma transacción exterior no salta hasta pedirlo: las restricciones están en diferidas.
    - Los dos tests de `_codes_for_constraint` pasan a core.
    - Siguen sin cambios: `users/tests/test_services.py:174-185` y `:397-411`, y `categories/tests/test_services.py:340-350` y `:359-369`.
    - Mecanismo: capturar fuera del atomic hace fallar el test de conexión usable; quitar `or ""` hace fallar el de sin diagnóstico; quitar `SET CONSTRAINTS ALL DEFERRED` hace fallar el de restricciones diferidas; quitar `SET CONSTRAINTS ALL IMMEDIATE` hace fallar el de la FK violada dentro del bloque.
  - Qué toca revisar: que los `raise` siguen fuera del `except`; que `change_user_email` restaura el email igual que antes; el orden de las dos sentencias `SET CONSTRAINTS` y que van dentro del `atomic`; que el comentario de `run_guarded` dice que, al terminar bien, deja las restricciones diferidas sea cual sea el modo de entrada (y que tras una reversión no ejecuta `ALL DEFERRED`, porque el savepoint restaura el modo de entrada).
  - Commit: `refactor(core): extract guarded database write`
  - Hecho cuando: el recuento cuadra (más los nuevos de core, menos los dos movidos); ruff en verde; no queda ninguna copia de `_save_guarded`; la suite de users y categories pasa sin cambios, salvo los dos tests movidos.

- [ ] **T4. App de bienes y función de aproximación.** RF-23, RF-24, RF-25, RF-26, RF-27, RF-28, RF-29, RF-30, RF-31
  - Cómo se prueba:
    - `apps/assets` con `AssetsConfig` en `INSTALLED_APPS` y `docker compose restart backend`.
    - `test_location.py`: muestra con las cuatro esquinas, Canarias, Baleares, bordes y esquinas de celda y `random.Random(5)`, para los tres radios; sin `django_db`. El antípoda (−52, −170), cuya `GDALException` es real (T2), da `projection_failed`.
    - `test_location_reference.py`: centros literales.
    - `test_location_geodesic.py`: `ST_Distance` sobre geography.
    - Mecanismo: `round` a 5 decimales hace fallar la referencia; `(ceil(x / r) - 0.5) * r` en vez de `(floor(x / r) + 0.5) * r` mete el borde superior en la celda y hace fallar solo el test del borde; quitar la comprobación de finito de `_transform_or_none` hace fallar los dos casos de infinito.
  - Qué toca revisar:
    - en `location.py`, que `bool` se descarta antes que `int` en la coordenada;
    - `floor` y el `+ 0.5`;
    - la comprobación de finito tras cada transformación;
    - el redondeo a 6 decimales;
    - que `ApproximationError` se lanza fuera del `except` y sin valores;
    - que nada de GDAL se guarda a nivel de módulo.
  - Commit: `feat(assets): add location approximation function`
  - Hecho cuando: los tests de RF-23 a RF-31 pasan; `manage.py check` y `makemigrations --check --dry-run` en verde (la app aún no tiene modelos).

- [ ] **T5. Reglas de los campos del bien.** RF-3, RF-4, RF-5, RF-7, RF-8, RF-10, RF-12, RF-13, RF-14
  - Cómo se prueba:
    - `test_rules.py`, con los casos de la Estrategia de tests; los invisibles se escriben con `chr()`.
    - Mecanismo: contar visibles sin excluir U+200D; patrón del precio con `\d`; contar los ceros finales; comparar la caja con `<` en vez de `<=`; radio sin excluir `bool`. Cada mutación hace fallar su test.
  - Qué toca revisar, línea a línea:
    - el orden tipo → sustituto → recorte → NFC, sin tope bruto del texto recibido;
    - la definición de carácter visible;
    - los Cc admitidos en la descripción;
    - `PRICE_PATTERN` y el recuento de decimales;
    - el orden tipo → `float()` → finito → rango → caja en las coordenadas;
    - que `bool` se descarta antes que `int`.
  - Commit: `feat(assets): add asset field rules`
  - Hecho cuando: los tests pasan; las reglas no importan modelos ni tocan la BD.

- [ ] **T6. Modelo de bien y migración inicial.** RF-1, RF-3 a RF-13 (parte de BD), RF-15, RF-17, RF-21 y RF-22 (parte del ORM), RF-36
  - Cómo se prueba:
    - `test_models.py`, en rojo antes del modelo:
      - campos;
      - sin `auto_now`;
      - `str()` y `repr()`;
      - cada CHECK con `save()` directo dentro de `atomic` espera `IntegrityError` con su nombre exacto;
      - coordenada NaN (latitud o longitud) en la exacta y en la pública, y exacta vacía, dan `IntegrityError`; latitud 91 y longitud 181 no dan error, porque el tipo las ajusta;
      - pública vacía y nula;
      - `ProtectedError` al borrar un usuario y una categoría con bienes.
    - `test_architecture.py`: la migración no depende de `categories.0002` (grafo).
    - `sqlmigrate assets 0001` revisado.
  - Qué toca revisar:
    - `PROTECT` y `related_name="+"`;
    - `TextField` con CHECK;
    - `max_digits=8`;
    - `spatial_index=False` en la exacta;
    - la ausencia de `default=`;
    - el SQL de los CHECK (cast, `NOT ST_IsEmpty` y los límites de `ST_X` y `ST_Y`, que son «coordenadas finitas» y no un rango);
    - la dependencia editada a `categories.0001`.
  - Commit: `feat(assets): add asset model`
  - Hecho cuando: `pytest -q`, ruff, `manage.py check` y `makemigrations --check --dry-run` en verde; los nombres de las FK están anotados para `CONSTRAINT_CODES`.

- [ ] **T7. Alta de bienes.** RF-1, RF-2, RF-6, RF-9, RF-11, RF-12, RF-15, RF-33, RF-38
  - Cómo se prueba:
    - `test_create.py`, con los casos de la Estrategia de tests;
    - el FK traducido con la comprobación de existencia anulada;
    - el CHECK traducido con una regla parcheada;
    - `public_location=` da `TypeError`;
    - `now` sin zona horaria da `ValueError`;
    - `ERROR_CODES` coincide con la tabla del plan.
    - Mecanismo: sin la comprobación forzada de `run_guarded` falla el test de la FK; con `from exc` falla el de causa y contexto.
  - Qué toca revisar:
    - que la comprobación forzada vive en `run_guarded` y el servicio no ejecuta `SET CONSTRAINTS`;
    - que los valores por defecto solo se aplican a `_UNSET` y no a `None`;
    - que la pública sale de la función;
    - que el `raise` está fuera del `except`.
  - Commit: `feat(assets): add asset creation service`
  - Hecho cuando: los tests de RF-1, RF-2, RF-6, RF-9, RF-11, RF-12, RF-15, RF-33 y RF-38 pasan; `pytest -q` y ruff en verde.

- [ ] **T8. Modificación de bienes con bloqueo de fila.** RF-12, RF-16, RF-18, RF-19, RF-20, RF-33, RF-34, RF-35, RF-39
  - Cómo se prueba:
    - `test_update.py`, con los casos de la Estrategia de tests, incluidos D6 (espía en `approximate_location`) y D7.
    - `test_concurrency.py`: orden de consultas con `CaptureQueriesContext` (D10 (b), sin segunda conexión): el primer SQL sobre `assets_asset` es `SELECT … FOR UPDATE`, antes de cualquier otra lectura del bien, y el UPDATE va después dentro del mismo atomic.
    - Mecanismo:
      - sin `select_for_update` falla el test de RF-35;
      - con una lectura del bien antes del bloqueo, falla el test de RF-35;
      - comparar con el estado recibido en vez del guardado hace fallar el de pausar y mover;
      - guardar sin `update_fields` hace fallar el de no pisar columnas.
  - Qué toca revisar:
    - que el bloqueo es la primera lectura del bien;
    - las comparaciones de igualdad exacta;
    - la condición de RF-39 y de D7 sobre el estado guardado;
    - la rama sin cambios;
    - la lista de `update_fields`;
    - que el bloqueo se verifica por su SQL y no por su efecto con dos conexiones (D10 (b)).
  - Commit: `feat(assets): add asset update service`
  - Hecho cuando: los tests pasan; `pytest -q` y ruff en verde.

- [ ] **T9. Borrado protegido completo, fugas y única vía de escritura.** RF-21, RF-22, RF-32, RF-37, RF-38
  - Cómo se prueba:
    - `test_deletion.py`: `DELETE` por SQL con `SET CONSTRAINTS ALL IMMEDIATE` y reversión real de la semilla con un bien, dentro de `atomic` con `set_rollback(True)` (T1), sin `transaction=True`.
    - `test_leaks.py`: los casos y las formas de la Estrategia de tests.
    - `test_architecture.py`: la regla AST.
    - Mecanismo:
      - `__str__` con la exacta hace fallar RF-17 y RF-37;
      - `django.db.backends` a DEBUG hace fallar `test_leaks`;
      - un módulo temporal que importa `Asset` hace fallar RF-32;
      - la dependencia de la migración puesta en `0002` hace fallar el test del grafo y el de la reversión.
  - Qué toca revisar: la lista de formas de las centinelas y las exclusiones del recorrido AST.
  - Commit: `test(assets): cover protected deletion, leaks and write path`
  - Hecho cuando: los tests pasan sin código de producción nuevo; si alguno exige código, se para y se revisa el plan.

- [ ] **T10. Validación y BD de desarrollo.** Todos
  - Cómo se prueba:
    1. Suite completa, ruff, `manage.py check` y `makemigrations --check --dry-run`.
    2. `git diff dev -- backend/requirements*.txt` vacío (RNF Dependencias).
    3. **Con OK en ese momento**, `migrate` en la BD de desarrollo; después `showmigrations assets categories`.
    4. `validation.md` RF por RF, con las pruebas de mecanismo de T3 a T9 y los riesgos aceptados del plan. Las de T3 no quedaron registradas en su commit: se repiten y se recogen aquí.
    5. `docs/architecture.md` con `core/db.py` y `assets`.
  - Qué toca revisar: el veredicto de `validation.md` y los riesgos aceptados que quedan anotados.
  - Commit: `docs(spec-005): record spec 005 validation`
  - Hecho cuando: cada RF de RF-1 a RF-39 tiene su test en verde; la BD de desarrollo tiene `assets.0001` aplicada; `validation.md` termina con un veredicto.
