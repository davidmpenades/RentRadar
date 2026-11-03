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

## Cuadro pedido, planificador y petición (T8)
Fecha: 2026-11-03 · Ficheros: `frontend/src/map/{requestBox.ts, scheduler.ts}`, `frontend/src/api/publicAssets.ts` y sus tests (`requestBox.test.ts`, `scheduler.test.ts`, `publicAssets.test.ts`). No se ha accedido a la BD de desarrollo ni se han añadido dependencias. Los tests corren en entorno node, sin importar maplibre-gl, con un reloj y un fetch falsos que respetan `AbortSignal`; no usan `vi.useFakeTimers`, `AbortSignal.timeout` ni `AbortSignal.any`. Sin pruebas de mecanismo: la tarea no toca privacidad ni seguridad.

Antes de implementar, los tres ficheros de tests fallaron por la razón esperada: `Cannot find module './requestBox'`, `'./scheduler'` y `'./publicAssets'`. Los cambios posteriores (fallo de red y margen en longitud) también se escribieron antes y fallaron por la suya: `NetworkError` sin definir y los índices de 80 y 85 grados distintos de los esperados.

| Comprobación | Orden | Resultado |
|---|---|---|
| Tests | `cd frontend && npx vitest run` | 197 passed en 4 ficheros: `validate` 81, `publicAssets` 64, `requestBox` 40, `scheduler` 12 |
| Build | `npm run build` | `tsc -b && vite build` en verde (los tests también pasan por `tsc`) |
| Lint | `npx eslint .` y `npx eslint` sobre los seis ficheros nuevos | Sin incidencias |
| Tipos generados al día | `npm run api:check` | Salida 0 |

### Lo observado
| # | Comprobación | Observado |
|---|---|---|
| 1 | Índices de `requestBox` calculados a mano frente al código | Coinciden en los cuadros de referencia: cerca del ecuador, 59–61 de latitud norte y sur, 80 y 85 grados, zona que cruza el ecuador, 2200 y 2201 celdas, 6 y 6,3 grados cuadrados, y los bordes de ±85 y ±180 |
| 2 | Margen en longitud | Usa la latitud más alejada del ecuador del cuadro ya ampliado en latitud, antes de redondear. Se desvía de la fórmula del plan, que usaba la latitud de la zona visible: con ella faltaban unos 1,1 m de los 2 km a 60 grados, 3,6 m a 80 y 7,2 m a 85. Dos zonas con el borde escogido a mano (80 y 85 grados) dan índices distintos con una fórmula y con la otra: zona 79,5 / 5,103665 / 80 / 7,39633, oeste 99 y este 151 (con la latitud visible serían 100 y 150); zona 84,5 / 0,7051 / 84,96 / 0,7949, oeste 9 y este 21 (con la visible, 10 y 20). El margen no anula el coseno: tras comprobar ±85 en latitud, el cuadro ampliado no pasa de 85 grados |
| 3 | `Math.ceil` de un valor entre −1 y 0 | Da `-0` (p. ej. norte −0,03: `north` sale `-0`); `boxToQuery` lo escribe `0.00` porque formatea desde el entero con `index < 0` y `Math.abs` |
| 4 | Estados distintos de 200 y `Content-Type` que no es JSON, con `Response` real de Node | `bodyUsed` sigue en `false`: no se lee el cuerpo |
| 5 | Cuerpo que nunca llega | Con un `ReadableStream` que falla al abortar la señal, `response.json()` rechaza con su motivo y el fallo sale como tiempo agotado; el temporizador sigue vivo al llegar las cabeceras (1 pendiente) y se cancela al validar (0) |
| 6 | Tiempo máximo | A 9 999 ms sigue pendiente; a 10 000 ms falla con la señal interna abortada y sin temporizadores. La instancia real arma un temporizador de 10 000 ms |
| 7 | Cancelación externa | Con la señal ya abortada no se llama a `fetch` ni se arranca ningún temporizador; abortada durante la petición o el cuerpo sale el mismo `AbortError`, sin temporizadores y con el listener quitado; `classifyFailure` lo propaga |
| 8 | Fallo de red | Solo la llamada a `fetch` se envuelve: su `TypeError` pasa a `NetworkError`, con mensaje fijo, sin dirección ni mensaje original ni `cause`. Un `TypeError` de `response.json()` o de las cabeceras se propaga y `classifyFailure` no lo clasifica; si el temporizador ya disparó, el `TypeError` de `fetch` sale como tiempo agotado |
| 9 | Respuesta de Vite | `index.html` con 200 y `text/html` se clasifica como respuesta no válida antes de `JSON.parse` |
| 10 | Contrato | Un test lee `backend/openapi.json` (`resolveJsonModule`): la ruta pedida es una de sus rutas y los cuatro parámetros de consulta son `east`, `north`, `south` y `west` |
| 11 | Planificador | Solo pide el último movimiento a los 300 ms; la anterior se aborta al vencer la espera (no al programar); `cancel()` repetido no falla y deja pedir de nuevo; una respuesta vieja no se pinta aunque llegue después de la nueva |

### Decisiones para revisar
- Paso de la cuadrícula de 0,05 grados, margen del cliente de 0,5 grados cuadrados (máximo de 2200 celdas) y espera de 300 ms (`REQUEST_DELAY_MS`), tal como fija el plan.
- `createRequestScheduler` entrega a `run` la señal y `isCurrent()`; quien pide comprueba `isCurrent()` antes de pintar o de mostrar un error.
- `classifyFailure` solo clasifica causas conocidas y propaga el resto (anotado en la T10).
- Margen en longitud con la latitud del cuadro ya ampliado y no con la de la zona visible, que es lo que decía el plan (observación 2).
- Un `TypeError` solo es un fallo de red si sale de la llamada a `fetch` (`NetworkError`); en cualquier otro punto es un error del código y se propaga.

