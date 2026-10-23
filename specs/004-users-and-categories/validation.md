# Validación — 004-users-and-categories
Fecha: 2026-10-23 · Rama: `feature/004-users-and-categories` · Entorno: Docker Compose, `postgis/postgis:18-3.6`, Django 5.2.18, Python 3.13.16, pytest 9.1.1, pytest-django 4.14.0, ruff 0.16.10

Esta spec no tiene interfaz: no hay verificación en navegador. La evidencia es la suite automática, las pruebas de mecanismo y las comprobaciones sobre la base de datos de desarrollo.

## Commits (de T1 a T8 y ajustes)

| Commit | Contenido |
|---|---|
| 000740e | T1: regla de caracteres de control y error de dominio |
| c5b5962 | Ajuste de ruff para las migraciones generadas (E501 e I001) |
| 67886bc | T2: modelo de usuario por email, migración inicial |
| 652199f | Refactor: la traducción de errores puede cambiar de campo |
| 7f8918f | T3: servicio de alta de usuarios |
| ad0985b, 6ed4e46 | Convención de comentarios sin referencias a la spec y limpieza |
| 2f3d1dc | T4: superusuario y cambio de email |
| 6c7a0f9 | T5: credenciales fuera de errores y logs |
| 85b00df | T6: modelo de categoría y migración inicial |
| b2b9057 | T7: servicio de validación y guardado de categorías |
| 1c99a2b | T8: semilla de las once categorías |
| 0512ada | Test del `LC_CTYPE`: unicidad del nombre con tildes |
| 18147d3, ce208b0 | Tests con los caracteres invisibles (NBSP, tilde descompuesta, ligadura) escritos como escapes: primero los de categorías y después los de core y users. Una detección sobre todos los `.py` de `backend/` da 0 líneas |

## Ejecución

| Comprobación | Orden | Resultado |
|---|---|---|
| Suite completa | `docker compose exec backend pytest -q` | 446 passed |
| Estilo y formato | `ruff check .` y `ruff format --check .` | Sin incidencias; 70 ficheros formateados |
| Configuración | `manage.py check` | Sin incidencias |
| Migraciones al día | `manage.py makemigrations --check --dry-run` | `No changes detected` |
| BD de test | La crea pytest desde cero en cada ejecución | Contiene las once categorías (RF-19) |
| `migrate` en desarrollo | Lo ejecutó el propietario a mano, de forma incremental | 17 migraciones aplicadas (`contenttypes` 2, `auth` 12, `categories` 2, `users` 1), todas `OK`. Salida literal más abajo |
| `showmigrations` en desarrollo | `manage.py showmigrations` | Ninguna pendiente; 19 marcadas `[X]` (las 17 más `core` y `sessions`) |
| Categorías en desarrollo | Consulta de solo lectura con `Category.objects` | 11, con los slugs y nombres de la semilla, en su orden |
| Tabla de usuarios | `to_regclass` | `auth_user` no existe (`None`); la de usuarios es `users_user` |
| Tablas del dominio | `information_schema.tables` | `auth_group`, `auth_group_permissions`, `auth_permission`, `categories_category`, `users_user`, `users_user_groups`, `users_user_user_permissions` |
| Nombres de restricciones | `pg_constraint` y `pg_indexes` | `users_user_email_key`, `users_user_email_lower_unique`, `categories_category_slug_key` y `categories_category_name_lower_unique` existen con esos nombres |
| Localización de la BD | `pg_database` | `rentradar`: `datctype` y `datcollate` `en_US.utf8`, codificación `UTF8` |
| `LOWER` con tildes | Consulta con parámetros desde Django | `lower('JARDÍN') = lower('Jardín')` es verdadero. Bajo la colación `C` da falso (`jardÍn`), así que el riesgo era real |

Sobre el desarrollo: "desde cero" se cumple en la BD de test. La de desarrollo se migró de forma incremental, como prevé la decisión D8 del plan.

### Salida literal del `migrate` en desarrollo
La ejecutó el propietario a mano, con `docker compose exec backend python manage.py migrate`:

```
Operations to perform:
  Apply all migrations: auth, categories, contenttypes, core, sessions, users
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying contenttypes.0002_remove_content_type_name... OK
  Applying auth.0001_initial... OK
  Applying auth.0002_alter_permission_name_max_length... OK
  Applying auth.0003_alter_user_email_max_length... OK
  Applying auth.0004_alter_user_username_opts... OK
  Applying auth.0005_alter_user_last_login_null... OK
  Applying auth.0006_require_contenttypes_0002... OK
  Applying auth.0007_alter_validators_add_error_messages... OK
  Applying auth.0008_alter_user_username_max_length... OK
  Applying auth.0009_alter_user_last_name_max_length... OK
  Applying auth.0010_alter_group_name_max_length... OK
  Applying auth.0011_update_proxy_permissions... OK
  Applying auth.0012_alter_user_first_name_max_length... OK
  Applying categories.0001_initial... OK
  Applying categories.0002_seed_categories... OK
  Applying users.0001_initial... OK
```

