# Plan 005 — Bienes y privacidad de la ubicación
Spec: specs/005-assets-and-location-privacy/spec.md (aprobada)

## Resumen
- Nueva app `apps/assets`. Contiene:
  - el modelo `Asset`;
  - una función pura de aproximación (`location.py`);
  - reglas puras de validación de campos (`rules.py`);
  - el servicio de escritura (`services.py`), con dos funciones: `create_asset` y `update_asset`.
- El guardado protegido está copiado en users y categories. Se extrae a `apps/core/db.py` con el nombre `run_guarded`:
  - ejecuta un bloque entero dentro de `transaction.atomic()`;
  - al terminar el bloque fuerza la comprobación de las restricciones diferidas y después las pone en diferidas, como `connection.check_constraints()` de Django en PostgreSQL (D3);
  - traduce el `IntegrityError` por el nombre de la restricción;
  - users y categories pasan a usarlo sin cambiar su comportamiento.
- La ubicación pública se deriva en el servicio, dentro de la transacción que bloquea la fila (`select_for_update`). Se deriva al crear y cuando cambian la exacta o el radio (D6).
- Proyección EPSG:4326 → EPSG:3035 con GDAL de `django.contrib.gis`, con orden de ejes tradicional y sin dependencias nuevas. Los tests miden las distancias geodésicas con `ST_Distance` sobre geography.
- No hay endpoints, serializers, vistas ni interfaz.
- T1 y T2 fijan con tests el comportamiento de PostgreSQL, PostGIS y GDAL que este plan supone.
  - Sus resultados entran en un único `/sdd-change` antes de T4, junto con D1, D4, D5, D6 y D7.
  - Si un resultado contradice el plan, se corrigen el plan y las tareas antes de seguir.
  - Tras T2 se decide si la spec se parte en 005a (T1 a T5) y 005b (T6 a T10).
- Dudas abiertas de la spec que se resuelven aquí:
  - método de test de RF-35 y verificación de RF-32: D10;
  - catálogo, formato y mapeo de los códigos de error: D8 y "Lógica".

## Archivos y responsabilidades
| Archivo | Crea/Modifica | Responsabilidad | RF |
|---|---|---|---|
| backend/apps/core/tests/test_database_platform.py | Crea (T1) | Fija el comportamiento de PostgreSQL y PostGIS que el plan supone | RF-5, RF-13, RF-36; prepara RF-2, RF-22, RF-34, RF-35 |
| backend/apps/core/tests/test_projection_platform.py | Crea (T2) | Fija versiones, orden de ejes, valores de proyección, cadena de transformación y fallo cerca del antípoda | RF-24, RF-27, RF-31, RF-37 |
| backend/apps/core/db.py | Crea (T3) | `run_guarded`, `constraint_name` y `codes_for_constraint` | RF-38 |
| backend/apps/core/tests/test_db.py | Crea (T3) | Tests del guardado protegido, incluidos los dos que hoy llaman a `services._codes_for_constraint` | RF-38 |
| backend/apps/users/services.py | Modifica (T3) | Usa `run_guarded`; borra `_save_guarded`, `_constraint_name` y `_codes_for_constraint` | — |
| backend/apps/categories/services.py | Modifica (T3) | Lo mismo | — |
| backend/apps/users/tests/test_services.py, backend/apps/categories/tests/test_services.py | Modifica (T3) | Quita el test de `_codes_for_constraint`, que pasa a core | — |
| backend/apps/assets/__init__.py, apps.py | Crea (T4) | Paquete y `AssetsConfig` | — |
| backend/config/settings/base.py | Modifica (T4) | Añade `"apps.assets"` a `INSTALLED_APPS`; el admin sigue sin instalarse | — |
| backend/apps/assets/location.py | Crea (T4) | `approximate_location`, `grid_cell_centre`, `ApproximationError` y las constantes de radios y rangos | RF-23 a RF-31 |
| backend/apps/assets/rules.py | Crea (T5) | Funciones puras `clean_*` y constantes de códigos | RF-3 a RF-5, RF-7, RF-8, RF-10, RF-12 a RF-14 |
| backend/apps/assets/models.py | Crea (T6) | `Asset`, `AssetStatus`, `PriceUnit`, restricciones CHECK y `__str__` | RF-1, RF-15, RF-17, RF-21, RF-22, RF-36 |
| backend/apps/assets/migrations/0001_initial.py | Crea (T6, `makemigrations` y edición de la dependencia) | Tabla `assets_asset`; depende de `categories.0001` | RF-22, RNF Migraciones |
| backend/apps/assets/services.py | Crea (T7, T8) | `create_asset`, `update_asset`, `CONSTRAINT_CODES` y `ERROR_CODES` | RF-1, RF-2, RF-6, RF-9, RF-11, RF-12, RF-15, RF-16, RF-18 a RF-20, RF-32 a RF-35, RF-38, RF-39 |
| backend/apps/assets/tests/ (test_location, test_location_reference, test_location_geodesic, test_rules, test_models, test_create, test_update, test_concurrency, test_deletion, test_leaks, test_architecture) | Crea (T4 a T9) | Tests por capa | RF-1 a RF-39 |
| specs/005-assets-and-location-privacy/validation.md | Crea (T1), completa (T2, T10) | Resultados de plataforma, pruebas de mecanismo y validación RF por RF | todos |
| docs/architecture.md | Modifica (T10) | Añade `core/db.py` y `assets` al árbol y explica el guardado protegido | — |

No se tocan `env.py`, `urls.py`, `MIDDLEWARE`, `LOGGING`, `log_redaction.py`, `docker-compose.yml`, `Dockerfile` ni las dependencias.

## Modelo de datos y migraciones

### Bien (`assets.Asset`, tabla `assets_asset`)
- `id`: `BigAutoField`.
- `owner`: `ForeignKey(settings.AUTH_USER_MODEL, on_delete=PROTECT, related_name="+")`. Sin acceso inverso: `user.assets.create()` no existe, así que no hay una segunda vía de escritura (D10).
- `category`: `ForeignKey("categories.Category", on_delete=PROTECT, related_name="+")`.
- `title` y `description`: `TextField`. Las longitudes las rechaza un CHECK con `IntegrityError`, no un `varchar` con `DataError` (D3).
- `price`: `DecimalField(max_digits=8, decimal_places=2)`.
  - Con 8 cifras y no 7, el valor 100000 llega al CHECK. Con 7 daría antes un `DataError` de desbordamiento (D3).
  - `numeric` redondea 12.345 sin dar error. Según la spec, la precisión solo se comprueba en validación.
- `currency`: `TextField`. `price_unit`: `TextField(choices=PriceUnit.choices)`. `status`: `TextField(choices=AssetStatus.choices)`.
  - Las choices no crean restricciones en la BD; la validación la hacen las reglas.
  - No llevan `default=`: los valores por defecto viven solo en el alta del servicio (RF-18).