## Comprobaciones previas al mapa base (T9)
Fecha: 2026-11-03 · No se ha tocado código ni la BD de desarrollo. Las dos peticiones a OpenFreeMap fueron un GET cada una, sin cookies ni cabeceras propias.

| # | Comprobación | Observado |
|---|---|---|
| 1 | `maplibre-gl` 6.14.0 y su export | No tiene export por defecto: `import maplibregl from "maplibre-gl"` falla en el build con `MISSING_EXPORT`. Se importa con nombre (`import { Map, setWorkerUrl } from "maplibre-gl"`). El CSS entra por `maplibre-gl/dist/maplibre-gl.css` (`exports` admite `./dist/*`) |
| 2 | Worker con Vite 8.3.5 | Por defecto busca `maplibre-gl-worker.mjs` junto al módulo (`src/util/web_worker.ts:32-41` y `:74`), que tras el empaquetado no existe. El worker no importa nada. `?url` lo copia tal cual como `.mjs`; `?worker&url` lo reempaqueta como `.js`. Se elige `?worker&url` y `setWorkerUrl` (`src/index.ts:177`) para no depender del tipo MIME de `.mjs` en producción. Build de prueba hecho; la carga real del worker, en dev y con `vite preview`, queda para la verificación en navegador de la T9 |
| 3 | Estilo positron (`GET https://tiles.openfreemap.org/styles/positron`) | 200, `application/json`, 25 202 bytes, `access-control-allow-origin: *`. Versión 8, 55 capas (background, fill, line, symbol). Fuentes: raster `https://tiles.openfreemap.org/natural_earth/ne2sr/{z}/{x}/{y}.png` y vectorial por TileJSON `https://tiles.openfreemap.org/planet`. Sprite `https://tiles.openfreemap.org/sprites/ofm_f384/ofm`. Glifos `https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf` |
| 4 | TileJSON (`GET https://tiles.openfreemap.org/planet`) | 200, `application/json`, 19 254 bytes. `tiles`: `https://tiles.openfreemap.org/planet/20261101_080013_pt/{z}/{x}/{y}.pbf`, con versión en la ruta. No lleva `url` |
| 5 | Hosts a los que el navegador hace peticiones | Solo `tiles.openfreemap.org`. Los demás hosts (`openfreemap.org`, `openmaptiles.org`, `openstreetmap.org`) aparecen únicamente como enlaces en el HTML de `attribution` del TileJSON y no generan peticiones hasta que se pulsan |
| 6 | Atribución en `maplibre-gl` 6.14.0 | Las opciones de la fuente pisan al TileJSON (`src/source/load_tilejson.ts:39`, `extend(tileJSON, options)`). `AttributionControl` pasa cada texto por `DOM.sanitize` (lista blanca de etiquetas y atributos, `src/util/dom.ts`) y no por `innerHTML` directo; aun así el texto y los enlaces serían del tercero. El TileJSON de OpenFreeMap trae enlaces sin `rel`, de modo que `rel="noopener noreferrer"` distingue en el navegador la atribución propia |

## Mapa base, círculos y fallo del estilo (T9)
Fecha: 2026-11-03 · Ficheros: `frontend/src/app/{route.ts, NotFoundPage.tsx}`, `frontend/src/main.tsx`, `frontend/src/map/{style.ts, loadStyle.ts, loadAssets.ts, geodesy.ts, circles.ts, MapView.tsx}`, `frontend/src/pages/MapPage.tsx`, `frontend/src/i18n/es.ts`, `frontend/src/styles/index.css` y sus tests (`route.test.ts`, `style.test.ts`, `loadStyle.test.ts`, `loadAssets.test.ts`, `geodesy.test.ts`, `circles.test.ts`). `loadStyle.ts` (descarga del estilo con timeout, tope y validación) y `loadAssets.ts` (decisión de pintar o vaciar los círculos) son módulos puros añadidos para poder probar esas decisiones en node. No se ha accedido a la BD de desarrollo, no se han tocado servicios de Docker ni se han añadido dependencias. Los tests corren en entorno node sin importar maplibre-gl ni React, con fetch y temporizadores falsos que respetan `AbortSignal`.

Antes de implementar, los seis ficheros de tests nuevos fallaron por la razón esperada (`Cannot find module './route'`, `'./geodesy'`, `'./circles'`, `'./style'`, `'./loadStyle'` y `'./loadAssets'`); los demás ficheros (los de la T7 y la T8) siguieron en verde.

| Comprobación | Orden | Resultado |
|---|---|---|
| Tests | `cd frontend && npx vitest run` | 344 passed en 10 ficheros: `validate` 81, `publicAssets` 64, `style` 57, `requestBox` 40, `circles` 28, `loadStyle` 23, `loadAssets` 16, `geodesy` 12, `scheduler` 12, `route` 11 |
| Build | `npm run build` | `tsc -b && vite build` en verde (aviso de chunk > 500 kB por maplibre-gl, esperado) |
| Lint | `npx eslint .` y `npx eslint` sobre los ficheros tocados | Sin incidencias |
| Tipos generados al día | `npm run api:check` | Salida 0 |

### Lo observado en el navegador
Chrome DevTools, servidor de desarrollo (`npm run dev`, puerto 5173) y `npm run build` + `npx vite preview` (puerto 4173), con la API real de localhost:8000 a través del proxy de Vite. Los dos servidores se pararon al acabar.

