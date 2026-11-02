# Validación — 006-public-map
Rama: `feature/006-public-map` · Entorno: Docker Compose, `postgis/postgis:18-3.6`, Django 5.2.18, psycopg 3.3.6, Python 3.13.16, pytest 9.1.1, ruff 0.16.10

## Identificador público (T2)
Fecha: 2026-11-02 · Ficheros: `backend/apps/assets/{models.py, migrations/0002_asset_public_id.py, migrations/0003_fill_asset_public_id.py, migrations/0004_alter_asset_public_id.py, tests/test_public_id.py, tests/test_models.py}`. `services.py` no cambia.

| Comprobación | Orden | Resultado |
|---|---|---|
| Suite completa con la BD de test recreada | `docker compose exec backend pytest -q --create-db` | 1197 passed (1177 previos) |
| Estilo y formato | `docker compose exec backend sh -c "ruff check . && ruff format --check ."` | Sin incidencias |
| Modelos y migraciones cuadran | `docker compose exec backend python manage.py makemigrations --check --dry-run` | No changes detected |
| SQL de las migraciones | `docker compose exec backend python manage.py sqlmigrate assets 0002`, `0003` y `0004` | Revisado (ver abajo) |

`migrate` no se ha ejecutado en la BD de desarrollo.

### Lo observado
| # | Comprobación | Observado |
|---|---|---|
| 1 | Nombre de la restricción única | `assets_asset_public_id_f569762c_uniq`, con hash porque la crea `AlterField`; no es `assets_asset_public_id_key`. El test lo fija |
| 2 | Origen del valor en `0004` | Es Django quien evalúa `uuid.uuid4` en Python, no PostgreSQL: `sqlmigrate` emite literales (`SET DEFAULT '…'::uuid` y `UPDATE … SET "public_id" = '…'::uuid WHERE "public_id" IS NULL`), y cada sentencia lleva un UUID distinto. Con filas nulas, ese `UPDATE` daría el mismo UUID a todas; no ocurre porque `0003` ya las rellenó |
| 3 | `0003` | `RunPython`: no se puede escribir como SQL, ni hacia delante ni hacia atrás. El relleno hace un `UPDATE` por fila con `uuid.uuid4()`; el `reverse_code` hace un único `UPDATE … SET public_id = NULL` y no borra bienes |
| 4 | Restricciones de la columna en PostgreSQL 18 | `pg_constraint` lista también el NOT NULL (`assets_asset_public_id_not_null`, tipo `n`); el test filtra por tipo `u` |

### Pruebas de mecanismo
Mutaciones sobre los propios ficheros, restaurados desde una copia hecha antes. sha256 idéntico antes y después en las seis; cada ejecución con `pytest --create-db`.

| Fichero | Mutación | Tests que fallan |
|---|---|---|
| `models.py` | `uuid.uuid4` → `uuid.uuid1` | 5: `test_a_created_asset_gets_a_version_4_uuid_that_is_not_its_primary_key`, `test_an_asset_built_directly_also_gets_a_version_4_uuid`, `test_the_field_is_a_required_unique_uuid_generated_by_uuid4`, `test_no_field_is_nullable_or_has_a_default`, `test_models_have_no_pending_migrations` |
| `0003_fill_asset_public_id.py` | `uuid.uuid4()` → `uuid.uuid1()` | 1: `test_filling_gives_each_row_its_own_version_4_uuid` |
| `models.py` | `editable=False` → `editable=True` | 2: `test_the_field_is_not_editable_and_stays_out_of_forms`, `test_models_have_no_pending_migrations` |
| `models.py` | Quitar `unique=True` | 2: `test_the_field_is_a_required_unique_uuid_generated_by_uuid4`, `test_models_have_no_pending_migrations` |
| `0004_alter_asset_public_id.py` | Quitar `unique=True` | 4: `test_the_database_rejects_a_repeated_public_id_by_name`, `test_the_unique_constraint_is_the_only_unique_one_on_the_column`, `test_the_last_migration_makes_the_column_required_unique_and_uuid4`, `test_models_have_no_pending_migrations` |
| `services.py` | `_apply_update` regenera `public_id` y lo añade a `update_fields` | 11: los 4 de `test_no_service_changes_the_public_id` y 7 de `test_update.py` |

sha256 antes y después:

| Fichero | sha256 |
|---|---|
| `models.py` | `bf0d3e92830c8f6755b8d6f4264f7603ed27ce5565d07de849b9b8e42f6b9c30` |
| `0003_fill_asset_public_id.py` | `310caf74f684262e40de105b96d5b224b5e2dfbc3b23d4b14fb622c4a3ebfcd9` |
| `0004_alter_asset_public_id.py` | `3d9e913477a3dd69c38ce5c5baa1ff409ffebc6b95c4d7e6ee05d1d1defd5189` |
| `services.py` | `ad17a3e668ba6c016a56a7b082ae21d876dd764c5ed08648462037039d3c4579` |

## Validación de la zona (T3)
Fecha: 2026-11-02 · Ficheros: `backend/apps/assets/zone.py` y `backend/apps/assets/tests/test_zone.py`. Ningún otro fichero de producción cambia.

| Comprobación | Orden | Resultado |
|---|---|---|
| Tests de la zona | `docker compose exec backend pytest -q apps/assets/tests/test_zone.py` | 284 passed |
| Suite completa con la BD de test recreada | `docker compose exec backend pytest -q --create-db` | 1481 passed (1197 previos) |
| Estilo y formato | `docker compose exec backend sh -c "ruff check . && ruff format --check ."` | Sin incidencias; 104 ficheros formateados |
| Pureza | `test_zone_module_stays_pure_without_django_drf_or_other_apps` (AST) | `zone.py` no importa Django, DRF ni otras apps |