## Validación por RF

| RF | Tests que lo cubren (sin parámetros) | Resultado |
|---|---|---|
| RF-1 | `users/test_models.py`: `test_user_is_identified_by_email`, `test_user_has_no_username_field`, `test_user_model_is_the_configured_auth_model`, `test_email_field_definition`. `users/test_services.py`: `test_user_authenticates_with_the_email_in_any_case`. `manage.py check` sin incidencias | Cumple |
| RF-2 | `users/test_emails.py`: `test_normalize_email_strips_surrounding_whitespace`, `..._lowercases_local_part_and_domain`, `..._applies_nfkc`, `..._applies_nfkc_before_lower`, `..._is_idempotent`, `..._is_available_from_the_manager_instance`, `test_get_by_natural_key_*`. `users/test_services.py`: `test_create_user_stores_the_normalized_email`, `test_change_user_email_stores_the_normalized_email` | Cumple. El orden recorte, NFKC y minúsculas queda fijado salvo la separación entre recorte y NFKC (ver Riesgos) |
| RF-3 | `users/test_services.py`: `test_create_user_stores_only_a_password_hash` | Cumple |
| RF-4 | `users/test_services.py`: `test_creation_rejects_invalid_emails` (usuario y superusuario), `test_change_user_email_rejects_invalid_emails_without_changes`. `core/test_text.py`: `test_detects_control_characters`, `test_ignores_text_without_control_characters`, `test_validator_*` | Cumple |
| RF-5 | `users/test_services.py`: `test_email_of_254_characters_is_accepted`, `test_email_of_255_characters_is_too_long`. `users/test_models.py`: `test_email_of_254_characters_is_saved`, `test_email_of_255_characters_is_rejected_by_the_database` (`DataError`) | Cumple |
| RF-6 | `users/test_services.py`: `test_exact_duplicate_email_is_taken`, `test_email_differing_only_in_case_is_taken`, `test_change_user_email_to_another_users_email_is_taken`, `test_change_user_email_to_its_own_email_in_other_case_is_accepted` | Cumple |
| RF-7 | `users/test_models.py`: `test_emails_differing_only_in_case_are_rejected_by_the_database`, `test_exact_duplicate_email_is_rejected_by_the_database` (nombres exactos de restricción). `users/test_services.py`: `test_concurrent_duplicate_is_translated_to_email_taken`, `test_concurrent_email_change_restores_the_instance` | Cumple |
| RF-8 | `users/test_services.py`: `test_missing_password_is_required`, `test_non_text_password_is_invalid`. `users/test_superuser.py`: `test_createsuperuser_without_password_variable_creates_nothing` | Cumple |
| RF-9 | `users/test_services.py`: `test_password_of_128_characters_is_accepted`, `test_password_of_129_characters_is_too_long`, `test_rejections_never_compute_the_hash`, `test_hash_guard_fires_on_a_valid_creation` | Cumple |
| RF-10 | `users/test_services.py`: `test_ordinary_user_gets_no_admin_permissions`, `test_admin_flags_cannot_be_passed`, `test_arguments_must_be_passed_by_name` | Cumple |
| RF-11 | `users/test_superuser.py`: `test_superuser_gets_admin_permissions`, `test_superuser_has_every_permission`, `test_createsuperuser_with_password_variable_creates_a_superuser` | Cumple |
| RF-12 | `users/test_leaks.py`: `test_creation_rejections_do_not_leak`, `test_email_change_rejections_do_not_leak`, `test_createsuperuser_without_password_does_not_leak`, `test_user_text_does_not_contain_the_email`. `users/test_models.py`: `test_str_does_not_expose_the_email`. `config/test_logging.py`: `test_sql_logger_is_fixed_to_info`, `test_base_logging_keeps_the_default_django_loggers`, `test_production_sql_logger_goes_through_the_redacting_handler`, `test_sql_logger_runs_at_info_or_above`. `core/test_errors.py`: `test_domain_error_*` | Cumple |
| RF-13 | `categories/test_models.py`: `test_slug_field_definition`, `test_str_is_the_name`. `categories/test_services.py`: `test_valid_category_is_saved` | Cumple |
| RF-14 | `categories/test_models.py`: `test_slug_with_valid_format_passes_validation`, `test_slug_with_invalid_format_is_rejected` (incluye `\n` final y un dígito no ASCII), `test_empty_slug_is_blank_not_invalid`. `categories/test_services.py`: `test_invalid_slugs_are_rejected`, `test_slug_with_hyphens_and_digits_is_accepted` | Cumple |
| RF-15 | `categories/test_services.py`: `test_slug_of_50_characters_is_accepted`, `test_slug_of_51_characters_is_too_long`, `test_repeated_slug_is_taken`, `test_concurrent_repeated_slug_is_translated_to_slug_taken`. `categories/test_models.py`: `test_slug_of_50_and_name_of_60_characters_are_saved`, `test_slug_of_51_characters_is_rejected_by_the_database`, `test_repeated_slug_is_rejected_by_the_database` | Cumple |
| RF-16 | `categories/test_services.py`: `test_blank_name_is_empty`, `test_name_with_a_control_character_is_rejected`, `test_non_text_name_is_invalid` | Cumple |
| RF-17 | `categories/test_services.py`: `test_name_matching_another_one_ignoring_case_is_taken`, `test_decomposed_name_matches_the_composed_one`, `test_name_of_60_characters_is_accepted`, `test_name_of_61_characters_is_too_long`, `test_concurrent_repeated_name_is_translated_to_name_taken`. `categories/test_models.py`: `test_name_of_61_characters_is_rejected_by_the_database`, `test_names_differing_only_in_case_are_rejected_by_the_database`, `test_accented_names_differing_only_in_case_are_rejected_by_the_database`, `test_name_uniqueness_ignores_case_with_a_named_constraint` | Cumple |
| RF-18 | `categories/test_services.py`: `test_slug_of_a_saved_category_cannot_change`, `test_changed_slug_reports_only_the_immutability`, `test_changed_slug_and_name_errors_are_reported_together`, `test_renaming_a_saved_category_is_accepted`, `test_saving_a_saved_category_without_changes_is_accepted`, `test_renaming_a_deleted_category_fails_instead_of_reinserting_it` | Cumple |
| RF-19 | `categories/test_seed.py`: `test_migrations_leave_the_eleven_seed_categories`, `test_each_seed_category_passes_the_validation_service`, `test_seed_constant_matches_the_spec_letter_by_letter`. En desarrollo, las once categorías (ver Ejecución) | Cumple |
| RF-20 | `categories/test_seed.py`: `test_reapplying_the_seed_restores_names_without_duplicates`, `test_applying_the_seed_twice_keeps_one_row_per_slug` | Cumple |
| RF-21 | `categories/test_seed.py`: `test_reverting_the_seed_deletes_only_its_categories` | Cumple |
| RF-22 | `categories/test_seed.py`: `test_seed_is_one_reversible_atomic_operation`, `test_reverting_the_seed_issues_a_single_delete`, `test_seed_writes_to_the_connection_being_migrated` | Cumple en parte, como prevé la spec. La parte con datos dependientes la verifica la spec 005 |
| RF-23 | `categories/test_models.py`: `test_normalize_name`, `test_normalize_name_is_idempotent`, `test_normalize_name_counts_a_decomposed_accent_as_one_character`. `categories/test_services.py`: `test_name_is_stored_trimmed_and_composed`, `test_renamed_category_is_stored_trimmed_and_composed` | Cumple |
| Errores (RNF) | `users/test_services.py` y `categories/test_services.py`: `test_error_codes_match_the_plan_table`, `test_unknown_constraint_is_reported_without_details`, `test_integrity_error_without_details_is_not_swallowed`. `core/test_errors.py`: `test_translate_*` | Cumple |
| Hasher (RNF) | `config/test_settings.py`: `test_test_environment_uses_a_fast_password_hasher`, `test_real_environments_keep_the_default_password_hashers` | Cumple |