| # | Comprobación | 1280 px | 375 px |
|---|---|---|---|
| 1 | `/` y `/map/` | Acaban en `/map`; el historial sube una entrada por la navegación y ninguna por la redirección; Atrás desde `/` vuelve a la página anterior (`/otra`), no a la raíz | Igual |
| 2 | Mapa | Pantalla completa (1280×800 en `.maplibregl-map`), mapa base visible en la vista inicial, panel de 400 px a la izquierda con todo el alto y el aviso | Panel de 375×267 px abajo (40dvh) con el aviso; sin desbordamiento horizontal (`scrollWidth` 375) |
| 3 | Atribución | Visible arriba a la derecha: «OpenFreeMap © OpenMapTiles Data from OpenStreetMap». Los tres enlaces llevan `rel="noopener noreferrer"` y `target="_blank"`, que el TileJSON no trae. Con `AttributionControl({compact: false})` y sin `customAttribution` no sale el enlace «MapLibre» | Igual; el texto ocupa 325 px y llega a solaparse con el rótulo de un pueblo del mapa |
| 4 | Controles | Zoom «Acercar» y «Alejar» de 44×44 px bajo la atribución; sin brújula | Igual |
| 5 | Círculos | Dibujados desde la API real (25 bienes de demostración, 24 activos); sin marcador ni punto central; con zoom bajo se dibujan todos, solapados | Igual |
| 6 | Peticiones de bienes | Una sola petición a `/api/v1/public/assets/` tras la carga. Tres clics en «Alejar» con 60 ms entre ellos y ocho pulsaciones de flecha dan una sola petición tras parar | Una petición tras la carga |
| 7 | Red | Solo `localhost:5173` (o `4173`) y `https://tiles.openfreemap.org`; la fuente woff2 sale del propio origen | Igual |
| 8 | Zoom fuera de rango | Con zoom bajo no se pide y los círculos desaparecen | — |
| 9 | Petición de bienes con 500 (fetch simulado) | — | Los círculos desaparecen; sin errores en consola |
| 10 | `/otra` | «Página no encontrada» y enlace «Ir al mapa» de 123×44 px con foco visible, que lleva a `/map` con Enter | Igual (123×44 px) |
| 11 | Teclado | Tab recorre mapa (con etiqueta «Mapa de bienes en alquiler»), tres enlaces de atribución, «Acercar» y «Alejar»; las flechas mueven el mapa y `=` acerca; foco de 3 px #14181F con 2 px de separación | «Ir al mapa» y «Reintentar» con el mismo foco |
| 12 | Estilo bloqueado (`VITE_MAP_STYLE_URL=http://tiles.openfreemap.org/styles/positron`, servidor aparte) | — | «No se ha podido cargar el mapa.» con «Reintentar» (44 px) en lugar del mapa; ninguna petición salvo al propio origen; Enter sobre «Reintentar» mantiene el mensaje; consola sin mensajes |
| 13 | Fallo de red del estilo (fetch simulado, falla dos veces) | — | Mensaje y «Reintentar»; al pulsarlo se descarga el estilo, se crea el mapa y salen los círculos |
| 14 | `vite preview` | El worker se carga desde `/assets/maplibre-gl-worker-*.js`; mapa, círculos y una petición de bienes | Igual |
| 15 | `BlockedUrlError` en MapLibre | Con un estilo hostil en una página aparte (fuentes `http://evil.example/…` y `https://evil2.example/…`) y `createTransformRequest`, los errores llegan al evento `error` como la misma instancia de `BlockedUrlError`, con el mensaje fijo, y no sale ninguna petición hacia esos hosts | — |

### Consola
Durante la verificación salió un único error, `Failed to load resource: 404` de `/favicon.ico`, que `index.html` no declaraba (preexistente de la T7). Se arregló en esta tarea con `<link rel="icon" href="data:,">` y se volvió a comprobar en dev (2026-11-03): sin errores. Hay dos avisos (`warn`) de MapLibre sobre los filtros de las capas `highway-shield-non-us` y `highway-shield-us-interstate` del estilo positron de OpenFreeMap (`layers[…].filter[1]: Expected value to be of type number, but found null instead`): el filtro de esas capas lleva `null` donde se espera un número. No vienen de nuestro código y no se silencian.

### Pruebas de mecanismo
Copia de cada fichero en `/home/david/.claude/jobs/ce733ec1/tmp/t9-mutations/`, mutación, `npx vitest run` y restauración desde la copia.

| # | Mutación | Fichero | sha256 antes → mutado → después (completos) | Test que falla |
|---|---|---|---|---|
| 1 | `validateStyleUrl` acepta `http:` | `style.ts` | `b871ef9ab5bc1346d5f579a7883fb760ce394e7dad03944acdb126865d3381e0` → `2956d9c8757c7f3ef178d91e983c601f00ac60696d3424a62dc7e93e1ef6267d` → `b871ef9ab5bc1346d5f579a7883fb760ce394e7dad03944acdb126865d3381e0` | `validateStyleUrl > rechaza "http://tiles.openfreemap.org/styles/positron"` |
| 2a | `isAllowedMapUrl` acepta `http:` | `style.ts` | `b871ef9ab5bc1346d5f579a7883fb760ce394e7dad03944acdb126865d3381e0` → `3febed67d1f739e5a7656aeb8625d86de4ba4b25d745608c1707bd53035e9ac0` → `b871ef9ab5bc1346d5f579a7883fb760ce394e7dad03944acdb126865d3381e0` | `rechaza http en un origen permitido` y `rechaza http en el origen propio` |
| 2b | `isAllowedMapUrl` acepta otro host | `style.ts` | `b871ef9ab5bc1346d5f579a7883fb760ce394e7dad03944acdb126865d3381e0` → `3150c318c7b3d8f658fe1a58632961f24224f7b22baea110783f76778929831b` → `b871ef9ab5bc1346d5f579a7883fb760ce394e7dad03944acdb126865d3381e0` | 8 tests: otro host, subdominio parecido, prefijo parecido, otro puerto, host tras una arroba, entre otros |
| 3 | El listener silencia cualquier error | `style.ts` | `b871ef9ab5bc1346d5f579a7883fb760ce394e7dad03944acdb126865d3381e0` → `c9d22ef6fc2ba4b4c22547aff4d7f3b862f0f40d99f3a9a4f412b5f16808b0be` → `b871ef9ab5bc1346d5f579a7883fb760ce394e7dad03944acdb126865d3381e0` | `no silencia cualquier otro error`, `no silencia algo que parece un BlockedUrlError sin serlo` y `registra un valor que no es un Error` |
| 4 | Sin sustitución de la atribución | `style.ts` | `b871ef9ab5bc1346d5f579a7883fb760ce394e7dad03944acdb126865d3381e0` → `47e98d1d41e5fc008a55dac417e24346a9291a7f848af266177d2c1ceadf2be1` → `b871ef9ab5bc1346d5f579a7883fb760ce394e7dad03944acdb126865d3381e0` | `sustituye la atribución hostil de cada fuente`, `pone la atribución propia a una fuente que no traía ninguna`, `no muta el estilo original` y `descarga el estilo sin credenciales y fija la atribución` |
| 5 | Pintar sin comprobar `isCurrent()` | `loadAssets.ts` | `32f04df8b0cd8537dbcab11d8c706e5daf5dc7674e9536327432cb140c93da8c` → `8e73d118dbee74d2e214bddf3e108f309af8209c2e8f8675c9762303554358b1` → `32f04df8b0cd8537dbcab11d8c706e5daf5dc7674e9536327432cb140c93da8c` | `no pinta la respuesta de una petición que ya no es la actual` y `comprueba la vigencia al llegar la respuesta, no al pedir` |