- `exact_location`: `PointField(geography=True, srid=4326, spatial_index=False)`. Nadie busca por la exacta.
- `public_location`: `PointField(geography=True, srid=4326)`, con índice espacial para la futura búsqueda.
- `privacy_radius`: `IntegerField`. No es `PositiveIntegerField`, que añade un CHECK automático que no hace falta.
- `created_at` y `updated_at`: `DateTimeField` sin `auto_now` ni `auto_now_add`, que pisarían la hora recibida (RF-15).
- Todas las columnas son `NOT NULL`.
- `__str__` devuelve `f"{self.title} ({self.pk})"`. `repr()` y `ProtectedError` lo reutilizan (RF-17).

Restricciones (`CheckConstraint(condition=..., name=...)`; los nombres tienen menos de 63 bytes):

| Nombre | Condición |
|---|---|
| `assets_asset_title_length` | `char_length(title)` entre 3 y 100 |
| `assets_asset_description_length` | `char_length(description)` entre 20 y 2000 |
| `assets_asset_price_range` | `price` entre 0.01 y 99999.99 |
| `assets_asset_currency_eur` | `currency = 'EUR'` |
| `assets_asset_price_unit_valid` | `price_unit IN ('hour','day','week','month')` |
| `assets_asset_privacy_radius_valid` | `privacy_radius IN (500,1000,2000)` |
| `assets_asset_status_valid` | `status IN ('active','paused')` |
| `assets_asset_exact_location_valid` | `NOT ST_IsEmpty(exact_location::geometry)` y, si T1 lo permite, `ST_Y` entre -90 y 90 y `ST_X` entre -180 y 180 |
| `assets_asset_public_location_valid` | Lo mismo sobre `public_location` (RF-36) |

- Un CHECK que da NULL se cumple, y `ST_Y(POINT EMPTY)` es NULL. Por eso el `NOT ST_IsEmpty` va explícito.
- La expresión hace un cast de geography a geometry (`Cast` + `Func`). Su forma exacta se confirma con `sqlmigrate` [NV].
- Si T1 confirma que geography ajusta los valores fuera de rango, la parte de rango se quita (cambio A del `/sdd-change`).

### Migración
- `assets/0001_initial` se genera con `docker compose exec -u "$(id -u)" backend python manage.py makemigrations assets`, con OK previo, y se le pasa `ruff format` con el mismo `-u`.
- `makemigrations` pondrá la dependencia en `categories.0002_seed_categories`. Se corrige a mano a `("categories", "0001_initial")` y se conserva `swappable_dependency(settings.AUTH_USER_MODEL)`. Lo vigila un test estático sobre el grafo de migraciones (RNF Migraciones, RF-22).
- En `sqlmigrate assets 0001` se revisa:
  - el SQL de cada CHECK;
  - las FK `DEFERRABLE INITIALLY DEFERRED`;
  - el índice espacial solo en `public_location`;
  - las columnas `geography(Point,4326)`.
- Los nombres de las dos FK (`assets_asset_owner_id_<hash>_fk_users_user_id` y el de la categoría) se copian a `CONSTRAINT_CODES` y los fija un test con `diag.constraint_name`.
- Nadie ejecuta `migrate` en la BD de desarrollo sin OK en el momento (T10). `test_migrations.py` vigila la app desde T6.

## Contrato de API
No aplica: la spec no expone endpoints, así que no hay anónimo, usuario ni propietario que declarar. El contrato interno lo forman las firmas del servicio, el catálogo de códigos y `ApproximationError` (ver Lógica). Las specs de API lo traducirán a HTTP (por ejemplo, `asset_not_found` a 404).

## Lógica

### Función de aproximación (`apps/assets/location.py`; sin BD, sin red, sin hora)
- Constantes:
  - `PRIVACY_RADII = (500, 1000, 2000)`;
  - `LATITUDE_LIMITS = (-90.0, 90.0)` y `LONGITUDE_LIMITS = (-180.0, 180.0)`;
  - `GEOGRAPHIC_SRID = 4326` y `GRID_SRID = 3035`.
- `ApproximationError(ValueError)`:
  - lleva `code`, que es `radius_invalid`, `coordinate_invalid` o `projection_failed`;
  - su mensaje es el propio código, y nunca lleva valores.
- `grid_cell_centre(x, y, radius)` devuelve `((floor(x / radius) + 0.5) * radius, (floor(y / radius) + 0.5) * radius)`. `floor` hace que la celda incluya su borde inferior e izquierdo.
- `approximate_location(latitude, longitude, radius) -> tuple[float, float]` devuelve (latitud, longitud):
  1. Radio: `int` que no sea `bool` y que esté en `PRIVACY_RADII`. Si no, `radius_invalid`.
  2. Coordenada: `int` o `float`, sin `bool`; `float()` convierte, y un `OverflowError` cuenta como inválida; finita y en rango. Si no, `coordinate_invalid`.
  3. `x, y = _project(latitude, longitude)` (x = Este, y = Norte). Si alguno no es finito, `projection_failed`.
  4. Calcula el centro con `grid_cell_centre`.
  5. `_unproject` del centro. Si da un valor no finito, `projection_failed`.
  6. `return round(lat, 6), round(lon, 6)`.
- `_project` y `_unproject`:
  - en cada llamada crean `SpatialReference(srid, axis_order=AxisOrder.TRADITIONAL)` y `CoordTransform`, porque GDAL no es thread-safe y nada se guarda a nivel de módulo;
  - usan `Point(lon, lat, srid=4326).transform(ct, clone=True)`.
- `GDALException`, `SRSException` y `GEOSException` se capturan solo para marcar el fallo. `ApproximationError` se lanza fuera del `except`, así que `__context__` y `__cause__` quedan a `None`.
- Nunca se interpola `str(Point)` (EWKT) ni ninguna coordenada.
- Los tests que fuerzan un valor infinito sustituyen `_project` o `_unproject` con `monkeypatch`.

### Reglas de campos (`apps/assets/rules.py`, puras)
Cada `clean_<campo>(raw)` devuelve `(valor_limpio | None, [códigos])`. El servicio decide qué significa "no indicado".
- **Texto** (`clean_title`, `clean_description`), en este orden:
  1. Si no es `str`, `*_invalid` y se para.
  2. Si contiene un sustituto suelto (categoría Cs), `*_invalid` y se para (D4).
  3. Si el texto recibido supera 400 o 8000 puntos de código, `*_too_long` y se para (D4 (a); se omite si T2 lleva D4 a (b)).
  4. `text = unicodedata.normalize("NFC", raw.strip())`.
  5. Se acumulan:
     - `*_control_char`: Cc; en la descripción se admiten `\n`, `\r` y `\t`;
     - `*_format_char`: Cf distinto de U+200D;
     - `title_too_short`: menos de 3 caracteres visibles (visible: no `isspace()`, ni Cc, ni Cf);
     - `description_too_short`: menos de 20 puntos de código;
     - `*_too_long`: más de 100 o de 2000.
