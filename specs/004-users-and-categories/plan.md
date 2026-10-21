# Plan 004 — Usuarios y categorías
Spec: specs/004-users-and-categories/spec.md (aprobada)

## Resumen
Se crean dos apps de dominio, `apps/users` y `apps/categories`, y dos módulos de reglas compartidas en `apps/core`: texto y errores de dominio.
- Usuario: modelo propio sobre `AbstractUser`, con el email como identificador y sin `username`. Se instalan `django.contrib.contenttypes` y `django.contrib.auth`, y se fija `AUTH_USER_MODEL`, todo en el mismo commit que la migración inicial del usuario.
- Categoría: slug único e inmutable, y nombre en castellano único sin distinguir mayúsculas. La semilla de once categorías es una migración de datos con `reverse_code` explícito.
- Las escrituras pasan por servicios. Los servicios normalizan, validan con `full_clean`, traducen cualquier error a una lista cerrada de códigos sin valores y capturan el `IntegrityError` dentro de `transaction.atomic()`.
- No hay endpoints, serializers, vistas ni interfaz. No hay dependencias nuevas.
- Reparto del trabajo (restricción de la spec): el usuario escribe `models.py` en las dos apps, incluida la normalización (email en `UserManager.normalize_email`; nombre en `Category.normalize_name`). Claude escribe los tests (primero, también los de normalización), las migraciones, la semilla, los servicios y las funciones puras de `core`, y revisa línea a línea el código del usuario.
- La spec ya recoge D1, D2 y D3 y el RF-23 (nombre de categoría normalizado), por `/sdd-change` del 2026-10-21.

## Archivos y responsabilidades
| Archivo | Crea/Modifica | Responsabilidad | RF |
|---|---|---|---|
| backend/apps/core/text.py | Crea (Claude) | `contains_control_character` y el validador `reject_control_characters` (código `control_char`, sin `params`) | RF-4, RF-16 |
| backend/apps/core/errors.py | Crea (Claude) | `DomainValidationError` (solo campo y código) y la función pura `translate_validation_error` | RF-12, RNF Errores |
| backend/apps/users/__init__.py, apps.py | Crea (Claude) | Paquete y `UsersConfig` | RF-1 |
| backend/apps/users/models.py | Crea (usuario) | `User` y `UserManager`: `normalize_email` (recorte, NFKC y minúsculas enteras; la reutilizará el login), `get_by_natural_key` normaliza, y `create_user` y `create_superuser` delegan en el servicio | RF-1, RF-2, RF-5, RF-7, RF-12 (`__str__`) |
| backend/apps/users/migrations/0001_initial.py | Crea (Claude, `makemigrations`) | Tabla `users_user` y sus restricciones | RF-5, RF-7 |
| backend/apps/users/services.py | Crea (Claude) | `create_user`, `create_superuser` y `change_user_email`; mapa de códigos; captura de `IntegrityError` | RF-2 a RF-12 |
| backend/apps/users/tests/ (test_emails, test_models, test_services, test_superuser, test_leaks) | Crea (Claude) | Tests por capa | RF-1 a RF-12 |
| backend/apps/categories/__init__.py, apps.py | Crea (Claude) | Paquete y `CategoriesConfig` | RF-13 |
| backend/apps/categories/models.py | Crea (usuario) | `Category` (T6) y `Category.normalize_name`, recorte y NFC (T7) | RF-13, RF-15, RF-17, RF-23 |
| backend/apps/categories/migrations/0001_initial.py | Crea (Claude, `makemigrations`) | Tabla `categories_category` y sus restricciones | RF-15, RF-17 |
| backend/apps/categories/migrations/0002_seed_categories.py | Crea (Claude) | `SEED`, `apply_seed`, `reverse_seed` y `RunPython(apply_seed, reverse_seed)` | RF-19 a RF-22 |
| backend/apps/categories/services.py | Crea (Claude) | `save_category`; mapa de códigos | RF-13 a RF-18, RF-23 |
| backend/apps/categories/tests/ (test_models, test_services, test_seed) | Crea (Claude) | Tests por capa | RF-13 a RF-23 |
| backend/apps/core/tests/ (test_text, test_errors) | Crea (Claude) | Tests de las funciones puras | RF-4, RF-12, RF-16 |
| backend/config/settings/base.py | Modifica | `INSTALLED_APPS` (contenttypes, auth, users y, en T6, categories), `AUTH_USER_MODEL = "users.User"` y `LOGGING` con `django.db.backends` a INFO (D5) | RF-1, RF-12 |
| backend/config/log_redaction.py | Modifica | Añade `django.db.backends` a INFO a la configuración de producción (D5) | RF-12 |
| backend/config/settings/test.py | Modifica | `PASSWORD_HASHERS` rápido, solo en test (D7) | (velocidad de la suite) |
| backend/config/tests/test_logging.py | Crea (Claude) | Nivel de `django.db.backends` en los tres entornos | RF-12 |
| docs/architecture.md | Modifica (T9) | Añade `core/text.py`, `core/errors.py`, `users` y `categories` al árbol | — |
| specs/004-users-and-categories/validation.md | Crea (T9) | Evidencia RF por RF y migración de la BD de desarrollo | todos |