### Lo observado
| # | Comprobación | Observado |
|---|---|---|
| 1 | Área con el contexto por defecto (28 dígitos) | Redondearía: `6.00000000000000000000000000003` se aceptaría como 6. Con `localcontext(Context(prec=100, traps=[Inexact, InvalidOperation]))` se rechaza |
| 2 | Cota de dígitos del área con operandos de 32 caracteres | Máximo 65 dígitos en 14 641 combinaciones de límites extremos y 300 000 zonas aleatorias, sin ninguna señal `Inexact` ni `InvalidOperation` |
| 3 | `abs()` frente a la comparación para el rango | `abs()` redondea a la precisión del contexto global: `90.0000000000000000000000000001` pasaría como 90. El rango se comprueba con `-limit <= valor <= limit` |
| 4 | Parámetro presente y vacío (`?south=`) | `not_a_number`; `required` queda para el ausente |

### Pruebas de mecanismo
Mutaciones sobre `zone.py`, restauradas desde una copia hecha antes. sha256 de `zone.py` idéntico antes y después de cada una, y también el de `test_zone.py`.

| Mutación | Tests que fallan |
|---|---|
| `fullmatch` → `match` | 72: texto que no es un decimal simple |
| `[0-9]` → `\d` (dígitos no ASCII) | 4: texto que no es un decimal simple |
| Longitud máxima 33 | 6: tres de 33 caracteres, el orden de claves, los cinco códigos y el contexto corto |
| Área con `float` | 3: área exacta con precisión por defecto, cola de 31 caracteres y contexto corto |
| Área sin `localcontext` | 3: los mismos tres |
| Inversión con `>=` | 8: sur = norte, oeste = este, `-0`, punto único y los bordes ±90 y ±180 |
| Área con `>=` | 5: área exactamente 6 aceptada |
| Área comprobada antes que la inversión | 1: invertida con ambos ejes y área positiva |
| La inversión ignora la longitud | 3: zona invertida |
| Aceptar duplicados (`> 2`) | 27: repetido (24), orden de claves (2) y los cinco códigos |
| `abs()` en vez de comparar | 4: bordes con 28 dígitos y fuera de rango |
| Rango exclusivo (`<`) | 16: bordes ±90 y ±180 y los que dependen de ellos |
| Vacío tratado como `required` | 9: vacío, repetido y texto no decimal |
| Límite de longitud en el sur | 7: rango y orden de claves |
| Formato comprobado antes que la longitud | 3: 33 caracteres de basura y orden de claves |

| Fichero | sha256 |
|---|---|
| `zone.py` | `a7329e76abff98163d348e8df5e709cfa9568334f9df6cebab4467c9b1b5022f` |
| `test_zone.py` | `cbd3cf9c14fde3c2bef955df1bf48db8c9c13136a89865d19cf9147482923a57` |

## Selector de la lectura pública (T4)
Fecha: 2026-11-02 · Ficheros: `backend/apps/assets/selectors.py` y `backend/apps/assets/tests/test_selectors.py`. Ningún otro fichero de producción cambia. `migrate` no se ha ejecutado en la BD de desarrollo: los tests usan la BD de test.

| Comprobación | Orden | Resultado |
|---|---|---|
| Tests del selector | `docker compose exec backend pytest -q apps/assets/tests/test_selectors.py` | 51 passed |
| Suite completa con la BD de test recreada | `docker compose exec backend pytest -q --create-db` | 1535 passed (1484 previos), `test_architecture` incluido |
| Estilo y formato | `docker compose exec backend sh -c "ruff check . && ruff format --check ."` | Sin incidencias; 108 ficheros formateados |

### Qué prueba cada grupo de tests
| Grupo | Tests | Qué demuestra |
|---|---|---|
| Privacidad | `test_the_coordinates_are_the_public_ones_and_not_the_exact_ones`, `test_each_row_carries_its_own_coordinates_without_crossing_the_axes` | Con la exacta desplazada +0,004° en latitud y +0,003° en longitud (≈ 445 m y ≈ 258 m a 39,5 N), `latitude` y `longitude` coinciden con la pública con tolerancia 1e-9° (≈ 0,1 mm) y difieren de la exacta en al menos 0,003° por eje. Las coordenadas asimétricas detectan un cruce de ejes |
| Privacidad | `test_an_asset_whose_public_location_is_inside_and_exact_outside_is_returned`, `test_an_asset_whose_public_location_is_outside_and_exact_inside_is_not_returned` | Un bien con la pública a un lado del borde y la exacta al otro se filtra por la pública |
| Estructura (apoyo a la privacidad) | `test_a_row_has_exactly_the_whitelisted_keys` y los tests del SQL | Las diez claves exactas, sin `id`, `owner` ni `exact_location`; el SQL capturado no contiene `exact_location` ni columnas de `users_user` en el SELECT |
| Coherencia, no privacidad | `test_the_coordinates_of_the_selector_match_what_the_service_stored` (radios 500, 1000 y 2000, Madrid) | Servicio y selector leen la misma columna. No afirma ninguna distancia entre exacta y pública: un punto en el centro de su celda daría ≈ 0 m |

### Lo observado
| # | Comprobación | Observado |
|---|---|---|
| 1 | Distancia entre exacta y pública con el servicio en Madrid (40,4168 / −3,7038) | 174 m con radio 500, 366 m con 1000 y 943 m con 2000 |
| 2 | Límites `Decimal` de la zona | El ORM los pasa al SQL como `float`; la comparación es en doble precisión. Un límite con más de unas 17 cifras significativas se redondea y no se prueba |
| 3 | Filtro por `ST_X`/`ST_Y` con `BETWEEN` | Inclusivo en los cuatro bordes; a 1e-6° fuera de cualquiera de ellos, el bien no aparece |
| 4 | `select_related("owner")` antes de `.values()` | El SQL es idéntico con y sin él: `.values()` lo descarta, así que esa mutación es equivalente (ver abajo) |