Ninguna mutación sobrevivió. Cada restauración coincide con el sha256 original.

### Decisiones para revisar
- Además de `moveend`, `MapView` avisa de `movestart` y `MapPage` cancela entonces el planificador. Motivo observado: una animación interrumpida (varios clics seguidos en el zoom, o varias pulsaciones de flecha) emite `moveend` antes de empezar la siguiente, y la petición salía a los 300 ms en mitad de la animación; con el aviso de `movestart` sale una sola, tras parar el mapa.
- `AttributionControl({compact: false})` sin `customAttribution` no pinta el enlace «MapLibre» (las opciones que se pasan sustituyen a las de por defecto).
- Movimiento reducido: ver la sección siguiente. MapLibre ya lo respeta; solo falta comprobar nuestro propio movimiento de cámara en la T10.

### Movimiento reducido
Se comprobó en el código de `maplibre-gl` 6.14.0 y en el navegador. En el código, `zoomIn`, `zoomTo` y `flyTo` pasan por `easeTo`, que pone `duration = 0` si la opción `essential` no está y el sistema pide movimiento reducido (`src/ui/camera.ts:851` y `:1337`); la inercia del arrastre también lo respeta (`src/ui/handler_manager.ts:793`). La preferencia se lee de `matchMedia('(prefers-reduced-motion: reduce)')` (`src/util/browser.ts:87-93`). En el navegador (Chrome DevTools, dev, 1280 px, `emulate` con `prefersReducedMotion`) se mide, con `performance.now()` y `PerformanceResourceTiming`, los milisegundos entre pulsar «Acercar» y el inicio de la petición de bienes, tres veces por caso:

| Emulación | Milisegundos hasta la petición | Qué significa |
|---|---|---|
| `reduce` | 309, 306 y 312 | Los 300 ms de espera del planificador y ninguna animación |
| `no-preference` | 817, 807 y 822 | Los 500 ms de la animación más la espera |

Ningún código nuestro pasa `essential`, así que el zoom de los botones, el teclado y el arrastre no se animan con movimiento reducido. Queda comprobar en la T10 el movimiento propio de «Volver a la zona inicial».

## Decisiones previas a la lista del panel (T10)
Fecha: 2026-11-03 · Sin código nuevo.

| # | Tema | Decisión o comprobación |
|---|---|---|
| 1 | Caso que RF-13 no enumeraba | Un error que `classifyFailure` no clasifica (un fallo del código, no de la red ni del servidor) llega al panel como el tipo `unexpected`, que existe solo en `viewState`; `classifyFailure` no cambia. Mensaje: «Ha ocurrido un error inesperado. Vuelve a intentarlo.», con «Reintentar». El error además va a `console.error`. Sin esto el panel se quedaría en «Buscando bienes…» |
| 2 | Zona de las tarjetas | El estado de la petición guarda la zona visible del momento de pedir (los límites de `getBounds`), nunca el cuadro que calcula `requestBox`. Las tarjetas son los bienes cuyo círculo toca esa zona; los círculos del mapa son todos los de la respuesta. Un bien dentro del cuadro pedido (ampliado 2 km) pero con el círculo fuera de la zona visible tiene círculo y no tiene tarjeta |
| 3 | Fallo del estilo y panel | Con el estilo fallido el panel muestra solo el aviso de ubicación aproximada, sin cabecera ni lista: el «Reintentar» está ya sobre el mapa. No se lanza ninguna petición de bienes |
| 4 | `?no-inline` en Vite 8.3.5 | Build de prueba fuera del repo con las 11 imágenes de `prototypes/006-mapa/datos/fotos`: con `import.meta.glob(..., {query: "?no-inline", import: "default"})` salen 11 ficheros `assets/<nombre>-<hash>.svg` y las rutas son `/assets/<nombre>-<hash>.svg`; con `?url` salen las 11 como `data:image/svg+xml`. Se usa `?no-inline` para que la CSP de la 011 pueda ser `img-src 'self'` |
| 5 | Imágenes de categoría | Los 11 nombres coinciden con los 11 slugs de `0002_seed_categories.py`. Sin `href`, `xlink`, `url(`, `<script>`, `<style>`, `<image>`, `<foreignObject>`, `data:` ni atributos `on*` una vez quitado el `xmlns`; solo `svg`, `rect`, `circle`, `ellipse` y `path` |

