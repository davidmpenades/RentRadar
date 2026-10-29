# Arquitectura del backend

## Estructura
```
backend/
├── manage.py              # Resuelve DJANGO_ENV antes de cargar Django
├── docker-entrypoint.sh   # Espera a la BD (wait_for_db) y ejecuta la orden del contenedor
├── conftest.py            # Guarda de la BD de test y fixture que bloquea la red
├── config/
│   ├── env.py             # Único lector de os.environ; valida sin mostrar valores
│   ├── log_redaction.py   # Formatter que tapa secretos en los logs de producción
│   ├── settings/
│   │   ├── base.py        # Común y seguro por defecto (DEBUG=False, UTC, es)
│   │   ├── development.py # DEBUG según DJANGO_DEBUG; BD desde el entorno
│   │   ├── test.py        # DEBUG siempre apagado; BD rentradar_test
│   │   └── production.py  # Rechaza la configuración insegura
│   ├── urls.py
│   ├── wsgi.py / asgi.py  # Mismo resolvedor que manage.py
│   └── tests/
└── apps/                  # Una carpeta por app: core y las de dominio
    ├── core/
    │   ├── db_wait.py     # Espera a la BD con reloj y pausa inyectados
    │   ├── text.py        # Detección de caracteres de control y su validador de Django
    │   ├── errors.py      # Error de dominio (solo campos y códigos) y traducción de errores de Django
    │   ├── db.py          # run_guarded: guardado protegido que traduce las restricciones de la BD a códigos
    │   ├── management/commands/wait_for_db.py
    │   └── migrations/    # 0001 declara la extensión PostGIS (necesaria en BD gestionadas)
    ├── users/             # Usuario identificado por email
    │   ├── models.py      # User y su gestor (normaliza el email y delega el alta en el servicio)
    │   └── services.py    # Alta de usuarios y superusuarios, cambio de email
    ├── categories/        # Lista cerrada de categorías
    │   ├── models.py      # Category y la normalización de su nombre
    │   ├── services.py    # save_category: valida, normaliza y guarda
    │   └── migrations/    # 0002 siembra las once categorías
    ├── assets/            # Bienes en alquiler y privacidad de su ubicación
    │   ├── location.py    # Función de aproximación (pura): centro de la celda de la cuadrícula
    │   ├── rules.py       # Reglas de los campos (puras): texto, precio, radio, estado, coordenadas
    │   ├── models.py      # Asset: ubicación exacta y pública en campos separados, CHECK con nombre
    │   ├── services.py    # create_asset y update_asset: única vía de escritura de bienes
    │   └── migrations/    # 0001 depende de categories.0001, no de la semilla
    └── <app>/
        ├── models.py
        ├── services.py    # Escrituras y reglas de negocio
        ├── selectors.py   # Lecturas (querysets con select_related, annotate…)
        ├── serializers.py # Solo traducen entre JSON y Python
        ├── views.py       # Solo traducen entre HTTP y servicios/selectores
        ├── migrations/
        └── tests/
```

## Selección de entorno
`DJANGO_ENV` (`development`, `test` o `production`) decide el módulo de settings. `manage.py`, `wsgi.py` y `asgi.py` llaman a `configure_settings_module()`, que siempre sobrescribe `DJANGO_SETTINGS_MODULE`. Un valor distinto de los tres impide arrancar. pytest usa siempre `config.settings.test` (`--ds` en `pyproject.toml`).

## Capas
Las vistas y los serializers no contienen reglas de negocio ni hacen consultas propias: las escrituras van en `services.py` y las lecturas en `selectors.py`. Los tests de cada app viven en `apps/<app>/tests/`; los de configuración, en `config/tests/`.