- **Precio** (`clean_price`, D5):
  1. Si es `bool` o no es `str` ni `Decimal`, `price_invalid`.
  2. `text = raw if str else str(raw)`. Si no cumple `PRICE_PATTERN.fullmatch(text)` (`\A[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\Z`), `price_invalid`. El patrón deja fuera exponente, `NaN`, `Infinity`, `sNaN`, dígitos no ASCII, `_`, espacios y coma.
  3. `value = Decimal(text)`.
  4. Si está fuera de [0.01, 99999.99], `price_out_of_range`.
  5. Se cuentan los decimales sin los ceros finales (`fracción.rstrip("0")`). Si quedan más de 2, `price_too_precise`. No se usa `normalize()`, que redondea a 28 cifras.
- **Moneda**: solo la cadena `"EUR"`; cualquier otra cosa da `currency_invalid`.
- **Unidad**: `hour`, `day`, `week` o `month`, exactos; si no, `price_unit_invalid`.
- **Radio**: `int` que no sea `bool` y que esté en `PRIVACY_RADII`; si no, `privacy_radius_invalid` (500.0 y `Decimal(500)` se rechazan).
- **Estado**: al crear solo vale `"paused"`, y al modificar `"active"` o `"paused"`. Si no, `status_invalid`.
- **Ubicación** (`clean_location(latitude, longitude)`), por coordenada:
  1. Tipo `int`, `float` o `Decimal`, sin `bool` ni `str`.
  2. `float()`; `OverflowError` o `ValueError` (sNaN) dan `location_invalid`.
  3. `math.isfinite`; si no, `location_invalid`.
  4. Rango; si no, `location_out_of_range`.
  5. Caja de coherencia con límites incluidos (27.5, 44.0, -18.5 y 5.0 son exactos en binario); si no, `location_outside_bounds`.
  - Da un solo código por campo `location`.
- **Identificadores** (`clean_reference(raw, field)`): `int` que no sea `bool`, entre 1 y 2^63−1. Si no, `owner_invalid`, `category_invalid` o `asset_not_found`.
- `contains_control_character` de `core.text` se reutiliza en el título. El recorte con NFC se repite aquí y en `Category.normalize_name`: son dos sitios, así que no se extrae.

### Servicio de escritura (`apps/assets/services.py`)
Firmas (solo con nombre; `_UNSET` es un centinela privado que significa "no indicado"):
- `create_asset(*, now, owner_id=_UNSET, category_id=_UNSET, title=_UNSET, description=_UNSET, price=_UNSET, currency=_UNSET, price_unit=_UNSET, latitude=_UNSET, longitude=_UNSET, privacy_radius=_UNSET, status=_UNSET) -> Asset`
- `update_asset(*, now, asset_id, category_id=_UNSET, title=_UNSET, description=_UNSET, price=_UNSET, currency=_UNSET, price_unit=_UNSET, latitude=_UNSET, longitude=_UNSET, privacy_radius=_UNSET, status=_UNSET) -> Asset`

Qué no aceptan:
- `update_asset` no tiene `owner_id`: pasarlo da `TypeError` y no cambia nada (RF-20).
- Ninguna acepta `public_location`, `id`, `created_at`, `updated_at` ni instancias. Cualquiera de ellos da `TypeError` (RF-33 por construcción).
- `now` debe ser un `datetime` con zona horaria. Si no, `ValueError("now_not_aware")` antes de tocar la BD.
- `TypeError` y `ValueError` son errores de programación del llamador, no de la entrada del usuario: no llevan código de dominio, y su mensaje nombra el argumento y nunca su valor.

Alta:
1. **Fase de forma**, sin BD: se limpia cada campo.
   - `_UNSET` o `None` en `owner_id`, `category_id`, `title`, `description`, `price` y `price_unit` dan `*_required`.
   - Si falta alguna coordenada, `location_required`.
   - `currency`, `privacy_radius` y `status` toman "EUR", 1000 y "paused" solo si son `_UNSET`; `None` cuenta como indicado e inválido.
   - Si hay errores, se lanza `DomainValidationError` sin consultar la BD.
2. **Fase de BD**, dentro de `run_guarded(bloque, CONSTRAINT_CODES)`:
   1. Comprueba que existen el propietario y la categoría (`owner_not_found`, `category_not_found`). Si falla, lanza `DomainValidationError` dentro del bloque (fuera de cualquier `except`), y el atomic hace rollback.
   2. `approximate_location(...)`. Si lanza `ApproximationError`, se marca y se lanza `__all__/approximation_failed` fuera del `except`.
   3. `Asset(..., created_at=now, updated_at=now).save()`.
   4. Al salir del bloque, `run_guarded` fuerza la comprobación de las FK diferidas (D3), así que una FK violada (por ejemplo, un propietario borrado a la vez) llega como `IntegrityError` dentro del `try`.
3. Si `run_guarded` devuelve códigos, se lanza `DomainValidationError` fuera de cualquier `except`.

Modificación:
1. **Fase de forma**: solo se limpian los campos indicados. `None` da `*_required` o `*_invalid`; una sola coordenada da `location_required`.
2. **Fase de BD** (`run_guarded`):
   1. `Asset.objects.select_for_update().filter(pk=asset_id).first()`. Si es `None`, `asset_not_found`.
   2. Si `category_id` cambia, se comprueba que existe.
   3. Cambios: cada valor indicado se compara con igualdad exacta con el de la **fila bloqueada**:
      - `Decimal` con `Decimal`;
      - `float` con `exact_location.y` y `.x`;
      - `int` con `int`.
   4. RF-39: si el estado guardado es `active` y cambia la exacta o el radio, `location_locked` o `privacy_radius_locked`.
   5. D7: si el estado guardado es `paused`, el nuevo es `active` y cambia la exacta o el radio, los mismos códigos.
   6. Si hay errores, se lanza dentro del bloque, con rollback.
   7. Sin cambios: se devuelve el bien sin `UPDATE` y sin tocar fechas (RF-16, RF-19).
   8. Con cambios: si cambian la exacta o el radio, se deriva la pública. Después `updated_at = now` y `save(update_fields=[cambiados..., "updated_at"])`.
- El bloqueo se toma antes de leer nada del bien. Nada se compara con lecturas sin bloqueo, que es el patrón de `_slug_changed` y aquí no se usa.

### Guardado protegido (`apps/core/db.py`)
```python
def run_guarded(write, constraint_codes):
    violated = None
    try:
        with transaction.atomic():
            result = write()
            check_deferred_constraints()
    except IntegrityError as exc:
        violated = constraint_name(exc)
    if violated is None:
        return result, {}
    return None, codes_for_constraint(violated, constraint_codes)


def check_deferred_constraints():
    with connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        cursor.execute("SET CONSTRAINTS ALL DEFERRED")
```
- `check_deferred_constraints` hace lo mismo que `connection.check_constraints()` de Django en PostgreSQL: pasa a inmediatas, lo que comprueba lo pendiente, y después pone todas las restricciones diferibles en diferidas, que para las FK de Django coincide con su modo inicial. Así las FK se comprueban dentro del `try` y quedan en su modo habitual (D3). Si el código exterior hubiera puesto alguna restricción en inmediata, queda diferida tras el bloque: no se restaura su modo.
- `constraint_name(exc)` devuelve `exc.__cause__.diag.constraint_name or ""`. `codes_for_constraint(name, codes)` devuelve `{campo: [código]}` o `{"__all__": ["constraint_violated"]}`.
- Users y categories llaman a `run_guarded(lambda: instance.save(update_fields=...), CONSTRAINT_CODES)`, así que su semántica no cambia:
  - solo se captura `IntegrityError`;
  - el `DatabaseError` de `update_fields` sigue propagándose;
  - `monkeypatch` sobre `Model.save` sigue valiendo;
  - las dos sentencias `SET CONSTRAINTS` se añaden también a sus guardados; sus restricciones son unicidades inmediatas, así que no cambia el resultado [NV, lo comprueba la suite de T3].