No se tocan `MIDDLEWARE` (no hace falta `AuthenticationMiddleware`; `test_http_hardening.py:30` solo exige `CommonMiddleware`), `urls.py`, `env.py`, `docker-compose.yml` ni las dependencias.

## Modelo de datos y migraciones

### Usuario (`users.User`, tabla `users_user`). Lo escribe el usuario
- Hereda de `AbstractUser`: `password` (el hash, `varchar(128)`, no la contraseña), `last_login`, `is_superuser`, `first_name`, `last_name`, `is_staff`, `is_active`, `date_joined`, `groups` y `user_permissions`.
- `username = None`.
- `email = EmailField(max_length=254, unique=True, validators=[reject_control_characters])`, sin `blank=True` (AbstractUser lo trae con `blank=True`).
  - `unique=True` lo exige `auth.E003`.
  - Hace que el duplicado exacto salga como error de campo `unique`.
- `USERNAME_FIELD = "email"`, `EMAIL_FIELD = "email"` y `REQUIRED_FIELDS = []` (si no, `auth.E002`).
- `objects = UserManager()`, que hereda de `BaseUserManager` y no lleva `use_in_migrations`.
- `Meta.constraints = [UniqueConstraint(Lower("email"), name="users_user_email_lower_unique", violation_error_code="email_taken")]`.
- `__str__` devuelve `f"User {self.pk}"` (el de Django devuelve el email). Orden de miembros según DJ012.

### Categoría (`categories.Category`, tabla `categories_category`). La escribe el usuario
- `id` con `BigAutoField` (`DEFAULT_AUTO_FIELD`). La 005 apunta a él con `PROTECT`.
- `slug = CharField(max_length=50, unique=True, validators=[RegexValidator(r"\A[a-z0-9]+(?:-[a-z0-9]+)*\Z", code="invalid")])`. No es `SlugField`, porque `validate_slug` admite mayúsculas y `_`. Se usa `[0-9]` y no `\d`, y `\Z` y no `$`.
- `name = CharField(max_length=60, validators=[reject_control_characters])`.
- `Meta.constraints = [UniqueConstraint(Lower("name"), name="categories_category_name_lower_unique", violation_error_code="name_taken")]`.
- `__str__` devuelve `self.name`.

### Con la opción (b) de D1
`email` y `name` pasan a `TextField`, y `slug` a `CharField` sin `max_length` o a `TextField`. Cada uno lleva su `CheckConstraint(condition=Q(...Length...), name=...)`; en 5.2 se usa `condition=`, no `check=`.

### Migraciones
- `users/0001_initial`: la genera `makemigrations users` (depende de `auth`). Se crea en el mismo commit que `AUTH_USER_MODEL` y la instalación de auth y contenttypes.
- `categories/0001_initial`: la genera `makemigrations categories`.
- `categories/0002_seed_categories`: se escribe a mano.
  - Constante `SEED` con los once pares `(slug, nombre)` de RF-19.
  - `apply_seed(apps, schema_editor)` usa `apps.get_model("categories", "Category")`, `.using(schema_editor.connection.alias)` y `update_or_create(slug=..., defaults={"name": ...})`.
  - `reverse_seed` hace `filter(slug__in=SEED_SLUGS).delete()` con un único `delete()` de QuerySet. La migración queda atómica (`atomic` por defecto). Nunca se usa `RunPython.noop`.
- Órdenes:
  - Se generan con `docker compose exec -u "$(id -u)" backend python manage.py makemigrations <app>` y después `ruff format` con el mismo `-u`.
  - El SQL de las restricciones se revisa con `sqlmigrate`.
  - `makemigrations` y `sqlmigrate` solo leen la BD de desarrollo.
- Nadie ejecuta `migrate` en la BD de desarrollo sin el OK explícito del usuario en ese momento (T9). La BD de test se crea desde cero en cada ejecución de pytest.
- `test_migrations.py` (RF-7 de la 002) vigila que cada modelo nuevo tenga su migración.

## Contrato de API
No aplica: la spec no expone endpoints ni serializers, así que no hay anónimo, usuario ni propietario que declarar.

El contrato interno lo forman las firmas de los servicios y la forma de `DomainValidationError` (ver Lógica). Las specs de API lo traducirán a HTTP según las "Reglas para specs posteriores".

## Lógica