SQL capturado por `captured_sql` con la zona 39,4 / −0,4 / 39,5 / −0,3 y `limit=200`:
```sql
SELECT "assets_asset"."public_id" AS "public_id", "assets_asset"."title" AS "title", "categories_category"."slug" AS "category__slug", "categories_category"."name" AS "category__name", "assets_asset"."price" AS "price", "assets_asset"."currency" AS "currency", "assets_asset"."price_unit" AS "price_unit", "assets_asset"."privacy_radius" AS "privacy_radius", ST_Y(("assets_asset"."public_location")::geometry(GEOMETRY,4326)) AS "latitude", ST_X(("assets_asset"."public_location")::geometry(GEOMETRY,4326)) AS "longitude" FROM "assets_asset" INNER JOIN "users_user" ON ("assets_asset"."owner_id" = "users_user"."id") INNER JOIN "categories_category" ON ("assets_asset"."category_id" = "categories_category"."id") WHERE ("users_user"."is_active" AND "assets_asset"."status" = 'active' AND ST_Y(("assets_asset"."public_location")::geometry(GEOMETRY,4326)) BETWEEN 39.4 AND 39.5 AND ST_X(("assets_asset"."public_location")::geometry(GEOMETRY,4326)) BETWEEN  -0.4 AND  -0.3) ORDER BY "assets_asset"."created_at" DESC, "assets_asset"."id" DESC LIMIT 201
```

### Pruebas de mecanismo
Mutaciones sobre `selectors.py`, restauradas desde una copia hecha antes; cada una se ejecutó con `test_selectors.py` y `test_architecture.py` (102 tests). sha256 de `selectors.py` idéntico antes y después de cada una, y también el de los ficheros de test.

| Mutación | Tests que fallan |
|---|---|
| Añadir `exact_location` a `values` | 2: claves exactas y `exact_location` en la consulta |
| Añadir `id` a `values` | 2: claves exactas y columnas fuera de la lista blanca |
| Añadir `owner` a `values` | 2: claves exactas y columnas de usuario en el SELECT |
| Quitar `.values()` | 35 |
| Quitar `.values()` y añadir `select_related("owner")` | 35 |
| `select_related("owner")` antes de `.values()` | 0: mutación equivalente, el SQL no cambia |
| Quitar el filtro de `status` | 1: bien pausado |
| Quitar el filtro `owner__is_active` | 2: propietario desactivado y condiciones del WHERE |
| Cortar con `[:limit]` | 5: límites, `LIMIT 201` y 201 bienes |
| Comparar con `queryset.count()` | 12: una sola consulta, sin `COUNT(` y SELECT |
| Quitar `-id` del orden | 1: empate de `created_at` |
| Orden ascendente | 10: orden y límites |
| Rango estricto (`gt` y `lt`) | 9: bordes, altura cero y anchura cero |
| Coordenadas desde `exact_location` | 16: valores, bordes, altura cero y SQL |
| Filtrar por la exacta y devolver la pública | 11: bordes, lados opuestos del borde y SQL |
| Intercambiar `ST_X` y `ST_Y` | 29 |
| Devolver la fila de más | 4: límites y 201 bienes |
| Incompleta con exactamente `limit` bienes | 4: 200 bienes, límite 0 sin bienes y límites |

| Fichero | sha256 |
|---|---|
| `selectors.py` | `8e88dbd21840c1552fbc61f217969e05ae5e9f71ad52699683660913c61b2422` |
| `test_selectors.py` | `69cf7774e0ec6c73f56acc96e14fbe3ba9076b54f2474a52d073d5c1d21b7c52` |

## Middleware de cookies (T5, primera mitad)
Fecha: 2026-11-02 · Ficheros: `backend/apps/core/middleware.py`, `backend/apps/core/tests/test_middleware.py` y `backend/config/settings/base.py` (el middleware, el primero de `MIDDLEWARE`). La vista, el límite y el serializer son de la segunda mitad. `migrate` no se ha ejecutado y no se ha accedido a la BD de desarrollo: los tests de la pila real no llevan `django_db`, así que cualquier acceso a la BD los haría fallar.

| Comprobación | Orden | Resultado |
|---|---|---|
| Tests del middleware | `docker compose exec backend pytest -q apps/core/tests/test_middleware.py` | 45 passed |
| Suite completa con la BD de test recreada | `docker compose exec backend pytest -q --create-db` | 1580 passed (1535 previos) |
| Estilo y formato | `docker compose exec backend sh -c "ruff check . && ruff format --check ."` | Sin incidencias; 110 ficheros formateados |

### Lo observado
| # | Comprobación | Observado |
|---|---|---|
| 1 | Vista sin marcar con `csrftoken=x` y `sessionid=short` | Sí lleva `Set-Cookie` (cookie CSRF nueva y cookie de sesión borrada) y `Vary: Cookie`: el montaje reproduce el problema |
| 2 | La misma petición a una vista marcada | Sin `Set-Cookie` y sin `Vary: Cookie`, con GET, HEAD, POST y otros métodos, y con respuestas 400, 405 y 429 |
| 3 | `SessionStore.load` parcheado para fallar | No se llama: ni el middleware ni la pila tocan la sesión |
| 4 | `Vary` con espacios alrededor de las comas | `cc_delim_re.split` deja espacios en los extremos de la cabecera; cada token se recorta, así que un `Vary` sin `Cookie` pero con espacios raros se reescribe normalizado con `", "` |
| 5 | `Vary: Cookies` | No se toca: la comparación es por token completo |

### Pruebas de mecanismo
Mutaciones restauradas desde una copia hecha antes; cada una se ejecutó con `test_middleware.py`. sha256 idéntico antes y después en `middleware.py`, `base.py` y `test_middleware.py`.

| Fichero | Mutación | Tests que fallan |
|---|---|---|
| `middleware.py` | No vaciar `response.cookies` | 23 |
| `middleware.py` | No quitar `Cookie` de `Vary` | 28 |
| `middleware.py` | Actuar sobre todas las respuestas, marcadas o no | 9 |
| `middleware.py` | Basta una marca truthy en vez de `True` | 5 |
| `middleware.py` | Actuar por la ruta `/api/` en vez de por la marca | 29 |
| `middleware.py` | Comparar el token `Cookie` distinguiendo mayúsculas | 3 |
| `middleware.py` | Quitar cualquier token que contenga «cookie» | 1 |
| `middleware.py` | Borrar `Vary` entero | 6 |
| `middleware.py` | Leer `request.session` | 24 |
| `base.py` | Middleware el último de la lista | 18 |
| `base.py` | Middleware fuera de la lista | 18 |

