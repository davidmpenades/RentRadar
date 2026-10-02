# MEMORY.md — RentRadar
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no aporte.
Lo que se vuelva permanente se mueve a AGENTS.md, a una skill o a docs/constitution.md.

## Estado actual
- Arnés montado: AGENTS.md, MEMORY.md, MCPs (Context7, Chrome DevTools) y skills de terceros.
- Constitución aprobada en docs/constitution.md.
- Arnés con subagentes: planner, implementer y tres revisores (quality, security, docs) en paralelo.
- Spec activa: 001-backend-skeleton, en curso en feature/001-backend-skeleton (progreso en su tasks.md).
- Specs en borrador: 002-quality-gates (pre-commit, gitleaks, CI) y 003-health-checks (vida y preparación). Orden: 001, 002, 003.

## Decisiones (y por qué)
- SDD desde el primer commit: cada funcionalidad nace como spec, plan y tareas aprobados.
- Producto: alquiler de bienes (productos y espacios) entre particulares o profesionales.
- Specs pequeñas (≤10 tareas): un cambio grande se parte en varias specs para revisarse bien.
- Solo el agente principal escribe MEMORY.md; los subagentes informan y el usuario valida.
- Imágenes: Pillow a WebP en el backend; disco local en dev y Cloudflare R2 en producción.
- Geocodificación detrás de una interfaz con un adaptador por proveedor; el Nominatim público no sirve para producción.
- Recurso ajeno: 404 si el usuario no puede verlo (no revela que existe), 403 si puede verlo pero no modificarlo.
- Lanzamiento en España (castellano, euros); objetivo Europa. i18n desde el día 1.
- Web y móvil (Expo) como objetivo; autenticación válida para ambos y API versionada.
- Mapa con MapLibre (web y nativo), a validar en la spec del frontend.
- Backend: apps en backend/apps/<app>/; solo config/env.py lee el entorno; PostGIS 18-3.6 (fuera del rango declarado por Django 5.2, lo vigila el test de RF-5).
- Ubicaciones en PostGIS geography; precios con importe y moneda.
- Backend en capas: servicios (escrituras y reglas), selectores (lecturas), serializers y vistas solo traducen.
- Una rama feature/NNN-slug por spec, creada desde dev; la spec se escribe en dev para que quede aunque no se implemente.

## Riesgos conocidos (detalle en la skill indicada)
- Backend (Nominatim, 403/401 con sesión, locks de pip, caché por proceso): ver skill django-drf.
- jsdom no calcula layout: el overflow y el responsive se verifican en navegador real. → testing
- Mocks de fetch: respetar AbortSignal y ordenar las claves de más a menos específica. → testing
- Leaflet captura eventos de puntero, si se usa Leaflet: los menús que cierran al hacer clic fuera escuchan pointerdown en fase de captura. → react-ts
- Las afirmaciones de un agente se comprueban contra el código antes de darlas por buenas.

## Aprendizajes de este proyecto
- (vacío por ahora)

## Próximos pasos
- Escribir las skills react-ts y testing a partir de Riesgos conocidos.
- Implementar la 001 tarea a tarea (T3 crea docs/architecture.md). Después, clarificar 002 y 003.
- Al cerrar la 001, en el commit de AGENTS.md (sección Comandos): las órdenes que escriben en el bind mount (p. ej. `ruff format`) van con `docker compose run --rm -u "$(id -u)" backend …`, porque el UID 10001 no puede escribir.
- Spec del frontend (Vite): en su plan, decidir Zod o guardas de tipo a mano para validar las respuestas de la API.
- Spec de despliegue: HTTPS, HSTS, cabecera de proxy, check --deploy en CI, servidor e imagen de producción, capacidad para sondas, migraciones antes del tráfico.
- Ubicación y privacidad: confirmar lo pendiente en docs/product.md (celda, profesionales, mapa) y decidir si hay reservas.
- docs/product.md con grill-me (incluye RGPD, DSA y DAC7 como requisitos a tener en cuenta).
