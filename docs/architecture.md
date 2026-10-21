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
    │   ├── management/commands/wait_for_db.py
    │   └── migrations/    # 0001 declara la extensión PostGIS (necesaria en BD gestionadas)
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

## Arranque y aislamiento de tests
El `ENTRYPOINT` del contenedor ejecuta `wait_for_db`, que reintenta la conexión hasta 60 s y, si no llega, falla con un mensaje fijo sin credenciales. Durante los tests, un fixture autouse de `backend/conftest.py` bloquea los sockets de internet (libpq y los sockets AF_UNIX siguen funcionando; el loopback TCP, 127.0.0.1 y ::1, también queda bloqueado) y una guarda aborta la sesión si la BD de test no contiene `test` o coincide con `DB_NAME`.