## Lista del panel, vacío y errores (T10)
Fecha: 2026-11-03 · Ficheros nuevos: `frontend/src/panel/{ResultsPanel.tsx, AssetCard.tsx, header.ts, categoryImage.ts}`, `frontend/src/state/viewState.ts`, `frontend/src/map/viewport.ts`, `frontend/src/i18n/format.ts`, `frontend/src/assets/categories/*.svg` (11, copiadas de `prototypes/006-mapa/datos/fotos`, que no está en git) y sus tests. Modificados: `frontend/src/map/{loadAssets.ts, MapView.tsx, circles.ts, geodesy.ts}`, `frontend/src/pages/MapPage.tsx`, `frontend/src/i18n/es.ts` y los tests de `loadAssets`, `circles` y `geodesy`. No se ha accedido a la BD de desarrollo, no se han tocado servicios de Docker ni se han añadido dependencias. El navegador solo hizo GET a la API pública por el proxy de Vite.

Antes de implementar, los tests nuevos fallaron por la razón esperada: `Cannot find module './format'`, `'./header'`, `'./categoryImage'`, `'./AssetCard'`, `'./viewport'` y `'./viewState'`; en los ficheros ya existentes, `isCircleVisible is not a function`, `distanceToBoundsMeters is not a function` y `report is not a function` (el contrato antiguo de `loadAssetsForView`).

| Comprobación | Orden | Resultado |
|---|---|---|
| Tests | `cd frontend && npx vitest run` | 539 passed en 18 ficheros (nuevos: `format` 37, `viewport` 3, `header` 18, `categoryImage` 25, `categorySvg` 45, `ResultsPanel` 24, `viewState` 20, `zone` 1; ampliados: `circles` 41, `geodesy` 18, `loadAssets` 18) |
| Build | `npm run build` | En verde. Las 11 imágenes salen como `assets/<nombre>-<hash>.svg` y ninguna como `data:` (ni en el JS ni en el worker) |
| Lint | `npx eslint .` | Sin incidencias |
| Tipos generados al día | `npm run api:check` | Salida 0 |
| Caracteres invisibles en los ficheros tocados | Detección por categoría Unicode (Cf, Zs, Mn, Cc, Zl, Zp) | Ninguno |

### Decisiones de la implementación
- **Estado único.** `MapPage` guarda `request: loading | loaded | notRequested | failed`. `loaded` lleva la lista y la zona visible del momento de pedir (el argumento `bounds` de `loadAssetsForView`, nunca el cuadro de `requestBox`). Las tarjetas (`viewState`) y los círculos (`requestCircles`) se derivan de él; `loading` lo pone la página al arrancar la petición, y si el cuadro no se pide `notRequested` llega en el mismo lote y «Buscando bienes…» no se pinta.
- **`loadAssetsForView`** cambia `show` y `clear` por `report(outcome)`. La comprobación de `isCurrent()` sigue antes de reportar, tanto en éxito como en fallo; un `AbortError` no reporta. Un error que `classifyFailure` propaga se reporta como `failed` con tipo `unexpected` y va a `console.error`.
- **Fallo del estilo.** `MapPage` guarda `styleFailed` y `MapView` es controlado (`styleFailed`, `onStyleFailed`, `onStyleRetry`). Con el estilo fallido no se pide nada y el panel solo lleva el aviso.
- **Volver a la zona inicial.** `resetSignal` (contador) que `MapView` convierte en `easeTo` sin `essential`. `onReady` y `onMoveEnd` entregan además centro y zoom para `atInitialView` (centro ±1e-6°, zoom ±0,01). Las constantes de la vista inicial pasan de `MapView` a `src/map/viewport.ts`, que no importa maplibre-gl.
- **Cabecera con una tarjeta y lista incompleta.** «Mostrando 1 bien. Puede haber más: acerca el mapa para verlos todos» (singular), probado en `header.test.ts`.
- **Precio.** `parsePriceCents` lee los céntimos del texto con una expresión regular y los trata como entero; `formatPrice` los pasa a `Intl.NumberFormat("es-ES")` en euros, sin decimales si los céntimos son cero. Una unidad desconocida lanza `RangeError` (la respuesta ya se validó con Zod; el tipo generado la trae como `string`).
- **Imágenes.** `Map` slug → URL construido con `import.meta.glob(..., {query: "?no-inline", import: "default"})`. En dev la URL lleva la consulta `?no-inline` (`/src/assets/categories/ebike.svg?no-inline`) y carga; en el build, `assets/ebike-<hash>.svg`.

### Error máximo de `isCircleVisible`
El punto más cercano de la zona se halla recortando latitud y longitud por separado (`distanceToBoundsMeters`). En un borde de meridiano el punto más cercano real no está a la misma latitud, y el recorte se desvía de él. Medido contra el punto más cercano buscado por muestreo denso de los cuatro bordes (latitudes 0, 39,47, 60 y 80; distancias de 100 m a 4 km; radios 500, 1000 y 2000): el máximo observado fue de unos 2 cm (0,004 % de un círculo de 500 m), y a 84° de latitud con un círculo de 2 km también unos 2 cm, en parte error del propio muestreo. Está muy por debajo del 1 % del radio (5 m para 500 m). `geodesy.test.ts` lo fija con un umbral de 5 cm para cada una de esas latitudes. No hace falta una alternativa.

### Lo observado en el navegador
Chrome DevTools, `npm run dev` (puerto 5173, parado al acabar) y la API real de localhost:8000 por el proxy. Para los estados simulados se sobrescribió `window.fetch` con un `initScript` (la API real no se tocó). 375×667 con `emulate` móvil y 1280×800.

