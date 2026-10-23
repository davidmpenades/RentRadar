---
name: django-drf
description: Úsala siempre que toques el backend de RentRadar (backend/, Django, DRF, PostGIS), es decir, al crear o cambiar modelos, migraciones, serializers, vistas, permisos, servicios, selectores, tests de pytest, geocodificación, búsquedas por radio, límites de tasa o dependencias de Python, y también al planificar tareas de backend en una spec, aunque el usuario no mencione Django ni DRF de forma explícita.
---

# Backend de RentRadar (Django + DRF + PostGIS)

Complementa a docs/constitution.md; si algo choca con ella, manda la constitución.

## Capas
La ubicación de cada fichero está en docs/architecture.md. Aquí solo van las responsabilidades:
- Servicios: escrituras y reglas de negocio (crear, cambiar estado, validar invariantes). Funciones con argumentos explícitos; lo externo (hora, geocodificador, almacenamiento) entra como parámetro para poder testearlo sin mocks globales.
- Selectores: lecturas. Devuelven querysets ya filtrados por lo que el usuario puede ver.
- Serializers: solo traducen y validan la forma (tipo, rango, tamaño). Sin reglas de negocio.
- Vistas: autenticación, permisos y llamada al servicio o selector. Sin consultas sueltas ni lógica.

Por qué: la regla de negocio se testea como función pura y la vista se queda en un test de contrato HTTP.

## Autorización por objeto: 404 frente a 403
- `get_queryset()` usa un selector que solo devuelve lo que el usuario puede **ver**. Lo que no está en él da 404 y no revela que existe.
- `has_object_permission()` decide si puede **modificar**. Si lo ve pero no es suyo, 403.
- Cada endpoint declara qué pueden hacer anónimo, usuario y propietario, y cada recurso ajeno tiene un test que intenta acceder y espera 404 o 403 según el caso.

## Anónimo: 403 o 401
Con `SessionAuthentication` como primera clase de autenticación, DRF responde 403 al anónimo, no 401, porque la sesión no envía cabecera `WWW-Authenticate`. Con autenticación por token primero, responde 401. Como la autenticación tiene que servir para web y móvil, el test fija el código que espera según la clase configurada; nunca se acepta «403 o 401».

## Consultas N+1
Los listados usan `select_related` o `prefetch_related` en el selector. Cada endpoint de listado tiene un test con `django_assert_max_num_queries` y varios objetos, para que una relación nueva sin precargar haga fallar el test.

## Ubicaciones con PostGIS geography
- Los campos de ubicación son `PointField(geography=True, srid=4326)`. Así las distancias se calculan en metros sobre la esfera sin tener que elegir proyección.
- `Point(x, y)` es `Point(lon, lat)`. Invertirlos manda el punto a otro continente sin dar error; los tests de radio comprueban un punto dentro y otro fuera.
- Búsqueda por radio: `filter(location__dwithin=(punto, D(m=radio)))`, que usa el índice espacial, y `annotate(distance=Distance(...))` solo si hace falta ordenar o mostrar la distancia.
- El radio y las coordenadas que llegan del usuario se validan en rango (lat ±90, lon ±180, radio con máximo) antes de construir la consulta.

## Precios
Importe y moneda por separado: `DecimalField` para el importe (nunca `float`) y código ISO 4217 para la moneda. Hoy solo se acepta EUR, pero el modelo no lo da por supuesto.

## Geocodificación: interfaz y adaptadores
- Los servicios dependen de una interfaz (`Protocol`) de geocodificación, no de un proveedor. Cada proveedor es un adaptador y cuál se usa se decide por configuración (variables de entorno).
- Los tests inyectan un adaptador falso; ningún test sale a la red.
- Cada adaptador fija un timeout, valida la forma de la respuesta del proveedor (constitución, punto 6) y la traduce a un tipo propio del dominio.
- El navegador nunca llama al proveedor; siempre pasa por el backend, que controla las cabeceras, la caché y los límites.
- El Nominatim público no sirve para producción: su política de uso limita la tasa y exige un User-Agent identificable. Solo se usa en desarrollo o detrás de una instancia propia.
- Si el adaptador usa Nominatim, las calles necesitan búsqueda estructurada (`street` + `city`); el texto libre falla con direcciones.

## Límites de tasa y caché
El throttling de DRF guarda los contadores en la caché por defecto. Con `LocMemCache` cada worker lleva su propia cuenta y el límite real se multiplica por el número de workers. Antes de desplegar hace falta una caché compartida; si eso añade una dependencia, necesita aprobación explícita (constitución, punto 1).

## Dependencias de Python
- Los locks llevan hashes. Regéneralos sin `--no-index`, que impide consultar PyPI, y revisa el diff del lock antes del commit.
- Una dependencia nueva solo entra con aprobación explícita.