### Funciones puras (sin BD, sin red, sin hora)
- `core.text.contains_control_character(text: str) -> bool` (Claude): `any(unicodedata.category(c) == "Cc" for c in text)`.
- `core.text.reject_control_characters(value)` (Claude): validador de Django que lanza `ValidationError("control_char", code="control_char")` sin `params`. Hace falta aunque exista `EmailValidator`, porque este acepta caracteres `\x01`-`\x1f` dentro de una parte local entre comillas.
- `UserManager.normalize_email(raw: str) -> str` (usuario, classmethod que sustituye al de `BaseUserManager`): `str.strip()` (D3), después NFKC (D2) y después `lower()`, en este orden. NFKC puede producir mayúsculas (`℡` pasa a `TEL`). El `clean()` heredado vuelve a aplicar NFKC, y sobre este resultado no cambia nada.
- `Category.normalize_name(raw: str) -> str` (usuario, staticmethod): `str.strip()` (D3) y después NFC (D2).
- `core.errors.translate_validation_error(error, codes) -> dict[str, list[str]]`:
  - Recorre `error.error_dict` y traduce cada par `(campo, código de Django)` con el mapa `codes`.
  - Descarta mensajes y `params` (llevan `{"value": ...}`) y elimina duplicados conservando el orden.
  - Un par que no está en el mapa pasa a `("__all__", "validation_failed")`.

### Error de dominio
`core.errors.DomainValidationError(ValidationError)` se construye con `{campo: [código, ...]}`.
- Cada mensaje es el propio código y no lleva `params`. `message_dict` devuelve `{campo: [códigos]}`, y `str()` y `repr()` solo contienen campos y códigos.
- Es subclase de `ValidationError` para que `createsuperuser` la convierta en `CommandError` sin traceback.
- Los servicios la lanzan siempre fuera de cualquier bloque `except`, de modo que `__context__` y `__cause__` quedan a `None`.

### Lista cerrada de códigos
| Campo | Código | Cuándo | Origen |
|---|---|---|---|
| email | `email_empty` | Vacío tras recortar, o `None` | `blank` / `required` |
| email | `email_invalid` | Sin formato de email, o no es texto | `invalid` / tipo |
| email | `email_control_char` | Carácter Cc tras recortar | `control_char` |
| email | `email_too_long` | Más de 254 caracteres | `max_length` |
| email | `email_taken` | Coincide con otro usuario | `unique`, `__all__`/`email_taken` o `IntegrityError` de `users_user_email_key` o `users_user_email_lower_unique` |
| password | `password_required` | `None` o `""` | Servicio |
| password | `password_invalid` | No es texto | Servicio |
| password | `password_too_long` | Más de 128 caracteres | Servicio |
| slug | `slug_empty` | Vacío | `blank` |
| slug | `slug_invalid` | Fuera del formato de RF-14, o no es texto | `invalid` / tipo |
| slug | `slug_too_long` | Más de 50 caracteres | `max_length` |
| slug | `slug_taken` | Ya existe | `unique` o `IntegrityError` de `categories_category_slug_key` |
| slug | `slug_immutable` | Cambio del slug de una categoría guardada | Servicio |
| name | `name_empty` | Vacío tras recortar | `blank` |
| name | `name_invalid` | No es texto | Tipo |
| name | `name_control_char` | Carácter Cc tras recortar | `control_char` |
| name | `name_too_long` | Más de 60 caracteres | `max_length` |
| name | `name_taken` | Coincide sin distinguir mayúsculas con otra | `__all__`/`name_taken` o `IntegrityError` de `categories_category_name_lower_unique` |
| `__all__` | `constraint_violated` | `IntegrityError` de una restricción no reconocida | Servicio |
| `__all__` | `validation_failed` | Código de Django no mapeado (no debería ocurrir) | Traductor |

- Un mismo campo puede llevar varios códigos. Por ejemplo, un tabulador interno en el email da `email_invalid` y `email_control_char`.
- Cada servicio expone sus códigos como constantes en inglés, y un test compara el conjunto con esta tabla.

### Servicios de usuarios (`apps/users/services.py`)
Firmas:
- `create_user(*, email, password) -> User`
- `create_superuser(*, email, password) -> User`
- `change_user_email(*, user, email) -> User`

Las firmas son solo con nombre y no aceptan `**extra_fields`. Pasar `is_staff`, `is_superuser`, `groups` o `user_permissions` da `TypeError` (RF-10 por construcción).

Flujo de creación:
1. Contraseña: si es `None` o `""`, `password_required`; si no es `str`, `password_invalid`; si `len(password) > 128`, `password_too_long`. No se recorta.
2. Email: si es `None`, se trata como `""`; si no es `str`, `email_invalid`; en otro caso se aplica `User.objects.normalize_email`.
3. Se construye `User(email=..., is_staff=X, is_superuser=X)`: `X` es `False` en `create_user` y `True` en `create_superuser`.
4. `user.full_clean(exclude={"password"})`. Los errores se traducen y se suman a los de la contraseña.
5. Si hay algún error, se lanza `DomainValidationError` sin haber calculado el hash (RF-9) ni guardado nada.
6. Si no hay errores, `user.set_password(password)` y después el guardado protegido.