| # | Comprobación | 1280 px | 375 px |
|---|---|---|---|
| 1 | Vista inicial con la API real | 24 tarjetas, cabecera «24 bienes en esta zona»; ninguna es «Piscina infantil con toldo» (el único bien pausado de `demo.py`) y los 24 títulos son los 24 activos | Igual |
| 2 | Panel | Columna de 400×800 px a la izquierda; cabecera y aviso fijos arriba y la lista con su propio desplazamiento (el aviso no se mueve al desplazar) | 375×267 px abajo (40dvh); lista de unos 139 px visibles, es decir, una tarjeta y media |
| 3 | Atribución y zoom | Visibles arriba a la derecha, sin tapar | Igual |
| 4 | Desbordamiento horizontal | `scrollWidth` 1280, sin desbordamiento | `scrollWidth` 375 |
| 5 | Imágenes | 24 `<img alt="">` cargadas (`naturalWidth` > 0 tras desplazar la lista); ningún elemento interactivo dentro de las tarjetas | Igual |
| 6 | Círculos | Dibujados para los 24 bienes (los pares de la misma ubicación y radio comparten círculo) | Igual |
| 7 | Zoom que deja fuera algunos círculos | — | Con zoom alto salen 7 tarjetas: solo las cuyo círculo toca la zona visible, incluida la parte tapada por el panel |
| 8 | Vacío | «No hay bienes en esta zona» con «Volver a la zona inicial» (44 px) tras acercar; al pulsarlo, el mapa vuelve y el botón desaparece | Igual |
| 9 | Zoom bajo | — | «Acerca el mapa para ver los bienes» con el botón (44 px); al pulsarlo vuelve la vista inicial y salen las 24 tarjetas |
| 10 | Lista incompleta | — | «Mostrando 24 bienes. Puede haber más: acerca el mapa para verlos todos»; con una sola tarjeta, «Mostrando 1 bien. Puede haber más: acerca el mapa para verlos todos» |
| 11 | Errores | — | Red, 500, 429, respuesta no válida y `RangeError`: cada uno con su mensaje, «Reintentar» de 44 px y sin tarjetas ni círculos; con la API real, «Reintentar» recupera la lista y la región anuncia «Buscando bienes…» y el resultado. El `RangeError` deja un único `console.error`; los demás, ninguno |
| 12 | Tiempo agotado | — | A los 10 s, «El servidor tarda demasiado en responder.» con «Reintentar» que se recupera |
| 13 | Estilo fallido (la descarga del estilo rechaza) | — | «No se ha podido cargar el mapa.» con «Reintentar» sobre el mapa; el panel solo lleva el aviso (sin cabecera, lista ni botones) y la API de bienes no recibe ninguna petición. Al reparar la descarga y pulsar «Reintentar» salen 24 tarjetas |
| 14 | Región de estado | Un `MutationObserver` registra «Buscando bienes…» y el resultado una vez por petición; cuando el fallo llega al instante, solo el resultado | Igual |
| 15 | Teclado | Tab llega a «Volver a la zona inicial» y Enter lo activa; contorno de 3 px #14181F con 2 px de separación | Tab llega a «Reintentar» (44 px) con el mismo contorno y Enter relanza la petición |
| 16 | Consola | Sin errores; solo los dos avisos conocidos del estilo positron | Igual |

### Movimiento reducido
Se mide con `performance.now()` el tiempo entre pulsar «Volver a la zona inicial» y el inicio de la petición normal que sigue al `moveend`.

| Emulación | Milisegundos | Qué significa |
|---|---|---|
| `no-preference` | 811 | 500 ms de animación del `easeTo` más los 300 ms del planificador |
| `reduce` | 306, 304 y 304 | Solo los 300 ms de espera: sin animación |

Con `reduce`, `transition-duration` de los botones del panel vale `0s`; con `no-preference` vale `0.15s` (`motion-safe:transition-colors`).

### Pruebas de mecanismo
Copia de cada fichero en `/home/david/.claude/jobs/ce733ec1/tmp/t10-mutations/`, mutación, `npx vitest run` completo y restauración desde la copia.

