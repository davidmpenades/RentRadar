# Arquitectura del backend

## Estructura
```
backend/
├── manage.py              # Resuelve DJANGO_ENV antes de cargar Django
├── config/
│   ├── env.py             # Único lector de os.environ; valida sin mostrar valores
│   ├── settings/
│   │   ├── base.py        # Común y seguro por defecto (DEBUG=False, UTC, es)
│   │   ├── development.py # DEBUG según DJANGO_DEBUG; BD desde el entorno
│   │   ├── test.py        # DEBUG siempre apagado; BD rentradar_test
│   │   └── production.py  # (T4) Rechaza la configuración insegura
│   ├── urls.py
│   ├── wsgi.py / asgi.py  # Mismo resolvedor que manage.py
│   └── tests/
└── apps/                  # (T5) Una carpeta por app: core y las de dominio
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