| Fichero | sha256 |
|---|---|
| `middleware.py` | `04dba6893fff87caad85a98e60d1520997e8fd174ba90bc8a884d8b7d295cb56` |
| `base.py` | `7ee4907e9f6cc76540da45a77fbc208c3721f0eff08df373bf5af744b8c7a205` |
| `test_middleware.py` | `8dff5c90f20d882c51b59ec0969c6958b9e244b9fa18ce58915780d825f0ffdc` |

## Lista pública de bienes (T5, segunda mitad)
Fecha: 2026-11-02 · Ficheros: `backend/apps/assets/{views,serializers,urls}.py`, `backend/apps/assets/tests/test_public_list_api.py`, `backend/config/urls.py`, `backend/conftest.py` (`cache.clear()` autouse) y `docs/architecture.md`. `migrate` no se ha ejecutado y no se ha accedido a la BD de desarrollo: todo se prueba contra la BD de test. `backend/openapi.json` no se genera aquí. La petición real de punta a punta (incluido el cuerpo vacío de HEAD con curl) queda para cuando se apliquen las migraciones en desarrollo.

| Comprobación | Orden | Resultado |
|---|---|---|
| Tests de la lista pública | `docker compose exec backend pytest -q apps/assets/tests/test_public_list_api.py` | 93 passed |
| Suite completa con la BD de test recreada | `docker compose exec backend pytest -q --create-db` | 1673 passed (1580 previos) |
| Estilo y formato | `docker compose exec backend sh -c "ruff check . && ruff format --check ."` | Sin incidencias; 114 ficheros formateados |
| Descripción OpenAPI | `call_command("spectacular", "--validate", "--fail-on-warn", "--lang", "en", …)` dentro de un test | Sin avisos; una sola ruta con `get`, cuatro parámetros obligatorios y respuestas 200, 400, 405 y 429 |

### Comprobado en el código instalado (DRF 3.18.3, Django 5.2.18)
| Afirmación del plan | Dónde |
|---|---|
| El límite se comprueba antes de resolver el método (un POST con el límite superado da 429) | `rest_framework/views.py:514` (`initial`) antes de `:517-521`; `check_throttles` en `:421` |
| `THROTTLE_RATES` se lee al importar | `throttling.py:66`; `rate` en la subclase evita `get_rate()` (`:69-70`) |
| Con `authentication_classes = []` no se toca la sesión | `request.py:166`, `:405-414` y el setter de `user` (`:240-250`) |
| Los contadores viven en la caché `default` | `throttling.py:62`, `:123` y `:140` |
| Las 429 no se anotan | `throttling.py:130-131` y `:143-146` |
| `Throttled.wait` se redondea hacia arriba | `exceptions.py:236-237` |
| `as_view` es `csrf_exempt` | `views.py:149` |
| `X-Forwarded-For` se ignora con `NUM_PROXIES = 0` | `throttling.py:31-33` |
| Una cookie `csrftoken` mal formada añade cookie aunque la vista sea `csrf_exempt` | `django/middleware/csrf.py:402-405` y `:420` |
| Una `sessionid` de menos de 8 caracteres se borra y añade `Vary: Cookie` | `django/contrib/sessions/middleware.py` (`process_response`) y `backends/base.py:215-232` |

### Lo observado
| # | Comprobación | Observado |
|---|---|---|
| 1 | Respuesta sin marcar con cada cookie mal formada por separado (ruta inexistente bajo `/api/v1/`) | `sessionid=short` sola, `csrftoken=x` sola y las dos a la vez añaden cada una su `Set-Cookie` y `Vary: Cookie`; una `sessionid` de 32 caracteres no añade nada. Los tests de errores con la vista real parametrizan las tres combinaciones |
| 2 | 400, 405 y 429 de la vista real con esas cookies | Sin `Set-Cookie` y sin `Vary: Cookie`, porque `finalize_response` marca todas las respuestas |
| 3 | `Vary: Cookie` puesto por la vista | No se ve por HTTP con el middleware activo, que lo quita; lo detecta el test que llama a la vista sin middleware |
| 4 | `SessionAuthentication` en la vista | Sin `AuthenticationMiddleware` en el proyecto no cambia la respuesta; lo detecta el test de atributos de la vista |
| 5 | Cabecera `Access-Control-*` puesta por la vista | La detectan 10 tests por HTTP: el middleware no la quita |

### Pruebas de mecanismo
Mutaciones restauradas desde una copia hecha antes. Cada una se ejecutó con `test_public_list_api.py`, `apps/core/tests/test_api.py` y `config/tests/test_api_settings.py`. sha256 idéntico antes y después en todos los ficheros tocados, incluidos `apps/core/api.py` y `config/settings/base.py`, que son anteriores a la tarea y se mutaron con copia.

| Fichero | Mutación | Tests que fallan |
|---|---|---|
| `serializers.py` | Campo `id` de más | 3 |
| `serializers.py` | `price` como `FloatField` | 1 |
| `serializers.py` | `category_slug` leído de `category__name` | 1 |
| `views.py` | `SessionAuthentication` | 1 |
| `views.py` | Quitar `permission_classes` (queda `IsAuthenticated`) | 88 |
| `views.py` | Quitar el `Vary: Accept-Encoding` explícito | 11 |
| `views.py` | Añadir `Cookie` al `Vary` | 1 |
| `views.py` | Añadir `Access-Control-Allow-Origin` | 10 |
| `views.py` | No marcar las respuestas | 13 |
| `views.py` | `finalize_response` marca solo el 200 | 10 |
| `views.py` | `rate = "61/min"` | 23 |
| `views.py` | Comprobar el límite dentro de `get` | 4 |
| `views.py` | Añadir `options` a `http_method_names` | 13 |
| `views.py` | `max_age` 61 | 1 |
| `views.py` | Caché sin `public` | 1 |
| `views.py` | Límite de 201 bienes | 2 |
| `views.py` | Pasar el `QueryDict` a `parse_zone` | 49 |
| `apps/core/api.py` | Caché pública también en los errores | 33 (20 de la lista y 13 de `test_api.py`) |
| `apps/core/api.py` | El manejador incluye `detail` | 49 (27 y 22) |
| `apps/core/api.py` | Quitar la cabecera `Retry-After` | 4 (1 y 3) |
| `config/settings/base.py` | `NUM_PROXIES = None` | 2 (1 de la lista y 1 de los ajustes) |