`change_user_email`:
- Normaliza y valida igual.
- Si se rechaza, devuelve la instancia a su email anterior y no toca la BD.
- Cambiar el email al propio con otras mayúsculas no es un duplicado.

Guardado protegido (patrón que reutilizará la 005):
```python
violated = None
try:
    with transaction.atomic():
        instance.save()
except IntegrityError as exc:
    violated = _constraint_name(exc)  # exc.__cause__.diag.constraint_name
if violated is not None:
    raise DomainValidationError(_codes_for_constraint(violated))
```
- No se registra en el log ni se encadena el error.
- Una restricción desconocida da `constraint_violated`.

`UserManager` (lo escribe el usuario):
- `get_by_natural_key(email)` aplica `self.normalize_email` y busca por igualdad exacta, no con `iexact`. Si el valor no es `str`, lanza `DoesNotExist`.
- `create_user` y `create_superuser` solo delegan en el servicio, con un import diferido dentro del método para evitar el ciclo entre `models` y `services`.
- `createsuperuser --noinput` sin `DJANGO_SUPERUSER_PASSWORD` llama a `create_superuser(email=..., password=None)`. El servicio responde `password_required` y el comando lo convierte en `CommandError` (RF-8).

### Servicio de categorías (`apps/categories/services.py`)
`save_category(category: Category) -> Category`:
1. Tipos: si `slug` o `name` no son `str`, `slug_invalid` o `name_invalid`. Después, `category.name = Category.normalize_name(category.name)`. El slug no se recorta.
2. RF-18: si `category.pk` existe y el slug guardado (una lectura con `values_list`) es distinto, `slug_immutable`.
3. `full_clean()`, traducción, el mismo guardado protegido y `DomainValidationError`.

No hay creación ni edición de categorías en ejecución (fuera de alcance). El servicio es el punto de validación que exigen RF-14 a RF-18 y el que usan los tests.

### Lo que salta la validación (riesgo aceptado)
`User.objects.create()`, `User(...).save()`, `update()` y `bulk_create()` se saltan normalización y validación. Las restricciones de BD cubren unicidad y longitud; lo demás queda a la regla de que se escribe por los servicios.

## Interfaz
No aplica: la spec no tiene pantallas. No hay verificación en navegador (lo dicen sus criterios de finalización).

## Decisiones
Las filas marcadas necesitan su elección antes de aprobar el plan.

