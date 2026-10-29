# MEMORY.md — RentRadar
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no aporte.
Lo que se vuelva permanente se mueve a AGENTS.md, a una skill o a docs/constitution.md.

## Estado actual
- Arnés montado (AGENTS.md, MEMORY.md, MCPs Context7 y Chrome DevTools, skills de terceros) con subagentes: planner, implementer y tres revisores (quality, security, docs) en paralelo. Constitución aprobada en docs/constitution.md.
- 001-backend-skeleton, 002-quality-gates y 004 (usuarios y categorías, specs/004-users-and-categories/validation.md) completadas y validadas; PR #3 y #5 mergeadas en dev. Pre-commit, detección de secretos y escaneo del historial pasan a una spec posterior. 003-health-checks aplazada hasta la spec de despliegue.
- 005 (assets y privacidad de ubicación) completada y validada, specs/005-assets-and-location-privacy/validation.md; PR a dev pendiente.

## Decisiones (y por qué)
- SDD desde el primer commit: cada funcionalidad nace como spec, plan y tareas aprobados.
- Producto: alquiler de bienes (productos y espacios) entre particulares o profesionales.
- Specs verticales y pequeñas (≤10 tareas; el tope de RF y la verificación en navegador, en AGENTS.md): un cambio grande se parte en varias para revisarse bien.
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
- Errores de dominio: DomainValidationError lleva solo campos y códigos, y los servicios lo lanzan fuera del except. El guardado protegido vive en apps/core/db.py (run_guarded), extraído en la T3 de la 005 tras su tercera repetición; users y categories lo usan. Las categorías solo cambian por migración.

## Riesgos conocidos (detalle en la skill indicada)
- Una sesión en segundo plano no puede editar dev; para implementar, sesión en primer plano.
- Backend (Nominatim, 403/401 con sesión, locks de pip, caché por proceso): ver skill django-drf.
- jsdom no calcula layout: el overflow y el responsive se verifican en navegador real; en los mocks de fetch se respeta AbortSignal y se ordenan las claves de más a menos específica. → testing
- Leaflet captura eventos de puntero, si se usa Leaflet: los menús que cierran al hacer clic fuera escuchan pointerdown en fase de captura. → react-ts
- Las afirmaciones de un agente se comprueban contra el código antes de darlas por buenas.
- Montaje de un fichero individual (./.env.example): un `sed -i` en el host cambia el inode y el contenedor sigue viendo el antiguo; se arregla recreando el contenedor.
- Tests: solo dentro del contenedor (geteuid == 10001) y con el loopback bloqueado por el fixture de red; psycopg resuelve el host en Python, así que una segunda conexión a la BD también queda bloqueada.

## Aprendizajes de este proyecto
- El backend postgis de Django crea la extensión por su cuenta (prepare_database, llamado desde migrate); la migración 0001 sirve para BD gestionadas.
- Las herramientas de edición convierten \uXXXX en el carácter literal: los escapes se escriben desde un script con chr(92). Los tests no llevan caracteres invisibles (NBSP, tildes descompuestas, ligaduras) escritos literales; se comprueba con una detección por categoría Unicode.
- La semilla de categorías vive en la BD de test: un test con transaction=True la vaciaría para los siguientes (usar serialized_rollback).
- Pruebas de mecanismo: se mutan los ficheros nuevos de la tarea, con sha256 antes y después; lo ajeno (p. ej. core/db.py) con un plugin de pytest de usar y tirar en el /tmp del contenedor (`pytest -p`, con PYTHONPATH=/tmp/x:/app); las mutaciones de migraciones, con `pytest --create-db`; las reglas por AST, con un módulo temporal sin versionar bajo backend/apps, escrito desde el host y borrado en el mismo comando.
- Tests de servicios: se parchean los nombres donde se usan (`apps.<app>.services`) y las funciones privadas son keyword-only; con la red bloqueada no hay segunda conexión, así que un `select_for_update` se verifica por el orden del SQL con `CaptureQueriesContext`.
- Ruff aplica las 88 columnas también a los comentarios; para ver ficheros nuevos en `git diff` se usa `git add -N`.

## Próximos pasos
- Antes del primer endpoint, decidir para web y móvil (Expo): autenticación (JWT o sesión web + JWT móvil), errores con códigos que traduce el cliente, OpenAPI con drf-spectacular y CORS para la web. Además, que la página de error de DEBUG no imprima las coordenadas de las variables locales de los servicios (`sensitive_variables`, o confirmar que producción nunca lo activa).
- /sdd-change pendiente sobre caracteres de formato: el dominio del email de la 004 acepta Cf (p. ej. U+202E) y el título de la 005 acepta U+2028 y U+2029.
- Ajuste manual del propietario: protección de rama de dev en GitHub (el CI ya está en verde); aprobación de workflows de forks.
- Escribir las skills react-ts y testing a partir de Riesgos conocidos.
- Spec del frontend (Vite): en su plan, decidir Zod o guardas de tipo a mano para validar las respuestas de la API.
- Spec de despliegue: HTTPS, HSTS, cabecera de proxy, check --deploy en CI, servidor e imagen de producción, capacidad para sondas, migraciones antes del tráfico, DB_PASSWORD de 16 caracteres como mínimo en producción (cambio de spec con /sdd-change); nivel de detalle del log de PostgreSQL (sus errores de unicidad incluyen el valor, y los de un CHECK de bienes la fila con las coordenadas: la spec 005 solo cubre los logs de la aplicación); localización de la BD de producción (LC_CTYPE UTF-8: con la C, Jardín y JARDÍN no chocarían); borrado o anonimización de cuentas (RGPD, art. 17) obligatorio antes de abrir a usuarios reales.
- Ubicación y privacidad: confirmar lo pendiente en docs/product.md (celda, profesionales, mapa). Hay reservas en el MVP: solicitud simple, el arrendatario pide fechas y el propietario acepta o rechaza; la dirección exacta se revela al confirmar. docs/product.md con grill-me (incluye RGPD, DSA y DAC7 como requisitos a tener en cuenta).