| Fichero | sha256 |
|---|---|
| `views.py` | `dc67279a1fc9486467d81bfcf94bfaa0a72e9e1e527c40fb9d7c75d72431f69c` |
| `serializers.py` | `c9f0e3dea6901bd1223027ff6af5f88926b48089695986330adbd88dcfa90932` |
| `apps/core/api.py` | `4c0c3586c54e1deba9afd1b165e333fa347e781f12725b7672662450fe9cdb09` |
| `config/settings/base.py` | `7ee4907e9f6cc76540da45a77fbc208c3721f0eff08df373bf5af744b8c7a205` |
| `test_public_list_api.py` | `17035b2d93ceca33dfc92141e6600e187614ade3b5e43a7b511587a1ace66928` |

## Comando de demostración (T6)
Fecha: 2026-11-02 · Ficheros: `backend/apps/assets/demo.py`, `backend/apps/assets/management/commands/create_demo_assets.py` (con sus `__init__.py`), `backend/apps/assets/tests/test_demo_command.py`, `ENVIRONMENT` en `backend/config/settings/{development,test,production}.py` y cuatro casos en `backend/config/tests/test_settings.py`. El comando solo se ha ejecutado dentro de pytest, contra la BD de test: no se ha accedido a la BD de desarrollo ni se ha ejecutado `migrate`.

| Comprobación | Orden | Resultado |
|---|---|---|
| Tests del comando y de los ajustes | `docker compose exec backend pytest -q apps/assets/tests/test_demo_command.py config/tests/test_settings.py` | 61 passed (39 del comando) |
| Suite completa con la BD de test recreada | `docker compose exec backend pytest -q --create-db` | 1716 passed (1673 previos) |
| Estilo y formato | `docker compose exec backend sh -c "ruff check . && ruff format --check ."` | Sin incidencias; 119 ficheros formateados |

### Lo observado
| # | Comprobación | Observado |
|---|---|---|
| 1 | Datos de demostración | 25 entradas: 24 activas y la última pausada; las 11 categorías de la semilla (las 11 primeras entradas, una por slug); radios 10 de 500, 9 de 1000 y 6 de 2000 |
| 2 | Reparto de radios | No es por turnos: dentro de 2 km del centro solo caben 6 celdas de 2000 m y, con más bienes de ese radio, algunos compartían celda. Se rebajaron dos entradas (la 22 a 500 y la 24 a 1000) para que el único par repetido sea el esperado |
| 3 | Distancias al centro (39,4699 / −0,3763) | Exactas a menos de 1715 m; públicas, calculadas por el servicio, a menos de 2343 m. El criterio es 4 km |
| 4 | Par con la misma ubicación pública y el mismo radio | Las entradas 1 y 12 (bicicletas eléctricas), radio 1000, exactas (39,4579 / −0,3803) y (39,4581 / −0,3801); pública común (39,455291 / −0,380941). Es el único grupo repetido |
| 5 | Selector sobre una zona alrededor del centro | Devuelve los 24 bienes activos y ninguno es el pausado |
| 6 | Comprobación de entorno | Primera sentencia de `handle`. Con `production`, `staging`, `Development`, `TEST`, vacío, ` test`, `None`, un valor no hashable o el atributo borrado: `CommandError` con el mensaje fijo, sin salida y sin acceso a la BD (el test no lleva `django_db`) |
| 7 | Sin salida de coordenadas ni contraseña | Con la configuración real (`django.db.backends` en INFO, sin `force_debug_cursor`), ninguna forma de las 25 coordenadas exactas ni la contraseña centinela aparece en stdout, stderr ni logs. El test comprueba antes el nivel efectivo y un control positivo de captura |
| 8 | Por qué no se prueba con DEBUG | Con `caplog` a DEBUG y `force_debug_cursor`, un `create_asset` correcto registra la ubicación exacta (EWKB) en el `INSERT` |
| 9 | Generador de contraseña y reloj reales | Los tests los sustituyen, así que una primera mutación del generador sobrevivió; se añadieron dos tests (contraseña de al menos 43 caracteres, URL-safe y distinta cada vez; hora con zona UTC) |

### Pruebas de mecanismo
Mutaciones restauradas desde una copia hecha antes; cada una se ejecutó con `test_demo_command.py` y `test_settings.py` (61 tests). sha256 idéntico antes y después en todos los ficheros tocados.

| Fichero | Mutación | Tests que fallan |
|---|---|---|
| `create_demo_assets.py` | Quitar la comprobación de entorno | 9 |
| `create_demo_assets.py` | Consultar la BD antes de comprobar el entorno | 9 |
| `create_demo_assets.py` | Quitar `atomic` | 2 |
| `create_demo_assets.py` | Imprimir la contraseña por stdout / por stderr / en un log | 3 / 1 / 1 |
| `create_demo_assets.py` | Entornos permitidos como conjunto (un valor no hashable lanza `TypeError`) | 1 |
| `create_demo_assets.py` | Permitir `production` | 1 |
| `create_demo_assets.py` | Misma hora para todos los bienes | 1 |
| `create_demo_assets.py` | Activar los 25 | 3 |
| `create_demo_assets.py` | Ignorar al propietario existente | 2 |
| `create_demo_assets.py` | Hora sin zona | 1 |
| `create_demo_assets.py` | Contraseña fija en vez de aleatoria | 1 |
| `demo.py` | Un punto a más de 4 km | 3 |
| `demo.py` | Quitar una categoría | 3 |
| `demo.py` | Solo dos radios | 3 |
| `demo.py` | Romper el par | 2 |
| `demo.py` | Todos activos / dos pausados | 6 / 6 |
| `demo.py` | Email fuera de `example.com` | 1 |
| `settings/test.py` | `ENVIRONMENT = "production"` | 13 |
| `settings/production.py` | `ENVIRONMENT = "development"` | 1 |
| `settings/development.py` | Sin `ENVIRONMENT` | 1 |