- Un `DomainValidationError` lanzado dentro de `write` deshace el atomic y sale tal cual, con `__context__` a `None`.
- Si T1 muestra que las restricciones no vuelven a diferidas cuando el savepoint se revierte tras un error, `run_guarded` ejecuta `SET CONSTRAINTS ALL DEFERRED` después de la reversión, dentro de la transacción exterior.

### Catálogo de códigos (formato: `DomainValidationError({campo: [códigos]})`)
| Campo | Código | Cuándo | Origen |
|---|---|---|---|
| owner | `owner_required` | Falta o `None` al crear | Servicio |
| owner | `owner_invalid` | No es `int`, es `bool` o está fuera de rango | Regla |
| owner | `owner_not_found` | No existe | Servicio; FK del propietario en la BD |
| category | `category_required`, `category_invalid`, `category_not_found` | Igual que owner; la categoría también se comprueba al modificar | Regla, servicio, FK |
| title | `title_required` | Falta o `None` | Servicio |
| title | `title_invalid` | No es `str` o tiene un sustituto suelto | Regla; `assets_asset_title_length` |
| title | `title_too_short` | Menos de 3 visibles | Regla |
| title | `title_too_long` | Más de 100 tras normalizar, o más de 400 recibidos (D4) | Regla |
| title | `title_control_char`, `title_format_char` | Cc; Cf distinto de U+200D | Regla |
| description | `description_required`, `description_invalid`, `description_too_short`, `description_too_long`, `description_control_char`, `description_format_char` | Lo mismo con 20 y 2000; se admiten `\n`, `\r` y `\t` | Regla; `assets_asset_description_length` va a `description_invalid` |
| price | `price_required` | Falta o `None` | Servicio |
| price | `price_invalid` | Tipo, formato, exponente o no finito | Regla |
| price | `price_out_of_range` | Menor que 0.01 o mayor que 99999.99 | Regla; `assets_asset_price_range` |
| price | `price_too_precise` | Más de 2 decimales significativos | Regla |
| currency | `currency_invalid` | Distinta de `"EUR"` | Regla; `assets_asset_currency_eur` |
| price_unit | `price_unit_required`, `price_unit_invalid` | Falta; fuera de la lista | Regla; `assets_asset_price_unit_valid` |
| privacy_radius | `privacy_radius_invalid` | Fuera de {500, 1000, 2000}, o no es `int` | Regla; `assets_asset_privacy_radius_valid` |
| privacy_radius | `privacy_radius_locked` | RF-39 y D7 | Servicio |
| status | `status_invalid` | RF-12 | Regla; `assets_asset_status_valid` |
| location | `location_required` | Falta alguna coordenada al crear, o solo llega una | Servicio |
| location | `location_invalid` | Tipo, `bool` o no finita | Regla; `assets_asset_exact_location_valid` |
| location | `location_out_of_range` | Latitud o longitud fuera de rango | Regla |
| location | `location_outside_bounds` | Fuera de la caja de coherencia | Regla |
| location | `location_locked` | RF-39 y D7 | Servicio |
| asset | `asset_not_found` | Identificador inválido o inexistente al modificar | Servicio |
| `__all__` | `approximation_failed` | La función falla con una coordenada ya validada | Servicio |
| `__all__` | `constraint_violated` | Restricción no reconocida o sin nombre (NOT NULL, `assets_asset_public_location_valid`) | `run_guarded` |

- **Fases**:
  - Los errores de forma de todos los campos se devuelven juntos, y cada campo puede llevar varios códigos.
  - La existencia, el bien no encontrado y RF-39 se evalúan solo si la forma es válida, y se devuelven juntos.
- `services.ERROR_CODES` contiene todos los códigos de la tabla, y un test lo compara con ella.
- No son errores de dominio, porque la regla de la spec "cada rechazo lleva un código" se refiere a la validación de datos:
  - `ApproximationError` (RF-31), que se lanza solo fuera del servicio y lleva su propio `code`;
  - el `TypeError` de un argumento no admitido y el `ValueError("now_not_aware")`, que son errores de programación;
  - un `DataError` de un precio de 10^6 o más escrito por fuera de la validación (sin valores [NV]).

## Interfaz
No aplica: la spec no tiene pantallas ni verificación en navegador (lo dicen sus criterios de finalización).

## Decisiones
Todas aprobadas por el usuario; D3 y D10 con los cambios que pidió.