## Migraciones
Pregunta antes de crear o aplicar una migración. Revisa el SQL (`sqlmigrate`) cuando toque campos espaciales o índices.
- Las migraciones generadas incumplen E501 e I001; `pyproject.toml` los ignora solo en `**/migrations/`. El resto de reglas de ruff sigue activo, también en las escritas a mano.
- Una migración de datos obtiene el modelo con `apps.get_model` (nunca importa el actual), escribe con `.using(schema_editor.connection.alias)`, siembra con `update_or_create` y declara un `reverse_code` explícito con un único `delete()` de QuerySet. Nunca `RunPython.noop`: revertir dejaría los datos.

## Errores de dominio y guardado protegido
- Los servicios lanzan `DomainValidationError` (`apps/core/errors.py`): solo campos y códigos estables en inglés, nunca el valor ni `params`. `translate_validation_error` convierte `(campo, código de Django)` en `(campo, código de dominio)`; una restricción con `Lower` llega en `__all__` y el mapa la lleva a su campo.
- El `IntegrityError` lleva el valor duplicado en su mensaje. El guardado va en `transaction.atomic()`, lee `exc.__cause__.diag.constraint_name` y **devuelve** los códigos; quien llama lanza fuera del `except`, así `__context__` y `__cause__` quedan en `None`. Si la restricción no tiene nombre, el resultado es `constraint_violated`: sin ese caso el error se tragaría y el servicio devolvería un objeto no guardado.
- Una instancia que ya existe se guarda con `save(update_fields=[...])`, y "existe" se decide con `_state.adding`, no con `pk`. Si la fila se borró, Django lanza `DatabaseError` en vez de reinsertarla.
- Los nombres automáticos de `unique=True` (`<tabla>_<campo>_key`) no salen en `sqlmigrate`; los fija un test con `diag.constraint_name`.
- El guardado protegido está copiado en `users` y `categories`; se extrae a `apps/core` en la tercera repetición.

## Texto: normalización y validación
- Recorta con `str.strip()`. El email va en NFKC y en minúsculas; los nombres, en NFC (NFKC cambiaría su significado al plegar ligaduras). La longitud se cuenta después de normalizar.
- `reject_control_characters` solo cubre la categoría Cc. Los Cf (U+202E, U+200B, U+200D) pasan, y `validate_email` los acepta en el dominio aunque los rechaza en la parte local. Qué Cf se rechazan es una decisión de cada spec, con cuidado de los legítimos como U+200D.
- `LOWER` de PostgreSQL con tildes depende de `LC_CTYPE`: la BD debe ser UTF-8 o `Jardín` y `JARDÍN` no chocarían. Un test lo fija en test y CI; la de producción se comprueba al desplegar.

## Tests de BD, de migraciones de datos y de fugas
- Unicidad y longitud en la BD: guarda saltándote la validación, dentro de `pytest.raises(...)` y `transaction.atomic()`, y espera `IntegrityError` (unicidad, con el nombre exacto de la restricción) o `DataError` (longitud).
- Las funciones de una migración de datos se prueban con las apps históricas (`MigrationLoader(connection).project_state(...)`) y un `schema_editor` sustituto que solo aporta `.connection`. Un test del alias (`ConnectionDoesNotExist`) demuestra que no escriben en `default` por casualidad.
- La semilla vive en la BD de test: los tests usan datos fuera de ella y comparan recuentos, no totales. Un test con `transaction=True` la vaciaría para los siguientes; usa `serialized_rollback`.
- Los caracteres invisibles o combinantes (NBSP, tildes descompuestas, ligaduras) se escriben en los tests como escapes Unicode, nunca literales: un editor que normalice haría que el test dejara de probar lo que dice.
- Para comprobar que no se filtra un valor: una marca que no aparece en ningún identificador ni línea de la llamada (el traceback imprime el código fuente), `caplog` a DEBUG y `connection.force_debug_cursor` para que Django intente registrar el SQL con sus valores.

## Pruebas de mecanismo
Un test en verde desde el principio no demuestra que detecte nada. Tras implementar una regla de seguridad o de integridad, rompe el código a propósito, una mutación cada vez, con el sha256 del fichero antes y después; comprueba qué test falla y por qué, y revierte a mano. Si una mutación no hace fallar ningún test, o falta un test o la mutación no cambia el comportamiento (como NON_EMAIL_FIELDS hoy); en el segundo caso se dice de forma explícita en validation.md. Se registran en `validation.md`.

## Tests y verificación
- Los tests de cada app van en un paquete `tests/` dentro de la app, con un módulo por capa o por endpoint.
- Reinicia el backend con `docker compose restart backend` al crear módulos nuevos, añadir una app a `INSTALLED_APPS` o tocar `AppConfig.ready()`. El autorecargador solo vigila los módulos ya importados, y lo que se registra en `ready()` o una app nueva solo se carga al arrancar. Para editar ficheros que ya existen no hace falta.
- `docker compose exec backend pytest -q` en verde antes de cada commit. El test se escribe primero y debe fallar por la razón esperada.