## Pruebas de mecanismo
Cada mutación se aplicó a mano (o con un `conftest.py` temporal sin versionar), se revirtió con `Edit` y el sha256 del fichero coincidió con el inicial. Los tests se citan sin parámetros.

**T1: informe del implementer de T1, no repetido.** Fuente: transcript local del subagente de T1 (sesión dd39c3a5, no versionado). Las seis mutaciones se hicieron sobre `apps/core/text.py` y `apps/core/errors.py` en la versión anterior al refactor `652199f`, que cambió `translate_validation_error`, y no se han repetido después. El informe da el número de tests que fallaron en cada una, no sus nombres:

| Mutación | Resultado |
|---|---|
| Quitar la deduplicación | 3 tests fallan |
| El no mapeado conserva el código de Django | 2 fallan |
| `DomainValidationError` con `params` | 1 falla |
| El traductor mezcla el mensaje con el código | 5 fallan |
| El validador lleva `params={"value": value}` | 1 falla |
| La detección de Cc excluye el tabulador | 1 falla |

**T2:** no se hicieron pruebas de mecanismo.

**T3** (`apps/users/services.py`, sha256 `005661e7…ef3811`)
- Quitar `or ""` de `_constraint_name`: falla `test_integrity_error_without_details_is_not_swallowed` (`DID NOT RAISE DomainValidationError`).
- `set_password` antes de `if errors:`: fallan `test_rejections_never_compute_the_hash` (contraseña ausente y de 129 caracteres) y `test_non_text_password_is_invalid` (`TypeError`).
- Quitar `transaction.atomic()`: fallan los dos casos de `test_concurrent_duplicate_is_translated_to_email_taken` (`IntegrityError` en bruto y `TransactionManagementError`).

