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

## Tests y verificación
- Los tests de cada app van en un paquete `tests/` dentro de la app, con un módulo por capa o por endpoint.
- Reinicia el backend con `docker compose restart backend` al crear módulos nuevos, añadir una app a `INSTALLED_APPS` o tocar `AppConfig.ready()`. El autorecargador solo vigila los módulos ya importados, y lo que se registra en `ready()` o una app nueva solo se carga al arrancar. Para editar ficheros que ya existen no hace falta.
- `docker compose exec backend pytest -q` en verde antes de cada commit. El test se escribe primero y debe fallar por la razón esperada.