| Decisión | Opciones | Elegida | Qué evita | Coste |
|---|---|---|---|---|
| D1. Rechazo de longitud en BD (RF-5, RF-15, RF-17) | (a) `varchar(N)`, que da `DataError`; la spec pasa a decir "error de base de datos: de integridad en unicidad, de datos en longitud" vía `/sdd-change`. (b) `TextField` + `CheckConstraint` con `Length`, que da `IntegrityError` y no cambia la spec. | (a), aceptada por el usuario | (a): que el DETAIL de un CHECK fallido (incluye la fila entera: email y hash) aparezca en errores y logs (RF-12); constraints extra. | (a): un `/sdd-change` (Definiciones y Criterios de finalización) antes de T1. (b): más esquema y más superficie de fuga. |
| D2. Forma Unicode | (a) Email en NFKC (como `AbstractBaseUser.clean()` y `UsernameField` del login) y nombre en NFC. (b) NFKC en los dos. (c) Sin normalización propia: el email recibe NFKC igualmente después de validar la longitud, y un nombre en NFD con 60 letras con tilde supera `varchar(60)`. | (a), aceptada por el usuario, en el mismo `/sdd-change` que D1 ("longitud contada tras normalizar") | (a): que la longitud se valide sobre un texto distinto del que se guarda; que "60 con tildes" falle si llega en NFD; cambiar el significado del nombre (NFKC pliega ligaduras y anchos). | `/sdd-change`. Los homóglifos (cirílico frente a latino) siguen siendo un riesgo aceptado. |
| D3. Recorte | (a) `str.strip()`: espacio en blanco Unicode, incluidos NBSP, `\x85` y `\x1c`-`\x1f`. (b) `strip(" \t\n\r")`, literal a la spec. | (a), aceptada por el usuario, aclarando la definición de "texto recortado" en el mismo `/sdd-change` | (a): nombres duplicados que solo difieren en un NBSP al borde. | Se aparta de la lectura literal; los Cc del borde se eliminan en vez de rechazarse. |
| D4. Apps | (a) `users` y `categories` separadas. (b) Una sola app (`accounts` o `catalog`). (c) `Category` dentro de la futura app de bienes. | (a), aceptada por el usuario | Mover un modelo entre apps más tarde (caro, con FK `PROTECT` desde la 005); acoplar categorías a bienes antes de que existan. | Dos apps y dos migraciones iniciales. |
| D5. Log de `django.db.backends` (RF-12) | (a) No tocar la configuración y fijarla con un test en tiempo de ejecución. (b) `LOGGING` explícito en `base.py` y en `build_production_logging` con `django.db.backends` a INFO, más un test estático en los tres entornos. | (b), aceptada por el usuario | Que alguien baje ese logger a DEBUG y el SQL con parámetros (email, hash) llegue al log. | Dos ediciones pequeñas. El `LOGGING` de base, que solo tiene `loggers`, debe convivir con el `DEFAULT_LOGGING` de Django [S]. |
| D6. La semilla choca por nombre con otra categoría | (a) Riesgo aceptado: la migración falla atómicamente y no cambia nada. (b) Resolver por nombre dentro de la semilla. (c) Comprobar antes y fallar con un mensaje propio. | (a), aceptada por el usuario | Lógica extra en una migración para un caso que solo se da insertando por shell, porque las categorías solo cambian por migración. | Un operador tendría que corregir a mano. |
| D7. Hasher en test | (a) `MD5PasswordHasher` solo en `settings/test.py`. (b) El hasher por defecto (PBKDF2). | (a), aceptada por el usuario | Segundos de PBKDF2 por cada usuario creado en la suite [NV]. | RF-3 se prueba con el hasher de test; un test comprueba que `base` y `production` no fijan `PASSWORD_HASHERS`. |
| D8. BD de desarrollo | (a) `migrate` incremental (con OK en el momento). (b) Recrearla desde cero (`down -v`, que borra los datos de desarrollo). | (a), aceptada por el usuario; "desde cero" se demuestra con la BD de test, que se recrea en cada ejecución | Borrar datos de desarrollo sin necesidad. | La BD de desarrollo no se prueba literalmente desde cero. |
| Unicidad del email | (a) `unique=True` + `UniqueConstraint(Lower)`. (b) Solo `Lower` y silenciar `auth.E003`. (c) CITEXT o colación no determinista. | (a) | `auth.E003`, que haría fallar `manage.py check` (`test_entrypoints.py:49`); campos obsoletos desde 4.2. | Dos índices sobre `email`. |
| Unicidad del nombre de categoría | (a) `UniqueConstraint(Lower("name"), violation_error_code="name_taken")` y traducción por código. (b) Comprobación manual en `clean()`. | (a) | Duplicar la regla; `iexact` usa `UPPER` y no coincide con el índice. | El error llega en `__all__` y el mapa lo lleva a `name`. |
| Formato del slug | (a) `CharField` + `RegexValidator` estricto. (b) `SlugField` + validador extra. | (a) | Dos validadores con reglas distintas sobre el mismo campo. | Ninguno relevante. |
| Clave de `Category` | (a) `id` + `slug` único. (b) `slug` como clave primaria. | (a) | Que cambiar el slug cree otra fila; FK de la 005 sobre un texto. | Una columna más. |
| Dónde van las reglas de usuario | (a) Servicios y manager fino que delega. (b) Lógica en el manager. (c) `save()` o `full_clean()` del modelo sobrescritos. | (a) | Reglas dentro del modelo que escribe el usuario; validación implícita en cada `save()`. | Import diferido en el manager. |
| Tipo del error de dominio | (a) Subclase de `ValidationError` que solo lleva códigos. (b) Excepción propia independiente. (c) El `ValidationError` crudo de `full_clean`. | (a) | (c) filtra `params={"value": ...}`; (b) haría que `createsuperuser` acabe en traceback. | Acopla el dominio a la excepción de Django (aceptable en este proyecto). |
| Firma de `create_user` | (a) Solo con nombre, sin `**extra_fields`. (b) `**extra_fields` rechazando los permisos. | (a) | Conceder permisos por descuido; listas negras incompletas. | No se pueden pasar `first_name` ni `last_name` (la spec no los usa). |
| Traducción del `IntegrityError` | (a) Por `diag.constraint_name`. (b) Analizando el mensaje. (c) Un código genérico siempre. | (a) | Leer un mensaje que contiene el valor; perder `email_taken`. | Los nombres automáticos de `unique=True` (`*_key`) quedan fijados por test. |
| Detección de caracteres de control | (a) En `apps/core`. (b) Duplicada en cada app. | (a) | Dos implementaciones de la misma definición (la 005 la reutiliza: "como en la spec 004"). | Es una sola regla de la spec, no una abstracción especulativa. |
| Dónde vive la normalización (decidido por el usuario) | (a) En el dominio que la usa: `UserManager.normalize_email` y `Category.normalize_name`, escritas por el usuario. (b) Funciones puras en `core` y `users/emails.py`, escritas por Claude. | (a) | Separar la regla de su modelo; que la lógica de dominio la escriba Claude. | El recorte (`str.strip()`) se repite en dos sitios: es una línea, no se extrae hasta la tercera repetición. |
| Tests de la semilla | (a) Importar la migración y llamar a `apply_seed` y `reverse_seed` con las apps históricas en un test `django_db` normal. (b) `django_db(transaction=True)` + `migrate` atrás y adelante. (c) `django-test-migrations`. | (a) | (b) trunca tablas y deja la semilla vacía para los tests siguientes; (c) es una dependencia nueva. | No ejecuta el `migrate` real hacia atrás; un test aparte comprueba que la operación registra `reverse_seed`. |
| `@sensitive_variables` | Sí / No | No | Decorar funciones que no son vistas: sin `ADMINS` ni `DEBUG`, el informe técnico no se usa. | Ninguno; se revisa en la spec de API. |