| Fichero | sha256 |
|---|---|
| `create_demo_assets.py` | `c41aeadbbffb833c0a10cae916b9843b6d88ba7a65cef986b8dc34a488fe6603` |
| `demo.py` | `1e1178c71504c8aae63433a0f353cc7e65401fa8f38b37bbea27fa0c662bc4e6` |
| `settings/development.py` | `0df56a7b9021faf622f8f8ff79aacb4c70b99ac9c35ff8286b54f8d363759d64` |
| `settings/test.py` | `e3ac015ad8621984d9c2699e598f7c9ede9ec0bf7bbb377adb4888bec194e7ec` |
| `settings/production.py` | `cc19ede72d8ea0393c4c3477d035d984d25ed6fefb3a54ae4fe4cbee5ac72d7d` |
| `test_demo_command.py` | `aa0c7b9104eadc833daf83ece3392197ce18af739337d2347e048b9de6ef8ee2` |
| `test_settings.py` | `4f27b16a0276b2a40690747fa86888f6c96a30c10b466e1d09134ca7c413efa8` |

## De punta a punta, parte de backend
Fecha: 2026-11-02 · Entorno: Docker Compose, BD de desarrollo, `runserver` en `127.0.0.1:8000`. Ejecutado con orden expresa del usuario para `migrate` (solo las tres migraciones de assets) y para `create_demo_assets` (dos veces). Los comandos de `manage.py` se lanzaron con el servidor parado (`docker compose stop backend` y `docker compose run --rm backend …`), como pide el plan. La comprobación en navegador (24 tarjetas y sus círculos en la vista inicial, a 375 y 1280 px) queda para la tarea del frontend.

Zona usada en los `curl`: `south=39.40&west=-0.45&north=39.55&east=-0.30`, sobre `http://localhost:8000/api/v1/public/assets/`.

| # | Orden | Esperado | Observado |
|---|---|---|---|
| 1 | `docker compose run --rm backend python manage.py showmigrations assets` | `0001` aplicada y `0002`, `0003` y `0004` pendientes | Igual |
| 1b | `… manage.py migrate --plan` | Solo las tres migraciones de assets, sin pendientes de otras apps | Igual: `0002` (Add field), `0003` (Raw Python operation) y `0004` (Alter field) |
| 2 | `… manage.py migrate` | Las tres se aplican, cada una en su transacción | `Applying assets.0002_asset_public_id… OK`, `0003_fill_asset_public_id… OK` y `0004_alter_asset_public_id… OK`; `showmigrations assets` las muestra aplicadas |
| 3 | `… manage.py create_demo_assets` | `Creados 25 bienes de demostración (24 activos, 1 pausado).` sin contraseña | Igual |
| 3b | El mismo comando otra vez | `El propietario de demostración ya existe; no se ha creado nada.` | Igual |
| 4 | `docker compose up -d backend` | `runserver` en `127.0.0.1:8000` | Igual |
| 5 | GET de la zona | `200`, `application/json`, `Cache-Control: public, max-age=60`, `Vary: Accept-Encoding`, `Allow: GET, HEAD`, sin `Set-Cookie`, sin `Vary: Cookie`, sin `Access-Control-*`; 24 bienes, `incomplete: false`, diez claves, sin el pausado, precio como texto | Igual. 24 bienes, todos de `demo.py` (ninguno ajeno), los 24 activos presentes y «Piscina infantil con toldo» (el pausado) ausente; un solo conjunto de claves: `category_name`, `category_slug`, `currency`, `latitude`, `longitude`, `price`, `price_unit`, `privacy_radius`, `public_id`, `title`; raíz con `incomplete` y `results`; todos los precios son texto (p. ej. «8.00»); el primer bien lleva la pública `39.455291 / -0.380941` |
| 6 | HEAD de la misma URL (`curl -I`) y socket crudo | `200` con las cabeceras del GET y cuerpo vacío | `200` con exactamente las mismas cabeceras que el GET (comparadas sin `Date`). En un socket crudo llegan 353 bytes en total y 0 tras la línea en blanco: no hay cuerpo. `Content-Length` es 6385, el mismo que el del GET, como permite HTTP para HEAD |
| 7 | POST a la misma URL | `405`, `{"code":"method_not_allowed"}`, `Allow: GET, HEAD`, `no-store`, sin `Set-Cookie` | Igual |
| 8 | GET con `south=40&west=-0.45&north=39.5&east=-0.30` | `400 {"code":"zone_inverted"}` y `no-store` | Igual |
| 8b | GET sin `east` | `400 invalid_parameters` con `{"params":{"east":"required"}}` y `no-store` | Igual |
| 9 | GET con `Cookie: csrftoken=x; sessionid=short` | `200`, mismo cuerpo que el paso 5, sin `Set-Cookie` y sin `Vary: Cookie` | Igual: cuerpo idéntico byte a byte (`cmp`), 0 cabeceras `Set-Cookie`, `Vary: Accept-Encoding` |
| 9b | Control: GET a `/api/v1/unknown/` con esas mismas cookies | `404` con `Set-Cookie` (`csrftoken` y la sesión borrada) y `Vary: Cookie` | Igual: ambas cookies y `Vary: Cookie`. Demuestra que el problema existe en el servidor real y que la vista pública lo evita |

No se pidió ni se cambió nada más en la BD de desarrollo: quedan el propietario `demo@example.com` y sus 25 bienes. En la zona consultada solo aparecen los 24 bienes de demostración: no hay otros bienes activos y visibles.

