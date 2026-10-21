# MEMORY.md — RentRadar
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no aporte.
Lo que se vuelva permanente se mueve a AGENTS.md, a una skill o a docs/constitution.md.

## Estado actual
- Arnés montado: AGENTS.md, MEMORY.md, MCPs (Context7, Chrome DevTools) y skills de terceros.
- Constitución aprobada en docs/constitution.md.
- Arnés con subagentes: planner, implementer y tres revisores (quality, security, docs) en paralelo.
- Spec 001-backend-skeleton completada y validada (evidencia en specs/001-backend-skeleton/validation.md); PR #2 mergeado en dev.
- 002-quality-gates (CI mínimo: GitHub Actions + Compose, lint y tests) implementada y validada en GitHub (specs/002-quality-gates/validation.md); pendiente de que el usuario mergee la PR #3 a dev. Pre-commit, detección de secretos y escaneo del historial pasan a una spec posterior.
- 003-health-checks aplazada hasta la spec de despliegue.

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
- La evidencia de las comprobaciones manuales de cada spec se registra en specs/NNN/validation.md, con fecha, orden y resultado.
- git push está denegado a los agentes en .claude/settings.json; los push los hace el usuario.

## Riesgos conocidos (detalle en la skill indicada)
- Backend (Nominatim, 403/401 con sesión, locks de pip, caché por proceso): ver skill django-drf.
- jsdom no calcula layout: el overflow y el responsive se verifican en navegador real. → testing
- Mocks de fetch: respetar AbortSignal y ordenar las claves de más a menos específica. → testing
- Leaflet captura eventos de puntero, si se usa Leaflet: los menús que cierran al hacer clic fuera escuchan pointerdown en fase de captura. → react-ts
- Las afirmaciones de un agente se comprueban contra el código antes de darlas por buenas.
- Montaje de un fichero individual (./.env.example): un `sed -i` en el host cambia el inode y el contenedor sigue viendo el antiguo; se arregla recreando el contenedor.
- Tests: solo dentro del contenedor (geteuid == 10001) y con el loopback bloqueado por el fixture de red.

## Aprendizajes de este proyecto
- El backend postgis de Django crea la extensión por su cuenta (prepare_database, llamado desde migrate); la migración 0001 sirve para BD gestionadas.

## Próximos pasos
- Abrir la 004 (User custom y Asset). Antes del primer endpoint, decidir para web y móvil (Expo): autenticación (JWT para todos o sesión web + JWT móvil), formato de errores con códigos que traduce el cliente, OpenAPI con drf-spectacular y CORS para la web.
- Ajuste manual del propietario: protección de rama de dev en GitHub (el CI ya está en verde); aprobación de workflows de forks.
- Contrato para la 004: los tests de modelos nuevos exigen su migración (lo vigila config/tests/test_migrations.py).
- Escribir las skills react-ts y testing a partir de Riesgos conocidos.
- Spec del frontend (Vite): en su plan, decidir Zod o guardas de tipo a mano para validar las respuestas de la API.
- Spec de despliegue: HTTPS, HSTS, cabecera de proxy, check --deploy en CI, servidor e imagen de producción, capacidad para sondas, migraciones antes del tráfico, DB_PASSWORD de 16 caracteres como mínimo en producción (cambio de spec con /sdd-change).
- Ubicación y privacidad: confirmar lo pendiente en docs/product.md (celda, profesionales, mapa). Hay reservas en el MVP: solicitud simple, el arrendatario pide fechas y el propietario acepta o rechaza; la dirección exacta se revela al confirmar.
- docs/product.md con grill-me (incluye RGPD, DSA y DAC7 como requisitos a tener en cuenta).