**T4** (mismo fichero, ya con T4; sha256 `054a0079…c0efb74`)
- No restaurar el email de la instancia al rechazar: fallan 12 tests (9 emails inválidos, 2 duplicados y la carrera) de `test_change_user_email_*` y `test_concurrent_email_change_restores_the_instance`.
- Guardar sin `update_fields=["email"]`: fallan `test_change_user_email_does_not_overwrite_other_columns` (pisa `first_name`) y `test_change_user_email_of_a_deleted_user_fails_without_the_email` (el `save()` reinserta la fila).
- Hashear antes de validar solo en el flujo del superusuario: fallan tres tests, todos con `superuser` (`test_rejections_never_compute_the_hash` en dos casos y `test_non_text_password_is_invalid`); los de `user` pasan, lo que demuestra la parametrización.

**T5** (`services.py`, `base.py` y `log_redaction.py`; sha256 `054a0079…c0efb74`, `a1ec5515…e4c50` y `c4ce217a…ebe8add`; con un `conftest.py` temporal)
- `raise DomainValidationError(...) from exc` dentro del `except`: fallan 5 tests de `test_leaks.py` (duplicado en BD y duplicado exacto en BD, con `user` y `superuser`, y el duplicado en BD del cambio de email) por `__cause__` no nulo.
- `django.db.backends` a DEBUG: fallan 13 tests de `test_leaks.py` porque el SQL con el email llega a `caplog.text`; pasan los otros 9 (rechazos por longitud, Cc y formato, y el de `str` y `repr`).
- Límite: el guarda en ejecución de `test_logging.py` (`getEffectiveLevel() >= INFO`) no tiene mutación propia.

**T6:** sin mutaciones. Evidencia equivalente: el primer `models.py` de categorías tenía `/Z` en lugar de `\Z` en el patrón del slug, y lo detectaron 5 tests (`test_slug_field_definition` y los cuatro casos de `test_slug_with_valid_format_passes_validation`; 5 failed, 18 passed).

**T7** (`apps/categories/services.py`, sha256 `d7d2f189…8c6c29`; `models.py`, `6a197ecb…3d2be3`)
- Quitar la comprobación de tipo del nombre: falla `test_non_text_name_is_invalid` (`AttributeError`).
- Quitar la inmutabilidad: 5 tests (`test_slug_of_a_saved_category_cannot_change`, `test_changed_slug_reports_only_the_immutability` en sus tres casos y `test_changed_slug_and_name_errors_are_reported_together`).
- Quitar la reasignación `(__all__, name_taken)` del mapa: 4 tests (`test_name_matching_another_one_ignoring_case_is_taken` en sus tres casos y `test_decomposed_name_matches_the_composed_one`).
- Normalizar después de validar: 4 tests (`test_blank_name_is_empty`, `test_slug_and_name_errors_are_reported_together`, `test_name_of_60_characters_is_accepted` con el nombre descompuesto y `test_changed_slug_and_name_errors_are_reported_together`).
- Guardar sin `update_fields=["name"]`: falla `test_renaming_a_deleted_category_fails_instead_of_reinserting_it` (`DID NOT RAISE DatabaseError`).
- Quitar `or ""` de la copia de `_constraint_name`: falla `test_integrity_error_without_details_is_not_swallowed` (`DID NOT RAISE DomainValidationError`).