## Blast radius
- `base.py`: `INSTALLED_APPS`, `AUTH_USER_MODEL` y `LOGGING`.
  - `manage.py check` en desarrollo (`test_entrypoints.py:49`) pasa a ejecutar los checks de auth. Falla si falta `REQUIRED_FIELDS = []` o `unique=True`.
- `log_redaction.py`: una entrada más en `loggers`, sin handlers propios. `test_only_the_redacting_handler_is_configured` solo recorre `LOGGER_NAMES` y el raíz, así que sigue valiendo.
- `settings/test.py`: `PASSWORD_HASHERS`. Los tests de settings existentes no lo miran.
- `test_migrations.py`: desde T2 vigila `users`, y desde T6 `categories`.
- `auth` añade `post_migrate` (permisos y contenttypes) a la creación de la BD de test, que tardará algo más.
- `test_http_hardening.py`: las sesiones siguen funcionando sin `AuthenticationMiddleware`.
- `test_tooling.py::test_ruff_accepts_the_backend_code`: las migraciones generadas deben pasar `ruff format` (Django no las formatea con ruff).
- BD de desarrollo: queda con migraciones sin aplicar desde T2 hasta T9 (`runserver` avisa y no falla). `sessions.0001` y `core.0001` no dependen de auth, así que no habrá `InconsistentMigrationHistory` [S].
- Backend en marcha: `docker compose restart backend` tras añadir cada app (skill django-drf).
- Spec 005: FK a `settings.AUTH_USER_MODEL` y a `categories.Category` con `PROTECT`. `reverse_seed` usa `delete()` de QuerySet para heredar ese `PROTECT` (RF-22).

## Riesgos
| Riesgo | Mitigación |
|---|---|
| Escrituras que se saltan el servicio (`create()`, `save()`, `update()`, `bulk_create()`) | Las restricciones de BD cubren unicidad y longitud; los tests documentan el camino soportado; regla para specs posteriores: se escribe por servicios. |
| `lower()` de Python y `lower()` de PostgreSQL difieren en algunos caracteres no ASCII (depende de la colación) | La restricción `Lower` de BD es el árbitro; si choca, el servicio la traduce a `email_taken`. |
| Nombres automáticos de `unique=True` (`users_user_email_key`, `categories_category_slug_key`) | Se confirman con `sqlmigrate` y quedan fijados por los tests de RF-7 y RF-15. |
| Un test futuro con `transaction=True` vaciaría la semilla para los tests siguientes | Los tests de semilla no lo usan; se anota en la skill django-drf al cerrar la spec. |
| La semilla falla si dos de sus nombres están intercambiados entre slugs en la BD | Riesgo aceptado (D6): falla atómicamente sin cambios. |
| El log del servidor PostgreSQL incluye el valor duplicado | Fuera de alcance; spec de despliegue (dudas abiertas de la spec). |
| `createsuperuser` interactivo muestra mensajes propios de Django en inglés | Es una herramienta de desarrollo; aceptado. |
| `caplog` a DEBUG podría capturar SQL con parámetros | `django.db.backends` fijado a INFO (D5); con `DEBUG=False` en test no hay cursor de depuración. |
| `set_password` guarda la contraseña en claro en `user._password` hasta el `save()` | Solo se llama tras validar; nunca se registra ni se serializa. |