| Decisión | Opciones | Elegida | Qué evita | Coste |
|---|---|---|---|---|
| D1. Forma del servicio (RF-32, RF-20, RF-33) | (a) `create_asset` y `update_asset`, solo con nombre y lista blanca de campos; `owner_id` solo al crear y `asset_id` solo al modificar; ni instancias ni pública. (b) Una sola `save_asset(asset_id=None, ...)`. (c) Una función que recibe una instancia (como `save_category`) | (a) | (b): ramas por modo dentro de una función (valores por defecto, propietario y estados distintos). (c): confiar en una instancia que el llamador puede haber manipulado (pública, propietario, fechas) | `/sdd-change` de la Definición de "servicio de escritura" y de RF-32: "las dos funciones de escritura de un único módulo". RF-20 y la pública recibida se cumplen por construcción, con `TypeError` y sin código |
| D2. Extracción del guardado protegido | (a) `run_guarded(write, constraint_codes)` en `core/db.py`: bloque entero en atomic, devuelve (resultado, códigos). (b) Extraer solo `constraint_name` y `codes_for_constraint`; cada servicio conserva su try/atomic. (c) Sin extracción; variante propia en bienes | (a) | Una cuarta copia; que bienes capture solo el `save()` y deje el bloqueo y la validación fuera; cambiar la semántica de users y categories | Commit aparte (T3) con la suite antes y después; dos tests de privados pasan a core |
| D3. Rechazo en la BD y FK diferidas (RF-2, RF-38) | (a) `TextField` + CHECK; `numeric(8,2)` + CHECK; solo `IntegrityError`; `run_guarded` fuerza la comprobación de las restricciones diferidas al terminar el bloque (`SET CONSTRAINTS ALL IMMEDIATE` y después `ALL DEFERRED`, como `connection.check_constraints()` de Django en PostgreSQL) y el servicio comprueba de forma explícita que existen propietario y categoría. (b) `varchar(100)` y `numeric(7,2)`, capturando también `DataError` como `constraint_violated`, con `/sdd-change` ("error de datos"). (c) `atomic(durable=True)`. (d) `SET CONSTRAINTS ALL IMMEDIATE` al abrir el bloque y sin volver a diferidas | (a), con el cambio pedido por el usuario | `DataError` antes del CHECK; una violación de FK que salta en el COMMIT de una transacción exterior, fuera del try; (c) rompería un futuro `ATOMIC_REQUESTS`; (d) dejaría el resto de la transacción exterior en modo inmediato | Dos sentencias más por guardado, también en users y categories. Una violación pendiente que el código exterior dejó antes del bloque salta en la comprobación y se traduce a `constraint_violated`. Un precio de 10^6 o más escrito por fuera da `DataError` |
| D4. Texto: tope bruto y sustitutos (RF-3, RF-4) | (a) Rechazar antes de normalizar lo que supere 4 veces el máximo (400 y 8000) con `*_too_long`, y los sustitutos sueltos con `*_invalid`. (b) Sin tope (lo pondrá el límite del cuerpo en la spec de API) y sustitutos `*_invalid`. (c) Sin tope ni regla de sustitutos | (a) si T2 mide un coste superlineal de NFC o de `Decimal()`; si no, (b). Los sustitutos se rechazan en los dos casos | NFC de coste cuadrático sobre megas de marcas combinantes [NV]; el `UnicodeEncodeError` crudo de psycopg | `/sdd-change` de casos límite. Con (a), un título válido con más de 300 espacios de relleno se rechaza |
| D5. Entrada numérica (RF-5, RF-10, RF-13) | (a) Precio `str` o `Decimal` validado por `str()` con patrón ASCII, y decimales contados sin ceros finales (12.340 vale 12.34). Coordenadas `int`, `float` o `Decimal` sin `bool` ni `str`, convertidas a `float` antes de comparar. Radio `int` sin `bool`. (b) Decimales escritos, como `DecimalValidator` (12.340 se rechaza); coordenadas solo `float` | (a) | Rechazar representaciones equivalentes (coherente con el riesgo aceptado de `+5` y `007.50`); dígitos Unicode, `1_0`, `sNaN`; que `500.0 in {500}` cuele; el `OverflowError` de `10**400`; que `Decimal("40.4") == 40.4` sea falso | `/sdd-change` de casos límite: "12.340 se acepta como 12.34" y "coordenada como texto se rechaza" |
| D6. RF-33 frente a RF-34 | (a) Derivar al crear y cuando cambian la exacta o el radio. (b) Recalcular en cada escritura y corregir la pública que no coincida. (c) Recalcular siempre y rechazar si no coincide | (a) | (b): que tras actualizar PROJ editar el título de un bien activo mueva su pública, contra HU-4. (c): impedir incluso pausar | Una pública escrita por fuera del servicio queda hasta el siguiente cambio de exacta o radio (riesgo de escrituras por fuera). `/sdd-change` del caso límite "pública manipulada" |
| D7. Activar y mover en la misma llamada (RF-39) | (a) Rechazar pasar de `paused` a `active` y a la vez cambiar la exacta o el radio. (b) Aceptarlo, que es la lectura literal de RF-39 | (a) | Publicar una zona nueva sin la revisión que pide HU-4 | `/sdd-change` de RF-39; el cliente hace dos llamadas |
| D8. Catálogo y formato de errores (RF-31, RNF Errores) | (a) `DomainValidationError` con todos los errores de forma a la vez y una segunda fase de BD; RF-31 con `ApproximationError(ValueError)` y `code`; errores de programación como `TypeError` o `ValueError`, sin código. (b) Solo el primer error. (c) `DomainValidationError` también en la función | (a) | (b) obliga al cliente a reenviar varias veces; (c) acopla la función pura al formato de validación de modelos | Unos 35 códigos fijados por test; un fallo de forma no consulta la BD |
| D9. Función de aproximación (RF-23 a RF-31) | (a) Módulo puro `apps/assets/location.py`: `CoordTransform` por llamada, orden TRADITIONAL explícito, y los tests sustituyen `_project`/`_unproject` para forzar infinito. (b) `apps/core/geo.py` con `CoordTransform` a nivel de módulo. (c) `ST_Transform` de PostGIS | (a) | (b): GDAL no es thread-safe, y `core` es para lo compartido; (c): consulta la BD (RNF Rendimiento) y usaría el PROJ de la imagen de PostGIS | Crear las SRS en cada llamada cuesta del orden del milisegundo [NV]; los tests sustituyen dos privadas |
| D10. Verificación de RF-35 y RF-32 | RF-35: (a) `CaptureQueriesContext` (el primer SQL sobre `assets_asset` es `SELECT … FOR UPDATE`, antes del UPDATE) más un test con `django_db(transaction=True, serialized_rollback=True)` en el que, con el bloqueo tomado (gancho en la derivación), una segunda conexión hace `SELECT … FOR UPDATE NOWAIT` y espera `LockNotAvailable` (55P03); (b) solo `CaptureQueriesContext`; (c) hilos con espera. RF-32: (a) test estático por AST, `related_name="+"` y exactamente dos funciones públicas en `services.py`; (b) un QuerySet que bloquee `update` y `bulk_*` | (a) para los dos. El test de la segunda conexión exige `transaction=True`: una segunda conexión no ve las filas sin confirmar, y en un `django_db` normal el `FOR UPDATE NOWAIT` no encontraría la fila y el test pasaría sin probar nada. Exige también `serialized_rollback=True`, para que el vaciado de la BD no se lleve la semilla. | Tests con `sleep` y no deterministas; un test que pasa en vacío; una segunda vía de escritura por el gestor inverso o por un import de `Asset` | Depende de T1 (segunda conexión). El test transaccional es más lento y deja la BD de test a restaurar. El AST no ve `RunSQL`, `loaddata` ni SQL de superusuario (riesgo aceptado) |

Aceptado como riesgo:
- Escrituras que el test estático no ve: `RunSQL`, migraciones de datos, `loaddata`, shell y SQL de superusuario (riesgo aceptado de la spec). El admin no está instalado (`base.py:9-17`) y así sigue.
- `PROTECT` sobre usuarios bloqueará el futuro borrado RGPD; la spec que lo defina decide.
- `str(ProtectedError)` incluye la representación de los bienes protegidos: título e id, sin coordenadas (RF-17).
- Un bien que se borra mientras otra modificación espera el bloqueo da `asset_not_found`.
- El log del servidor PostgreSQL (STATEMENT con literales y DETAIL con la fila en EWKB) queda para la spec de despliegue.
- El manejador de errores de GDAL de Django escribe en `django.contrib.gis` a nivel ERROR. Se acepta si T2 confirma que su texto no lleva coordenadas.

Cambios de spec que propone este plan, en un único `/sdd-change` antes de T4:
1. D1: la Definición de "servicio de escritura" y RF-32 pasan a "dos funciones de un único módulo".
2. D4:
   - sustitutos sueltos: un caso límite, y RF-3 y RF-4 pasan a decir "no es texto";
   - tope bruto, si T2 lo justifica.