| # | Mutación | Fichero | sha256 antes → mutado → después (completos) | Tests que fallan |
|---|---|---|---|---|
| 1 | El título pintado con `dangerouslySetInnerHTML` | `src/panel/AssetCard.tsx` | `aa8e938c1c667ed9a75aaf28c119112746f7b633c31f5845169da5012cdc9d8b` → `aa31e69756190d25252a430cc1c419f68ce37a6c9c43514d8ae32f0dd0c66a3b` → `aa8e938c1c667ed9a75aaf28c119112746f7b633c31f5845169da5012cdc9d8b` | 5: los 4 de `el título … sale escapado y dentro de <bdi>` (`<img src=x onerror=alert(1)>`, `<script>`, `"><svg onload=alert(1)>` y `&lt;b&gt;`) y `pinta una tarjeta y una imagen por bien, todas con alt vacío`. ESLint también rechaza la línea (`24:16 error No se inyecta HTML  no-restricted-syntax`) |
| 2 | Búsqueda de la imagen con `in` sobre un objeto | `src/panel/categoryImage.ts` | `4549d633545f8ebe6e36b5feec6566f3ddf9a50dc49663ff4d45f750d32a7bfd` → `7288e538deaa319139499de6cc4caba43398d054acc4151f331c68d2b657ecef` → `4549d633545f8ebe6e36b5feec6566f3ddf9a50dc49663ff4d45f750d32a7bfd` | 7: `un slug hostil (…) da la imagen de other y siempre una cadena` con `__proto__`, `constructor`, `toString`, `hasOwnProperty`, `valueOf` y `__defineGetter__`, y `usa la imagen de other si el slug es hostil` |
| 3 | Un SVG con `<image href="https://evil.example/x.png"/>` | `src/assets/categories/other.svg` | `c875ff67540f8eaef55187772cd49bcf831e627cfb95d33184b06970a5b26c78` → `be4abfb1263cb9028b68f871e7244dd3a50cb8e81295ec88c96dcb07f1e4dec5` → `c875ff67540f8eaef55187772cd49bcf831e627cfb95d33184b06970a5b26c78` | 3, de `other.svg`: `solo contiene etiquetas de la lista blanca…`, `solo usa atributos de la lista blanca…` y `no tiene referencias externas ni scripts` |
| 4 | `loaded` guarda los límites del cuadro pedido en vez de la zona visible | `src/map/loadAssets.ts` | `30c17817ead17e66730307fa1ac6531f77965d625a29fb344dc62f5f290fd47b` → `1319b1e88db08c6345f03cc00eaeab1100a9df60738cdfeae37db9a6b00e9c2b` → `30c17817ead17e66730307fa1ac6531f77965d625a29fb344dc62f5f290fd47b` | 4: `zone.test.ts > un bien dentro del cuadro pedido con el círculo fuera de la zona visible tiene círculo y no tarjeta` (el test clave) y tres de `loadAssets.test.ts` que comprueban la zona reportada |
| 5 | Reportar sin comprobar `isCurrent()` | `src/map/loadAssets.ts` | `30c17817ead17e66730307fa1ac6531f77965d625a29fb344dc62f5f290fd47b` → `c74fa8bcbe92c14db0319132f2c55877347667f72642c6704a448b96c76ce527` → `30c17817ead17e66730307fa1ac6531f77965d625a29fb344dc62f5f290fd47b` | 4: `no reporta la respuesta de una petición que ya no es la actual`, `comprueba la vigencia al llegar la respuesta, no al pedir`, `ignora el fallo de una petición que ya no es la actual` e `ignora también un error inesperado de una petición que ya no es la actual` |

Ninguna mutación sobrevivió. Cada restauración coincide con el sha256 original.

### Revisión con web-design-guidelines (solo informe, sin cambios fuera de alcance)
- Pasa: región `aria-live` siempre presente, `alt=""` en imágenes decorativas, dimensiones explícitas y `loading="lazy"`, números tabulares, `Intl` para precio, contorno de foco con `:focus-visible`, `overscroll-contain` en la lista, texto largo con `line-clamp` y `wrap-anywhere`, sin `transition: all`.
- `ResultsPanel.tsx`: al recuperarse tras «Reintentar» el botón desaparece y el foco cae en `body`; el resultado sí se anuncia. Resuelto en «Arreglos posteriores a la revisión».
- `AssetCard.tsx`: el precio y la unidad se separan con espacios normales, así que «12,50 € / día» puede partirse antes de «/»; un espacio duro lo evitaría. Resuelto en «Arreglos posteriores a la revisión».
- `ResultsPanel.tsx`: la lista llega a 200 tarjetas sin virtualizar; las imágenes son perezosas y ligeras, y el tope lo fija la API.
- El panel no tiene encabezados (la página tampoco tiene `h1`); la cabecera es el texto de la región de estado.
- La lista con desplazamiento no tiene elementos enfocables; Chrome y Firefox la hacen enfocable por su cuenta.

### Decisiones para revisar
- **Parpadeo de los círculos.** Resuelto: `loading` conserva la última respuesta cargada solo para los círculos (ver «Arreglos posteriores a la revisión»).
- **Altura de la lista en móvil.** A 375×667 el aviso y la cabecera ocupan unos 130 px de los 267 del panel y la lista deja ver una tarjeta y media. Es la altura fija del plan (`40dvh`, mínimo 240 px); la 007 reordena las alturas.
- **Foco tras «Reintentar».** Resuelto: el foco pasa a la cabecera del panel (ver «Arreglos posteriores a la revisión»).
- **Imagen por categoría de la semilla.** Solo hay 11 imágenes; una categoría nueva usa «other» hasta que se añada la suya.

### Arreglos posteriores a la revisión
Fecha: 2026-11-03 · Tres cambios sobre la T10. Ficheros: `frontend/src/state/viewState.ts` y su test, `frontend/src/pages/MapPage.tsx`, `frontend/src/panel/{ResultsPanel.tsx, AssetCard.tsx}` y `frontend/src/panel/ResultsPanel.test.ts`. El texto del aviso de ubicación aproximada no se ha tocado. Sin BD de desarrollo, sin Docker y sin dependencias nuevas. Esta subsección sustituye a las dos primeras decisiones de «Decisiones para revisar» (parpadeo de los círculos y foco tras «Reintentar») y al punto del espacio entre precio y unidad de la revisión de diseño.

| Comprobación | Orden | Resultado |
|---|---|---|
| Tests | `cd frontend && npx vitest run` | 552 passed en 18 ficheros (`viewState` 28, `ResultsPanel` 29, `zone` 1) |
| Build | `npm run build` | En verde |
| Lint | `npx eslint .` | Sin incidencias |
| Tipos generados al día | `npm run api:check` | Salida 0 |
| Caracteres invisibles en los ficheros tocados | Detección por categoría Unicode | Ninguno |

Antes de implementar, los tests nuevos fallaron por la razón esperada: `startLoading is not a function`, la cabecera sin `tabindex` (`Target cannot be null or undefined`) y `</span> / día` sin espacio duro.