## Campos opcionales del error en la descripción OpenAPI (previo a la T7)
Fecha: 2026-11-02 · Commit `bb837b3` · Ficheros: `backend/apps/assets/serializers.py` y `backend/apps/assets/tests/test_public_list_api.py`. No se ha accedido a la BD de desarrollo: todo contra la BD de test.

Causa: `drf_spectacular/openapi.py:1094-1097` añade a `required` todo campo cuyo esquema es `readOnly` mientras `COMPONENT_NO_READ_ONLY_REQUIRED` valga `False` (el valor por defecto), aunque el campo tenga `required=False`. `params` y `retry_after` de `ApiErrorSerializer` eran `read_only=True`, así que `openapi.json` los exigía y el servidor los omite (un 405 solo lleva `code`). Arreglo: quitar `read_only=True` de esos dos campos, porque el serializer solo documenta respuestas; `code` sigue de solo lectura y por tanto obligatorio. Se descarta `COMPONENT_NO_READ_ONLY_REQUIRED=True`: dejaría de exigir también los campos de `PublicAsset` y de `PublicAssetList`.

| Comprobación | Orden | Resultado |
|---|---|---|
| Test nuevo antes del arreglo | `docker compose exec backend pytest -q apps/assets/tests/test_public_list_api.py -k only_requires` | Falla porque `ApiError.required` contiene `params` y `retry_after` |
| Test nuevo con el arreglo | la misma orden | Pasa |
| Suite completa | `docker compose exec backend pytest -q` | 1717 passed (1716 previos) |
| Estilo y formato | `docker compose exec backend sh -c "ruff check . && ruff format --check ."` | Sin incidencias; 119 ficheros formateados |
| Descripción regenerada | `docker compose run --rm -T --no-deps --entrypoint "" -u "$(id -u)" backend python manage.py spectacular --format openapi-json --file openapi.json --validate --fail-on-warn --lang en` | `ApiError.required` pasa a `["code"]` y desaparece `readOnly` de `params` y `retry_after`; nada más cambia |
| Tipos regenerados | `npm run api:gen` | `params?` y `retry_after?` opcionales y sin `readonly` |

El test comprueba, en la descripción generada, que `ApiError` conserva sus tres propiedades y solo exige `code`, que `PublicAsset` exige sus diez campos y que `PublicAssetList` exige `results` e `incomplete`.

### Pruebas de mecanismo
Mutaciones restauradas desde una copia hecha antes; cada una se ejecutó con `test_public_list_api.py`, `apps/core/tests/test_api.py` y `config/tests/test_api_settings.py` (149 tests en verde sin mutar). sha256 idéntico antes y después en `serializers.py` y en `config/settings/base.py`, que es anterior a la tarea.

| Fichero | Mutación | Tests que fallan |
|---|---|---|
| `serializers.py` | `params` vuelve a `read_only=True` | 1: `test_the_description_only_requires_what_the_server_always_sends` |
| `serializers.py` | `retry_after` vuelve a `read_only=True` | 1: el mismo |
| `serializers.py` | Los dos vuelven a `read_only=True` | 1: el mismo |
| `serializers.py` | `params` sin `required=False` | 1: el mismo |
| `config/settings/base.py` | `COMPONENT_NO_READ_ONLY_REQUIRED=True` en `SPECTACULAR_SETTINGS` | 1: el mismo |

| Fichero | sha256 |
|---|---|
| `serializers.py` | `9d0a8effbf175399d94374c362e5ea33908772804d7b15032a735e3ec715df9d` |
| `config/settings/base.py` | `7ee4907e9f6cc76540da45a77fbc208c3721f0eff08df373bf5af744b8c7a205` |

## Esqueleto del frontend y contrato del cliente (T7)
Fecha: 2026-11-02 · Ficheros: `frontend/` (configuración, `src/main.tsx`, `src/styles/index.css`, `src/i18n/es.ts`, `src/api/{schema.gen.ts, validate.ts, validate.test.ts}`), `backend/openapi.json`, `.github/workflows/ci.yml` y `docs/architecture.md`. No se ha accedido a la BD de desarrollo. El workflow de CI no se ha ejecutado en GitHub: sus órdenes se han probado en local.

El lock se resolvió y auditó antes, fuera del repo, con `npm install --package-lock-only --ignore-scripts` y las 19 versiones exactas. El del repo tiene el mismo sha256 (`773728f3644cebe7e0d04e32da357cbaf2db4534efa0cc72966c148c17417466`) y no ha cambiado con `npm ci`.

| Comprobación | Orden | Resultado |
|---|---|---|
| Instalación | `cd frontend && npm ci --ignore-scripts` | 240 paquetes instalados; el lock tiene 288 entradas sin la raíz y solo `fsevents` trae script de instalación |
| Tests | `npx vitest run` | 81 passed (un fichero) |
| Build | `npm run build` | `tsc -b && vite build` en verde |
| Lint | `npx eslint .` | Sin incidencias |
| Tipos generados al día | `npm run api:check` | Salida 0 con el contrato real; salida 1 («Generated types are not up-to-date!») con una copia en la que `ApiError.required` lleva `params` |
| Auditoría de producción | `npm audit --omit=dev` | 0 vulnerabilidades |
| Auditoría completa | `npm audit` | 13 moderados, todos del aviso GHSA-g3hv-75wg-m249 (minimatch < 11.0.1) en eslint, typescript-eslint y openapi-typescript; aceptado como riesgo de desarrollo (plan, Riesgos) |
| Desfase de la descripción | `docker compose run --rm -T --no-deps --entrypoint "" backend sh -c "python manage.py spectacular --format openapi-json --file /tmp/openapi.json --validate --fail-on-warn --lang en && diff /tmp/openapi.json openapi.json"` | Salida 0 |
| YAML del CI | Cargado con PyYAML | Dos jobs (`backend-quality` y `frontend-quality`) |
| Acciones del CI | `gh release list -R actions/setup-node` | La versión 7 existe (v7.1.0, 2026-10-08) |