3. D5: casos límite de `12.340` y de la coordenada como texto.
4. D6: se reescribe el caso límite "pública manipulada", porque el servicio no acepta una pública y la guardada solo cambia con la exacta o el radio.
5. D7: RF-39 añade "activar y cambiar exacta o radio en la misma modificación se rechaza".
6. Según T1 y T2, los cambios A, A', B y C descritos en sus tareas.

## Blast radius
- `users/services.py:124-144` y `categories/services.py:99-119` se sustituyen por `core.db` (T3).
  - `users/tests/test_services.py:168-171` y `categories/tests/test_services.py:353-356` llaman a `services._codes_for_constraint`; pasan a `core/tests/test_db.py`.
  - `users/tests/test_services.py:174-185` y `categories/tests/test_services.py:359-369` parchean `Model.save`; siguen valiendo porque la lambda llama a `save`.
  - `users/tests/test_services.py:397-411` y `categories/tests/test_services.py:340-350` exigen que el `DatabaseError` de `update_fields` se siga propagando.
  - Los guardados de users y categories ejecutan ahora dos sentencias `SET CONSTRAINTS` más; cualquier test que cuente consultas allí tendría que ajustarse [NV, lo revela la suite de T3].
- `base.py:9-17`: `INSTALLED_APPS` gana `apps.assets`. Tras añadirla, `docker compose restart backend`. `auth` crea permisos y tipos de contenido de `Asset` en `post_migrate`.
- `config/tests/test_logging.py:29` exige que `LOGGING["loggers"]` sea exactamente `[DB_LOGGER]`. No se configura `django.contrib.gis` salvo que T2 lo obligue, y entonces se cambia ese test en la misma tarea.
- `config/tests/test_migrations.py` vigila `assets` desde T6. `config/tests/test_tooling.py` exige que la migración generada pase `ruff format`.
- `categories/tests/test_seed.py:41-42`: `historical_apps()` calcula el estado en `categories.0002`, que no tiene `Asset`. Ningún test nuevo lo usa para comprobar `PROTECT`, porque daría un falso verde.
- `conftest.py:32-44`: el bloqueo de red afecta a la segunda conexión de RF-35 si psycopg resuelve el nombre en Python [NV, T1].
- Borrar usuarios o categorías queda protegido. Los tests existentes que borran lo hacen sin bienes (`users/tests/test_services.py:400`, `categories/tests/test_services.py:343`, `test_seed.py:93-99`) y no cambian.
- `related_name="+"`: `user.assets` y `category.asset_set` no existen; las specs posteriores filtran por `Asset.objects`.
- La BD de desarrollo tiene migraciones sin aplicar desde T6 hasta T10 (`runserver` avisa y no falla).
- `docs/architecture.md` (T10) y `spec.md` (`/sdd-change`).

## Riesgos
| Riesgo | Mitigación |
|---|---|
| geography ajusta los valores fuera de rango y el CHECK nunca ve 91 o 181 | T1 lo fija antes del modelo; si ajusta, `/sdd-change` A y el rango solo se garantiza en validación |
| PROJ elige una transformación WGS84→ETRS89 distinta de la identidad, o cambia con las rejillas | T2 compara con la fórmula LAEA de la guía EPSG 7-2 escrita en el test; si difiere, `/sdd-change` C (tomar la entrada como ETRS89, EPSG:4258) |
| Una actualización de GDAL o PROJ cambia los centros publicados | Test de valores de referencia (T4); con D6, nada recalcula sin cambio de exacta o radio; riesgo aceptado de la spec |
| Una FK diferida se viola en el COMMIT de una transacción exterior | `run_guarded` fuerza la comprobación al terminar el bloque y después pone las restricciones en diferidas (D3); test con la comprobación anulada |
| Fugas de coordenadas por EWKT, EWKB, DETAIL, log de GDAL o NOTICE de psycopg | El servicio construye `Point` desde `float` validados; mensajes fijos; test de fugas con todas las formas (T9) |
| Un test con `transaction=True` vacía la semilla | `serialized_rollback=True` en todos; T8 comprueba que hay once categorías al empezar [NV, orden de pytest-django] |
| El test de la segunda conexión pasa en vacío porque la fila no está confirmada | `transaction=True` y una aserción previa de que la segunda conexión ve la fila (D10) |
| Revertir la semilla en un test deja la BD de test sin 0002 si el test falla | Revertir dentro de `atomic` con `set_rollback(True)` (T1 lo valida); si no, `finally` con `migrate` hacia delante |
| GDAL no es thread-safe | SRS y `CoordTransform` creados en cada llamada (D9) |
| T4 y T6 son las tareas más largas | Si superan los 30 min, se anota; tras T2 se decide si se parte la spec en 005a (T1 a T5) y 005b (T6 a T10) |