## Estrategia de tests
| RF | Cómo se verifica (pytest) |
|---|---|
| RF-1 | `users/tests/test_models.py`: `USERNAME_FIELD == "email"`, `get_field("username")` lanza `FieldDoesNotExist`, `REQUIRED_FIELDS == []`, `get_user_model() is User` y `AUTH_USER_MODEL == "users.User"`. `test_services.py`: `authenticate(email="ANA@Correo.ES", password=...)` devuelve el usuario. `manage.py check` en desarrollo (test existente). |
| RF-2 | `test_emails.py`: `" Ana@Correo.ES\n"` da `"ana@correo.es"` y casos NFKC y de recorte (D2, D3). `test_services.py`: el valor guardado tras `create_user` y `change_user_email`; `get_by_natural_key` con otras mayúsculas encuentra al usuario. |
| RF-3 | `test_services.py`: `user.password != raw`, `identify_hasher(user.password)` funciona y `check_password(raw)` es `True`; el valor recibido no aparece en ningún campo guardado. |
| RF-4 | `test_services.py`, parametrizado para crear y para cambiar el email: `""`, `"   "`, `None`, `"ana"`, `"ana@"`, `"a\x00na@x.es"`, `"an\ta@x.es"`, `"an\na@x.es"`, `'"a\x01b"@x.es'` y un valor no texto. Esperan `email_empty`, `email_invalid` o `email_control_char`, y que no se cree ninguna fila. `core/tests/test_text.py` cubre las funciones puras. |
| RF-5 | Validación: 254 caracteres se acepta (dominio con etiquetas de 63 como máximo) y 255 da `email_too_long`. BD (`test_models.py`): `User(email=255).save()` dentro de `atomic` espera `DataError` (o `IntegrityError` si D1 = b). |
| RF-6 | `Ana@Correo.ES` y después `ana@correo.es` dan `email_taken`; cambiar a `ANA@correo.es` cuando existe `ana@correo.es` da `email_taken`; cambiar al propio email con otras mayúsculas se acepta. |
| RF-7 | `test_models.py`: dos `User(...).save()` con `Ana@Correo.ES` y `ana@correo.es`, sin pasar por el servicio, dentro de `atomic`; espera `IntegrityError` con `__cause__.diag.constraint_name == "users_user_email_lower_unique"`. Sin hilos ni `serialized_rollback`. `test_services.py`: con `User.full_clean` anulado por `monkeypatch` (simula la carrera), el servicio devuelve `email_taken` y la conexión sigue usable. |
| RF-8 | `create_user` y `create_superuser` con `None` y `""` dan `password_required` y no crean ninguna fila. `test_superuser.py`: `call_command("createsuperuser", interactive=False, email=...)` sin `DJANGO_SUPERUSER_PASSWORD` (`monkeypatch.delenv`) lanza `CommandError` y no crea ninguna fila. |
| RF-9 | 128 caracteres se acepta y 129 da `password_too_long`. `django.contrib.auth.base_user.make_password` parcheado para fallar si se llama: no se llama ante ningún rechazo. |
| RF-10 | `create_user` deja `is_staff` e `is_superuser` en `False`, sin grupos ni permisos. `create_user(..., is_staff=True)` lanza `TypeError` y no crea ninguna fila. |
| RF-11 | `create_superuser` deja `is_staff` e `is_superuser` en `True`. `createsuperuser --noinput` con `DJANGO_SUPERUSER_PASSWORD` por `monkeypatch` crea un superusuario. |
| RF-12 | `test_leaks.py`, con centinelas `*_SENTINEL` y `caplog.set_level(DEBUG)`. Para cada rechazo (duplicado en validación, duplicado en BD, email largo, Cc, inválido, contraseña larga, contraseña ausente) comprueba que ni el email (recibido y normalizado) ni la contraseña aparecen en `str()`, `repr()`, `traceback.format_exception()`, `message_dict` ni `caplog.text`, y que `__context__` y `__cause__` son `None`. `str(user)` no contiene el email. `config/tests/test_logging.py`: `django.db.backends` a INFO en los tres entornos y `getEffectiveLevel() >= INFO` en ejecución. |
| RF-13 | `categories/tests/test_models.py`: `slug` es único y el modelo tiene `name`. `test_services.py`: `save_category` crea una categoría válida (`slug="garden"`, `name="Jardín"`). |
| RF-14 | Parametrizado: `Ebike`, `e bike`, `-ebike`, `ebike-`, `e--bike`, `e_bike` y `""` dan `slug_invalid` o `slug_empty`; `e-bike-2` se acepta. |
| RF-15 | 50 caracteres se acepta, 51 da `slug_too_long` y `pool` repetido da `slug_taken`. BD: slug repetido con `objects.create` da `IntegrityError` (`categories_category_slug_key`); 51 caracteres da `DataError` (D1). |
| RF-16 | `"   "` da `name_empty`; tabulador interno y `\x00` dan `name_control_char`. |
| RF-17 | `"  piscina  "` con `Piscina` existente da `name_taken`; 60 caracteres con tildes (en NFC y en NFD si D2 = a) se acepta; 61 da `name_too_long`. BD: `Piscina` y `PISCINA` dan `IntegrityError` (`categories_category_name_lower_unique`); 61 caracteres da `DataError` (D1). |
| RF-18 | Cambiar el slug de una categoría guardada da `slug_immutable` y la BD conserva el anterior; cambiar solo el nombre se acepta. |
| RF-19 | `test_seed.py`: tras la migración de la BD de test, las once categorías existen con el slug y el nombre literales de la spec (lista escrita en el test, no importada de `SEED`); cada entrada de la semilla pasa la validación de `save_category`. |
| RF-20 | Con las apps históricas (`MigrationLoader(connection).project_state(("categories", "0002_seed_categories")).apps`) y un `schema_editor` sustituto que solo aporta `.connection`: se renombra `pool` y se borra `kayak`; tras `apply_seed`, hay once, sin duplicados, y `pool` vuelve a llamarse `Piscina`. |
| RF-21 | Con una categoría ajena (`garden`), tras `reverse_seed` no queda ningún slug de la semilla y `garden` sigue existiendo. |
| RF-22 | Parcial en la 004 (lo prevé la spec): la operación es `RunPython(apply_seed, reverse_seed)`, `Migration.atomic` es `True` y `reverse_seed` borra con un único `delete()` de QuerySet (el recolector comprueba `PROTECT` antes de borrar nada). El caso con datos dependientes lo verifica la 005. |
| RF-23 | `categories/tests/test_models.py`: `Category.normalize_name` recorta con `str.strip()` (incluido NBSP), pasa a NFC y no cambia mayúsculas. `test_services.py`: `save_category` con `" Jardín "` y con `Jardín` en NFD guarda `"Jardín"` en NFC, tanto al crear como al cambiar el nombre. |
| RNF Fechas | `date_joined` tiene zona horaria y desplazamiento UTC 0. |
| RNF Errores | El conjunto de códigos de cada servicio coincide con la tabla de Lógica; `translate_validation_error` descarta `params` y envía lo no mapeado a `validation_failed`. |
| RNF Hasher | `base` y `production` no definen `PASSWORD_HASHERS` (D7). |

