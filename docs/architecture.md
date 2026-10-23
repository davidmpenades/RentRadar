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
    │   ├── management/commands/wait_for_db.py
    │   └── migrations/    # 0001 declara la extensión PostGIS (necesaria en BD gestionadas)
    ├── users/             # Usuario identificado por email
    │   ├── models.py      # User y su gestor (normaliza el email y delega el alta en el servicio)
    │   └── services.py    # Alta de usuarios y superusuarios, cambio de email
    ├── categories/        # Lista cerrada de categorías
    │   ├── models.py      # Category y la normalización de su nombre
    │   ├── services.py    # save_category: valida, normaliza y guarda
    │   └── migrations/    # 0002 siembra las once categorías
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
- El guardado captura el `IntegrityError` dentro de una transacción atómica, lee el nombre de la restricción (`diag.constraint_name`, sin leer el mensaje, que lleva el valor) y devuelve los códigos. El servicio lanza el error de dominio fuera de cualquier `except`, de modo que no queda encadenado al error original.
- Una restricción desconocida da `constraint_violated`.

## Logs
`django.db.backends` está fijado en INFO en los tres entornos (en producción, con el handler que redacta secretos): con DEBUG, Django registra cada consulta con sus valores, entre ellos el email y el hash.

## Arranque y aislamiento de tests
El `ENTRYPOINT` del contenedor ejecuta `wait_for_db`, que reintenta la conexión hasta 60 s y, si no llega, falla con un mensaje fijo sin credenciales. Durante los tests, un fixture autouse de `backend/conftest.py` bloquea los sockets de internet (libpq y los sockets AF_UNIX siguen funcionando; el loopback TCP, 127.0.0.1 y ::1, también queda bloqueado) y una guarda aborta la sesión si la BD de test no contiene `test` o coincide con `DB_NAME`.