## Estrategia de tests
| RF | Cómo se verifica (pytest) |
|---|---|
| RF-1 | `test_create.py`: un alta válida guarda propietario, categoría, título y descripción normalizados, precio `Decimal`, moneda, unidad, exacta, pública, radio, estado y fechas. `test_models.py`: existen los campos y no hay ningún campo más. |
| RF-2 | `test_rules.py`: `clean_reference` con `None`, `True`, `"5"`, `0` y 2^63. `test_create.py`: propietario o categoría ausentes, `None`, no `int` o inexistentes dan `*_required`, `*_invalid` o `*_not_found`, y no se crea ninguna fila. BD (`test_models.py`): INSERT por SQL con una FK inexistente, tras `SET CONSTRAINTS ALL IMMEDIATE`, da `IntegrityError` con el nombre de la FK. Servicio con la comprobación de existencia anulada por `monkeypatch`: `owner_not_found` por traducción de la FK, gracias a la comprobación forzada de `run_guarded`. Prueba de mecanismo: sin la comprobación forzada, el test falla con `DID NOT RAISE`. |
| RF-3 | `test_rules.py`, con los casos límite de la spec y escapes con `chr()`: solo espacios, 2, 3, 100 y 101 caracteres, solo U+200D, "a" con dos U+200D, la familia de tres emojis, NFD, U+202E, Cc, no `str`, sustituto suelto y tope bruto (D4). BD: 2 y 101 puntos de código por `save()` directo dan `IntegrityError` `assets_asset_title_length`. |
| RF-4 | `test_rules.py`: 19, 20, 2000 y 2001 caracteres; ESC; `\r\n` aceptado; U+202E; U+200D dentro de un emoji aceptado; no `str`; tope bruto. BD: 19 y 2001 dan `IntegrityError` `assets_asset_description_length`. |
| RF-5 | `test_rules.py`: `0.1` (`float`), `True`, `5` (`int`), `1e2`, `1E2`, `Decimal("1E+2")`, `NaN`, `Infinity`, `sNaN`, `12,50`, dígitos `chr(0x0661)`, `1_0`, `" 5"`, `0`, `0.00`, `-5`, `100000`, `12.345`, `0.01`, `99999.99`, `12.340` (D5), `+5` y `007.50`. Se comprueba que el valor guardado es el recibido, sin redondeo. BD: `0` y `100000` dan `IntegrityError` `assets_asset_price_range`. `test_database_platform.py` (T1): con `numeric(7,2)`, 100000 daría `DataError`. |
| RF-6 | `test_create.py`: sin moneda se guarda `EUR`. |
| RF-7 | `test_rules.py`: `usd`, `eur`, `USD`, `None` y `1` dan `currency_invalid`. BD: `USD` da `IntegrityError` `assets_asset_currency_eur`. |
| RF-8 | `test_rules.py`: se aceptan las cuatro unidades; `night`, `Day` y `""` se rechazan. `test_create.py`: sin unidad, `price_unit_required`. BD: `night` da `IntegrityError`. |
| RF-9 | `test_create.py`: sin radio se guarda 1000. |
| RF-10 | `test_rules.py`: `0`, `-500`, `1500`, `500.5`, `500.0`, `True`, `"500"` y `Decimal(500)` se rechazan. BD: 1500 da `IntegrityError`. |
| RF-11 | `test_create.py`: sin estado o con `paused`, el bien nace `paused`. |
| RF-12 | `test_create.py`: `active` al crear da `status_invalid`. `test_update.py`: `deleted`, `Active` y `None` se rechazan. BD: `deleted` da `IntegrityError`. |
| RF-13 | `test_rules.py`: ±91, ±181, `True`, `False`, NaN, ±inf, `"40.4"`, `None`, `10**400`, `Decimal("sNaN")` y una sola coordenada. BD: según T1, un CHECK de rango con `IntegrityError` o el ajuste fijado en `test_database_platform.py`, y una exacta vacía da `IntegrityError` `assets_asset_exact_location_valid`. |
| RF-14 | `test_rules.py`: coordenadas intercambiadas (-3.7, 40.4) se rechazan. Lisboa, Andorra y Toulouse se aceptan, igual que los cuatro límites exactos. `math.nextafter` hacia fuera de cada límite se rechaza. |
| RF-15 | `test_create.py`: `created_at == updated_at == now`, con zona horaria y desplazamiento UTC 0. Un `now` sin zona horaria da `ValueError` y no escribe nada. `test_models.py`: `auto_now` y `auto_now_add` son `False`. |
| RF-16 | `test_update.py`: un cambio pone `updated_at = now2` y conserva `created_at`. Sin cambios, o con valores iguales (precio `"12.3"` frente a 12.30, mismas coordenadas), no hay UPDATE en `CaptureQueriesContext` ni cambian las fechas. |
| RF-17 | `test_models.py`: `str()` y `repr()` contienen el título y el id y ninguna forma de las coordenadas centinela (repr, 6 decimales, EWKT, EWKB). |
| RF-18 | `test_update.py`: los campos no indicados se conservan (radio 2000, estado `active`, moneda). Las validaciones se aplican al valor indicado. Los valores por defecto no se aplican al modificar. |
| RF-19 | `test_update.py`: activar y pausar funcionan; activar un bien activo y pausar uno pausado no dan error, no hacen UPDATE ni tocan fechas. |
| RF-20 | `test_update.py`: `update_asset(owner_id=...)` da `TypeError` y el propietario no cambia. Cambiar la categoría se acepta. |
| RF-21 | `test_deletion.py`: `user.delete()` da `ProtectedError` y el usuario sigue existiendo. `DELETE` por SQL tras `SET CONSTRAINTS ALL IMMEDIATE`, dentro de `atomic`, da `IntegrityError` (ForeignKeyViolation) con el nombre de la FK. |
| RF-22 | `test_deletion.py`: lo mismo con la categoría. `call_command("migrate", "categories", "0001_initial")` con un bien de `pool` da `ProtectedError`, quedan las once categorías y `0002` sigue registrada. `test_architecture.py`: `MigrationLoader(...).graph.forwards_plan(("assets", "0001_initial"))` no incluye `("categories", "0002_seed_categories")`. |
| RF-23 | `test_location.py`: sobre el conjunto de muestra (las cuatro esquinas de la caja, Canarias, Baleares, Lisboa, Andorra, Toulouse, bordes y esquinas de celda, y 200 puntos de `random.Random(5)`) y para los tres radios, el resultado proyectado está a menos de 1 m del centro de la celda que contiene el original. `grid_cell_centre` con `x` exactamente en un borde lo asigna a la celda superior. Un punto válido fuera de la caja devuelve un valor. |
| RF-24 | `test_location.py`: dos llamadas dan el mismo resultado, sin marca `django_db` (un acceso a la BD fallaría) y con la red bloqueada. `test_location_reference.py`: centros literales para Madrid, Las Palmas y Palma con los tres radios. |
| RF-25 | `test_location.py`: la distancia en la proyección no supera 0,71 × radio en toda la muestra. |
| RF-26 | `test_location_geodesic.py` (`django_db`): `ST_Distance` sobre geography, en una sola consulta con `unnest`, no supera el radio en toda la muestra. |
| RF-27 | `test_location_geodesic.py`: el lado inferior y el izquierdo de la celda de cada punto, desproyectados y medidos con `ST_Distance`, están entre el 95 % y el 105 % del radio, para los tres radios, con Canarias, Baleares y las esquinas. |
| RF-28 | `test_location.py`: dos puntos de la misma celda (cerca de la esquina inferior izquierda y de la superior derecha) dan el mismo resultado. |
| RF-29 | `test_location.py`: f(f(p)) == f(p) en toda la muestra. |
| RF-30 | `test_location.py`: el resultado con 500 está en la misma celda de 1000 y de 2000 que el original, y el de 1000 en la misma de 2000. |
| RF-31 | `test_location.py`: radios `0`, `1500`, `True`, `"1000"` y `500.0` dan `radius_invalid`. Coordenadas 91, NaN, inf, `True` y `"40"` dan `coordinate_invalid`. El antípoda (según T2) y `_project` o `_unproject` sustituidos para devolver `math.inf` dan `projection_failed`. No se devuelve ningún valor, y `__context__` y `__cause__` son `None`. |
| RF-32 | `test_architecture.py` (AST sobre `backend/apps` y `backend/config`, sin `migrations/` ni `tests/`): solo `assets/models.py`, `services.py` y `selectors.py` importan `Asset`; nadie llama a `get_model("assets", …)`; `models.py` y `selectors.py` no llaman a `save`, `create`, `update`, `delete`, `bulk_create`, `bulk_update`, `get_or_create` ni `update_or_create`; las funciones públicas de `services.py` son exactamente `{create_asset, update_asset}`; `owner` y `category` tienen `related_name == "+"`. Prueba de mecanismo: un módulo temporal que importa `Asset` hace fallar el test. |
| RF-33 | `test_create.py`: la pública es igual a `approximate_location(exacta, radio)`, y pasar `public_location=` da `TypeError`. `test_update.py`: mover la exacta de un bien pausado a otra celda o cambiar su radio actualiza la pública en el mismo guardado. Criterio de la spec: tras una secuencia de altas y modificaciones, cada pública guardada coincide con la derivada de su exacta y su radio. |
| RF-34 | `test_update.py`: mover la exacta dentro de la misma celda no cambia la pública. Cambiar solo el título no llama a `approximate_location` (espía con `monkeypatch`) ni cambia la pública (D6). |
| RF-35 | `test_concurrency.py`, dos tests. (1) Con `CaptureQueriesContext` (vale un `django_db` normal), el primer SQL sobre `assets_asset` es `SELECT … FOR UPDATE`, y el UPDATE va después dentro del mismo atomic. (2) Con `django_db(transaction=True, serialized_rollback=True)`, el gancho en `approximate_location` abre una segunda conexión y, con el bloqueo tomado: primero comprueba que esa conexión **ve** la fila (`SELECT count(*)` da 1), después ejecuta `SELECT … FOR UPDATE NOWAIT`, espera `OperationalError` con sqlstate 55P03 y cierra la conexión. Pruebas de mecanismo: sin `select_for_update`, el test (2) falla en el `NOWAIT`; con el test (2) marcado como `django_db` normal, falla la aserción de visibilidad, en lugar de pasar en vacío. Al terminar, un test posterior comprueba que siguen las once categorías. |
| RF-36 | `test_models.py`: `exact_location` y `public_location` son campos distintos. Una pública vacía da `IntegrityError` `assets_asset_public_location_valid`, y una nula da `IntegrityError` de NOT NULL. |
| RF-37 | `test_leaks.py`, con coordenadas centinela, `caplog` a DEBUG (captura también `django.contrib.gis` y `psycopg`) y `connection.force_debug_cursor`. Casos: rechazo de validación, `location_locked`, fallo de la función por radio, por coordenada y por proyección, CHECK de la BD (regla parcheada para que pase `price=0`), y `ProtectedError` de usuario, de categoría y de la reversión de la semilla. Se busca la exacta y la pública derivada como `repr(float)`, con 6 decimales, en EWKT, en EWKB hexadecimal en mayúsculas y en minúsculas, y como hexadecimal little y big endian de cada `double`. Se busca en `str()`, `repr()`, `traceback.format_exception()`, `message_dict` y `caplog.text`. |
| RF-38 | `core/tests/test_db.py`: traducción por nombre; desconocida o sin nombre da `constraint_violated`; el `DatabaseError` se propaga; el `DomainValidationError` lanzado dentro hace rollback; una FK violada dentro del bloque salta dentro del `try`; tras el bloque, una FK violada posterior en la misma transacción exterior no salta hasta pedirlo (restricciones en diferidas). `test_leaks.py` y `test_create.py`: un CHECK en el servicio da su código, `__context__` y `__cause__` son `None` y la conexión sigue usable. Pruebas de mecanismo: con `from exc` dentro del `except`, el test falla; sin el `SET CONSTRAINTS ALL DEFERRED`, falla el test de restricciones diferidas. |
| RF-39 | `test_update.py`: bien `active` con la exacta cambiada da `location_locked`, y con el radio cambiado `privacy_radius_locked`. `active` con los mismos valores se acepta. `paused` con cambio se acepta. Pausar y mover en la misma llamada se rechaza. `paused` a `active` con movimiento se rechaza (D7). |
| RNF Errores | `services.ERROR_CODES` coincide con la tabla del catálogo. |
| RNF Rendimiento | Los tests de la función no llevan `django_db` y tienen la red bloqueada. |
| RNF Dependencias | T10: `requirements*.txt` sin diff respecto a `dev`. |
| RNF Migraciones | Test estático del grafo (RF-22). |