**T8** (`0002_seed_categories.py`, sha256 `fd1f86f0…835e`)
- `update_or_create` por `create`: fallan `test_reapplying_the_seed_restores_names_without_duplicates` y `test_applying_the_seed_twice_keeps_one_row_per_slug` (`IntegrityError` en `categories_category_slug_key`).
- `reverse_seed` con `.all().delete()`: falla `test_reverting_the_seed_deletes_only_its_categories`.
- `reverse_code` por `RunPython.noop`: falla `test_seed_is_one_reversible_atomic_operation`.
- Quitar `.using(...)` en las dos funciones: fallan los dos casos de `test_seed_writes_to_the_connection_being_migrated` (`DID NOT RAISE ConnectionDoesNotExist`).
- `Piragua` por `Piraguas` en `SEED`: 5 tests (`test_migrations_leave_the_eleven_seed_categories`, `test_each_seed_category_passes_the_validation_service` para `canoe`, los dos de RF-20 y `test_seed_constant_matches_the_spec_letter_by_letter`).
- Borrado fila a fila: falla `test_reverting_the_seed_issues_a_single_delete` (`assert 11 == 1`).

## Desviaciones respecto al plan
- Se añadió el ajuste de ruff para migraciones (`c5b5962`) porque las migraciones generadas incumplían E501 e I001.
- El refactor `652199f`: el mapa de traducción pasó a ser `(campo, código) → (campo destino, código)`, para que `email_taken` y `name_taken`, que Django devuelve en `__all__`, lleguen a su campo.
- `_save_guarded` devuelve los códigos en lugar de lanzar, para que el `raise` quede fuera del `except`.
- Tests no previstos en `tasks.md`: el del alias de conexión y el del único `DELETE` en la semilla, el del `LC_CTYPE` y los de formato del slug en el modelo.
- Convención nueva en `AGENTS.md`: los comentarios no citan identificadores de la spec.
- El `sqlmigrate` no muestra `users_user_email_key` ni `categories_category_slug_key` (el `UNIQUE` va en línea). Los nombres los fijan los tests y se han confirmado en la BD de desarrollo.

## Riesgos y notas
- **Fila borrada en `change_user_email` (aceptado):** si la fila del usuario ya no existe, se lanza `DatabaseError` sin el email y la instancia conserva el email nuevo, porque el error no pasa por la restauración.
- **Localización de la base de datos:** el test `test_accented_names_differing_only_in_case_are_rejected_by_the_database` protege la BD de test y el CI, pero no producción. La localización de la BD de producción hay que comprobarla en la spec de despliegue: con `LC_CTYPE` `C`, `Jardín` y `JARDÍN` no chocarían. Ese test no pasó por rojo: caracteriza el entorno y pasó desde el principio.
- **Semilla y nombre ajeno (aceptado, D6):** si alguien inserta por shell una categoría ajena cuyo nombre coincide, sin distinguir mayúsculas, con uno de la semilla, la migración falla de forma atómica y no cambia nada; hay que corregirlo a mano.
- **Tests con `transaction=True`:** vaciarían las tablas al terminar y la semilla desaparecería para los tests siguientes; habría que usar `serialized_rollback`. Hoy ningún test del proyecto lo hace.
- **Caracteres de formato (Cf) en el dominio del email (aceptado):** `reject_control_characters` solo rechaza la categoría Cc. Con Django 5.2.18, tras la NFKC, `validate_email` rechaza U+202E, U+200B y U+200D en la parte local, pero los acepta en el dominio. Los nombres de categoría tampoco rechazan Cf, pero solo entran por migración. Qué Cf rechazar, con cuidado de los legítimos como U+200D, se decide en el `/sdd-clarify` de la 005 (títulos y dominio del email).
- **Orden recorte y NFKC del email:** con `str.strip()` no se encontró una entrada que distinga recortar antes o después de NFKC, así que ese orden concreto no tiene test.
- **`NON_EMAIL_FIELDS`:** hoy equivale a excluir solo `password`; ningún test lo distingue. Protege si se añade un campo con validación estricta.
- **Aceptados en el plan:**
  - Las escrituras que se saltan el servicio (`create()`, `save()`, `update()`, `bulk_create()`) solo están cubiertas por las restricciones de BD.
  - `lower()` de Python y el de PostgreSQL pueden diferir en caracteres no ASCII; manda la restricción de BD.
  - El log del servidor de PostgreSQL incluye el valor duplicado en sus errores de unicidad (spec de despliegue).
  - `createsuperuser` interactivo muestra mensajes de Django en inglés.
  - `set_password` deja la contraseña en claro en `user._password` hasta el `save()`.

## Veredicto
Cumple. Los RF-1 a RF-23 tienen su test automático en verde (RF-22 en parte, como prevé la spec) y la BD de desarrollo contiene las once categorías. Los riesgos de arriba están aceptados, con dos pendientes de cerrar fuera de esta spec: la localización de la BD en producción y qué caracteres Cf se rechazan (se decide en la 005).