En cada test que protege un mecanismo (captura del `IntegrityError`, descarte de `params`, nivel del logger, `make_password` no llamado) se hace la prueba de mecanismo de la skill. Se usa un test temporal sin commitear que parchea el mecanismo, sin editar ficheros versionados fuera de la tarea.

## Afirmaciones no verificadas
- [V en Django 5.2.17 del `.venv` del host; el contenedor usa 5.2.18, se supone igual]:
  - `AbstractBaseUser.clean()` aplica NFKC a `USERNAME_FIELD`.
  - `full_clean` deja fuera de `validate_unique` y `validate_constraints` los campos que ya tienen errores.
  - Un `UniqueConstraint` de expresiones lanza el error con `violation_error_code` en `__all__`.
  - `createsuperuser --noinput` pasa `password=None` y convierte `ValidationError` en `CommandError`.
  - `EmailValidator` acepta `\x01`-`\x1f` en una parte local entre comillas y limita a 320 caracteres.
- [S] Un `varchar(N)` excedido lanza `django.db.utils.DataError` (`StringDataRightTruncation`) con un mensaje sin el valor.
- [S] `IntegrityError.__cause__.diag.constraint_name` está disponible con psycopg 3.3.
- [S] PostgreSQL llama `users_user_email_key` y `categories_category_slug_key` a las restricciones de `unique=True`. Se confirma con `sqlmigrate` en T2 y T6.
- [S] `migrate` incremental en la BD de desarrollo aplica contenttypes, auth, users y categories sin `InconsistentMigrationHistory`.
- [S] Un `LOGGING` en `base.py` con solo `loggers` mantiene operativos los handlers de `DEFAULT_LOGGING` en desarrollo.
- [S] `MigrationLoader.project_state(...).apps` da el modelo histórico, y un objeto con solo `.connection` basta como `schema_editor` para `apply_seed` y `reverse_seed`.
- [S] El DDL de PostgreSQL es transaccional: un fallo en `reverse_seed` revierte la migración completa.
- [S] Con `DEBUG=False` (test) no hay `CursorDebugWrapper`; en desarrollo, con `DEBUG=True`, el SQL va a DEBUG y lo filtra el nivel INFO.
- [S] Las fixtures `admin_user` y `django_user_model` de pytest-django llaman a `create_superuser` solo con argumentos con nombre.
- [S] `post_migrate` de auth (permisos y contenttypes) no interfiere con la semilla ni con sus tests.
- [NV] Coste de PBKDF2 por usuario dentro del contenedor (justifica D7).

## Skills que aplican
- sdd.
- django-drf: capas, migraciones (preguntar antes de crear o aplicar), `restart` al añadir apps y tests por capa en `apps/<app>/tests/`.