### Lo observado
| # | Comprobación | Observado |
|---|---|---|
| 1 | `z.number()` con `NaN` e `Infinity` | Los rechaza (tests de latitud NaN, infinita y longitud infinita negativa) |
| 2 | `z.uuidv4()` en Zod 4.6.7 | Existe; rechaza UUID v1 y v7 |
| 3 | Tipos generados frente a Zod | `price_unit` y `currency` salen `string`, `privacy_radius` sale `number` y `public_id` y `price` salen texto, porque el serializer los declara como `CharField`, `IntegerField` y `UUIDField`. Zod es más estricto; la aserción de compilación exige que `z.infer` sea asignable al tipo generado, en un solo sentido. La descripción no limita unidades, moneda ni radios: solo los limita Zod |
| 4 | Build | Las tres variantes de la fuente salen como `url(/assets/…woff2)`, del propio origen. Las URL del JS son internas de React (mensajes de error y espacios de nombres XML) y la del CSS es el comentario de licencia de Tailwind; ninguna es una petición |
| 5 | `tseslint.config()` | Está marcado `@deprecated` en typescript-eslint 8.72.1 a favor de `defineConfig()` de ESLint; `eslint.config.js` usa `defineConfig` |
| 6 | Proxy de Vite | Añade `Vary: Origin` a las respuestas en desarrollo; no lo pone Django |

### Proxy de Vite (mismo origen)
`npm run dev` en `frontend/`, con el backend arrancado. Ninguna de las dos peticiones consulta la BD: el POST se rechaza por método y el GET falla en la validación de la zona, las dos antes del selector.

| Orden | Esperado | Observado |
|---|---|---|
| `ss -ltn \| grep :5173` | Solo en localhost | `127.0.0.1:5173` |
| `curl -si -X POST http://localhost:5173/api/v1/public/assets/` | 405 con el formato único | `405`, `{"code":"method_not_allowed"}`, `allow: GET, HEAD`, `cache-control: no-store` |
| `curl -si http://localhost:5173/api/v1/public/assets/` | 400 con los cuatro límites ausentes | `400`, `{"code":"invalid_parameters","params":{"south":"required","west":"required","north":"required","east":"required"}}`, `no-store` |
| `curl -si http://localhost:5173/` | La página de Vite | `200`, `text/html` |

### ESLint: sintaxis de inyección de HTML
Fichero temporal sin versionar con un caso por línea, ya borrado (`eslint src/lint-probe.tsx --format json`). Con la configuración anterior, 13 de los 17 casos no saltaban. Con la actual saltan los 17 y los 5 controles quedan limpios.

| Casos que saltan | Controles que no saltan |
|---|---|
| `dangerouslySetInnerHTML` en JSX, en un objeto de `createElement` y como clave entre comillas; `innerHTML`, `outerHTML`, `insertAdjacentHTML` y `setHTML`; `document.write`, `document.writeln` y `window.document.write`; los mismos con corchetes y con plantilla (``el[`innerHTML`]``, `document["write"]`); acceso opcional `el?.innerHTML` | `textContent`, `document.title`, `el["textContent"]`, `write` de otro objeto y una clave dinámica (`el[key]`, límite conocido: no se puede analizar) |

### Pruebas de mecanismo de Zod
36 mutaciones de `validate.ts`, restauradas desde una copia hecha antes; 33 se ejecutan con vitest (81 tests en verde sin mutar) y 3 con `tsc -p tsconfig.app.json --noEmit`. Ninguna sobrevive. sha256 de `validate.ts` y de `validate.test.ts` idéntico antes y después.

| Mutación | Fallos |
|---|---|
| Bien: `strictObject` a `object` | 1 |
| Raíz: `strictObject` a `object` | 2 |
| `privacy_radius` de unión de literales a `number` | 4 |
| `latitude` admite `null` | 1 |
| `currency` de literal a `string` | 2 |
| `price_unit` de enum a `string` | 1 |
| Precio sin el ancla `^` | 3 |
| Precio sin el ancla `$` | 2 |
| Precio de hasta 6 cifras enteras | 1 |
| Precio con 1 o 2 decimales | 1 |
| Precio con `\s*` final | 1 |
| Máximo de bienes 201 | 1 |
| Sin comprobar ids únicos | 1 |
| Título con máximo 201 | 1 |
| Título sin `refine` (acepta solo espacios) | 2 |
| Título con `trim()` (reescribe el valor) | 1 |
| `public_id` de `uuidv4` a `uuid` | 2 |
| `public_id` de `uuidv4` a `string` | 3 |
| `incomplete` con `coerce.boolean` | 3 |
| `latitude` sin máximo | 1 |
| `latitude` sin mínimo | 1 |
| `longitude` con máximo 181 | 1 |
| `longitude` con mínimo −181 | 1 |
| `category_slug` sin mínimo | 1 |
| `category_slug` con máximo 65 | 1 |
| `category_name` sin mínimo | 1 |
| `category_name` con máximo 101 | 1 |
| El error lleva `cause` con el error de Zod | 1 |
| El error lleva la ruta del campo en el mensaje | 2 |
| `validateResponse` devuelve el JSON sin validar | 56 |
| Clave de más en el esquema de la raíz | 25 |
| Clave de más en el esquema del bien | 22 |
| Quitar una clave del esquema de la raíz (vitest) | 24 |
| Aserción de tipos: `incomplete` como `string` | `tsc` TS2322 |
| Aserción de tipos: `privacy_radius` como `string` | `tsc` TS2322 |
| Aserción de tipos: quitar `incomplete` del esquema (`tsc`) | `tsc` TS2741 |

| Fichero | sha256 |
|---|---|
| `frontend/src/api/validate.ts` | `2faff7e0cb1a834e69739e8647b03993dabdb7e25904d2282ce09ef74e076068` |
| `frontend/src/api/validate.test.ts` | `1f4c6dceed962e8f0ab6376f43c656546454061e0eba329160868c159ddc342e` |