Cada test que protege un mecanismo lleva su prueba de mecanismo, que se registra en `validation.md`.

## Afirmaciones no verificadas
- [V, Django 5.2.17 del `.venv` del host; el contenedor usa 5.2.18]:
  - `SpatialReference` usa `AxisOrder.TRADITIONAL` por defecto (`gis/gdal/srs.py:65`).
  - El manejador de GDAL escribe `"GDAL_ERROR %d: %s"` en `django.contrib.gis` a nivel ERROR (`gis/gdal/libgdal.py:128`), y GEOS escribe `GEOS_NOTICE` y `GEOS_ERROR` en el mismo logger (`gis/geos/libgeos.py:86,100`).
  - `full_clean` admite `validate_constraints` (`db/models/base.py:1634`). Si la consulta de un CHECK falla, Django escribe un WARNING con el error (`db/models/query_utils.py:192-193`); por eso los bienes no usan `full_clean`.
  - `GeometryField.get_prep_value` interpola el valor en un `ValueError` (`gis/db/models/fields.py:229-230`).
  - `DecimalValidator` cuenta los decimales escritos (`core/validators.py:538` y siguientes).
- [NV] Lo que comprueba T1:
  - geography ajusta, rechaza o guarda 91, 181 y NaN;
  - geography admite POINT EMPTY, y `ST_Y` da NULL;
  - el `DataError` de `numeric(7,2)` no lleva el valor;
  - las FK de Django son `DEFERRABLE INITIALLY DEFERRED`;
  - la ida y vuelta EWKB es exacta;
  - la segunda conexión abre y usa la BD de test, y solo ve las filas confirmadas;
  - `migrate` hacia atrás funciona dentro de la transacción del test y `set_rollback` lo deshace;
  - `SET CONSTRAINTS ALL IMMEDIATE` dentro de un savepoint que se revierte tras un error deja las restricciones en diferidas.
- [NV] Lo que comprueba T2:
  - PROJ usa la identidad WGS84→ETRS89 y `PROJ_NETWORK` está apagado;
  - qué hace GDAL cerca del antípoda (−52, −170) y qué texto registra;
  - el coste de NFC y de `Decimal()` sobre entradas de megas.
- [NV] `SET CONSTRAINTS ALL IMMEDIATE` comprueba en ese momento lo pendiente de toda la transacción, y `ALL DEFERRED` pone todas las restricciones diferibles en diferidas, que para las FK de Django coincide con su modo inicial.
- [NV] El recolector aplica `PROTECT` con `related_name="+"` (relaciones ocultas incluidas). Lo cubren los tests de RF-21 y RF-22.
- [NV] Al revertir `categories.0002` con `migrate`, el estado histórico incluye `Asset`, así que `PROTECT` actúa. Lo cubre el test de RF-22.
- [NV] La forma de la expresión del CHECK (`Cast`, `Func` y lookups como expresiones dentro de `condition`); se confirma con `sqlmigrate`.
- [NV] pytest-django serializa la BD de test cuando algún test pide `serialized_rollback` y ejecuta los transaccionales al final.
- [NV] `LockNotAvailable` llega como `django.db.utils.OperationalError` con `__cause__.sqlstate == "55P03"`.
- [NV] psycopg 3.3 entrega los NOTICE de PostgreSQL al logger `psycopg`.
- [NV] `char_length` cuenta puntos de código en una BD UTF-8.
- [NV] Crear `SpatialReference(3035)` en cada llamada cuesta del orden del milisegundo.

## Skills que aplican
- sdd.
- django-drf: capas; migraciones (se pregunta antes de crearlas o aplicarlas, y se revisa `sqlmigrate` con campos espaciales); `restart` al añadir la app; guardado protegido; tests de BD, de migraciones y de fugas; pruebas de mecanismo.
