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