## Errores de dominio
Los servicios no devuelven los errores de Django tal cual: los traducen a `DomainValidationError`, una subclase de `ValidationError` que solo contiene campos y códigos estables en inglés (`email_taken`, `name_too_long`…), nunca el valor recibido ni sus parámetros. Cada servicio expone sus códigos como constantes, y un test compara el conjunto con la tabla del plan.
- `translate_validation_error` convierte cada par (campo, código de Django) en un par (campo, código de dominio); lo que no está en el mapa pasa a `validation_failed`. El campo de destino puede ser otro: la violación de una restricción de unicidad con `Lower` llega en `__all__` y se coloca en su campo.
- `run_guarded(write, constraint_codes)` (en `core/db.py`) ejecuta el bloque entero dentro de un `atomic`, captura el `IntegrityError` fuera de él, lee el nombre de la restricción (`diag.constraint_name`, sin leer el mensaje, que lleva el valor) y devuelve `(resultado, códigos)`. El servicio lanza el error de dominio fuera de cualquier `except`, de modo que no queda encadenado al error original. Lo usan users, categories y assets.
- Antes de salir del bloque ejecuta `SET CONSTRAINTS ALL IMMEDIATE` y después `ALL DEFERRED`: una clave foránea violada salta dentro del `try` y se traduce, en lugar de saltar en el `COMMIT` de una transacción exterior, y las restricciones quedan diferidas sea cual sea el modo con el que se entró. Si el bloque falla, el savepoint restaura el modo de entrada.
- Un `DomainValidationError` lanzado dentro de `write` deshace el `atomic` y sale tal cual; un `DatabaseError` que no es de integridad se propaga.
- Una restricción desconocida o sin nombre (un `NOT NULL`) da `constraint_violated`.

## Ubicación de los bienes
- Cada bien guarda dos ubicaciones en campos `geography` separados. La exacta es privada. La pública es la única que se muestra o se usa para buscar, y se deriva de la exacta y del radio de privacidad (500, 1000 o 2000 m).
- `approximate_location` proyecta la coordenada a EPSG:3035, localiza la celda cuadrada de lado igual al radio (los bordes inferior e izquierdo pertenecen a la celda) y devuelve su centro en latitud y longitud, a 6 decimales. No consulta la BD ni la red, y crea las referencias espaciales en cada llamada porque GDAL no es seguro entre hilos. Cambiar la proyección o el origen movería todas las celdas ya publicadas.
- `create_asset` y `update_asset` son las únicas funciones que escriben bienes, y solo `services.py` obtiene `Asset` y `approximate_location` (lo vigila un test por AST). No admiten una ubicación pública ni un propietario nuevo: fallan con un `TypeError`. La hora entra como parámetro. Fuera de `apps/assets`, el servicio solo se usa importando por nombre esas dos funciones y nadie llega a la app por `get_app_config("assets")`; otro test por AST lo vigila.
- `update_asset` bloquea la fila con `select_for_update` como primera lectura del bien, compara con el estado guardado y escribe solo las columnas que cambian. Con el bien activo no deja cambiar la ubicación exacta ni el radio.
- Las FK de `owner` y `category` son `PROTECT` y sin `related_name`: borrar un usuario o una categoría con bienes se rechaza, también al revertir la semilla de categorías.
- Ni los errores, ni `str()` ni `repr()` ni los logs contienen coordenadas. `test_leaks.py` lo comprueba con coordenadas centinela en 22 formas.

## Logs
`django.db.backends` está fijado en INFO en los tres entornos (en producción, con el handler que redacta secretos): con DEBUG, Django registra cada consulta con sus valores, entre ellos el email y el hash.

## Arranque y aislamiento de tests
El `ENTRYPOINT` del contenedor ejecuta `wait_for_db`, que reintenta la conexión hasta 60 s y, si no llega, falla con un mensaje fijo sin credenciales. Durante los tests, un fixture autouse de `backend/conftest.py` bloquea los sockets de internet (libpq y los sockets AF_UNIX siguen funcionando; el loopback TCP, 127.0.0.1 y ::1, también queda bloqueado) y una guarda aborta la sesión si la BD de test no contiene `test` o coincide con `DB_NAME`.