#### 1. Los círculos no parpadean al mover
- `RequestState` pasa a `loading` con `previous`: la última respuesta cargada o `null`. `startLoading(estado)` la guarda desde `loaded`, la conserva desde `loading` y la descarta desde `failed` y `notRequested`. `requestCircles` dibuja los círculos de `loaded` y los de `loading.previous`. `viewState` no la usa: en `loading` el panel sigue mostrando «Buscando bienes…» sin lista, y las tarjetas no se derivan de la respuesta anterior.
- `MapPage` pone `setRequest(startLoading)` al arrancar la petición. Tras un fallo del estilo vuelve a `INITIAL_REQUEST`.
- Tests: `viewState.test.ts` comprueba `loading` con previa (círculos de esa respuesta), `loading` sin previa, `failed` y `notRequested` (ninguno), `loading` tras `loaded` y `loading` tras `loading` (no pierden la respuesta) y que en `loading` no salgan tarjetas.

| Comprobación en navegador | 1280 px | 375 px |
|---|---|---|
| Círculos de la fuente `circles` (`serialize().data.features.length`, leído desde el estado de React de `MapView`) en la vista inicial | 23 (24 bienes; el par de la misma ubicación y radio comparte círculo) | 23 |
| Petición ralentizada a 1,5 s tras alejar (muestreo cada 100 ms) | 23 durante «24 bienes en esta zona» y durante «Buscando bienes…» (sin parpadeo); el panel solo muestra «Buscando bienes…» sin tarjetas | Igual |
| Fallo de red | 0 círculos | 0 |
| «Reintentar» con petición lenta tras un fallo | 0 círculos mientras carga y 23 al llegar la respuesta | — |
| «Acerca el mapa para ver los bienes» | 0 círculos | — |

#### 2. El foco pasa a la cabecera
- La cabecera del panel (el contenedor de la región de estado y de los botones, no el aviso) lleva `tabIndex={-1}` y un `ref`; «Reintentar» y «Volver a la zona inicial» le pasan el foco al activarse, mientras el botón sigue montado. Enfocar un contenedor no cambia el texto de la región `aria-live`, así que no hay un anuncio extra.
- Test (`ResultsPanel.test.ts`, `react-dom/server`): con resultados, error, vacío y estilo fallido hay un solo `tabindex="-1"`, antes de la región de estado y de los botones, y el contenedor se cierra antes del aviso.

| Comprobación en navegador con Enter | 1280 px (1277×700 al ejecutarlo) | 375 px |
|---|---|---|
| Enter sobre «Volver a la zona inicial» | `document.activeElement` es el `<div tabindex="-1">` que contiene la región de estado; sigue siéndolo cuando el estado cambia y el botón desaparece | Igual |
| Enter sobre «Reintentar» (desde Tab) | Igual | Igual (el botón se enfocó por código y Enter fue una pulsación real) |
| Anuncios de la región tras pulsar | «Buscando bienes…» y el resultado, sin ninguno más | — |

#### 3. Espacio duro entre el importe y «/ unidad»
- `AssetCard.tsx` usa la entidad `&nbsp;` de JSX (sin carácter invisible literal). El test comprueba en el HTML `</span>` + espacio duro (construido con `String.fromCharCode(160)`) + `/ día`, y que no aparece `</span> / día`.
- En el navegador, el precio de la primera tarjeta es `8[NBSP]€[NBSP]/ día` y ocupa una sola línea a 375 y 1280 px.

#### Tarjetas visibles a 375 px con el aviso actual
Con 375×667: el panel mide 267 px y la lista 138 px. La primera tarjeta (115 px) se ve entera y de la segunda (135 px) asoman unos 22 px; es decir, una tarjeta y un resto. Las tarjetas de dos líneas de título miden 135 px.

#### Pruebas de mecanismo
Copia de cada fichero en `/home/david/.claude/jobs/ce733ec1/tmp/t10-mutations/`, mutación, `npx vitest run` completo y restauración desde la copia.

| # | Mutación | Fichero | sha256 antes → mutado → después (completos) | Tests que fallan |
|---|---|---|---|---|
| 6a | `startLoading` descarta la respuesta cargada | `src/state/viewState.ts` | `07717570bb63365690e7da66e71e47776461c6a51a8dc05524a4e28ecf77e081` → `961cf506268b9f33e822e94f76d81c132f7645c91d1eae5b7622070b770a24b9` → `07717570bb63365690e7da66e71e47776461c6a51a8dc05524a4e28ecf77e081` | 3: `requestCircles > mientras se espera una respuesta nueva conserva los círculos…`, `startLoading > guarda la respuesta cargada…` y `startLoading > no pierde la última respuesta cargada…` |
| 6b | `requestCircles` ignora la respuesta previa de `loading` | `src/state/viewState.ts` | igual antes → `5ee5a142c6c70800a7be5bbf857136d9cf813b447a8172e73305afa385c6fe0a` → igual después | 1: `requestCircles > mientras se espera una respuesta nueva conserva los círculos…` |
| 6c | `startLoading` desde `loading` descarta la previa | `src/state/viewState.ts` | igual antes → `c69ed861d63ba910cd79a48b91d4045aed68ae6a7ce33ab818f080fd25f8d4a8` → igual después | 1: `startLoading > no pierde la última respuesta cargada si empieza otra petición mientras se espera` |
| 6d | `startLoading` conserva la última respuesta tras `failed` o `notRequested` | `src/state/viewState.ts` | igual antes → `232a952708bdf3464bba3cfecc8baf8add65bd2ecb1ae8a1b149af560b299aa5` → igual después | 3: `tras failed…`, `tras notRequested…` y `tras un fallo con una respuesta cargada antes…` |
| 5 (repetida) | Reportar sin comprobar `isCurrent()` | `src/map/loadAssets.ts` | `30c17817ead17e66730307fa1ac6531f77965d625a29fb344dc62f5f290fd47b` → `c74fa8bcbe92c14db0319132f2c55877347667f72642c6704a448b96c76ce527` → `30c17817ead17e66730307fa1ac6531f77965d625a29fb344dc62f5f290fd47b` | 4, los mismos que la vez anterior |

Ninguna mutación sobrevivió. Cada restauración coincide con el sha256 original.
