# MEMORY.md — RentRadar
Memoria del proyecto entre sesiones. Máximo ~50 líneas: resume o elimina lo que ya no aporte.
Lo que se vuelva permanente se mueve a AGENTS.md, a una skill o a docs/constitution.md.

## Estado actual
- Arnés montado: AGENTS.md, MEMORY.md, MCPs (Context7, Chrome DevTools) y skills de terceros.
- Sin código todavía. Spec activa: ninguna.

## Decisiones (y por qué)
- SDD desde el primer commit: cada funcionalidad nace como spec, plan y tareas aprobados.
- Producto: alquiler de bienes (productos y espacios) entre particulares o profesionales.
- Specs pequeñas (≤10 tareas): un cambio grande se parte en varias specs para revisarse bien.
- Solo el agente principal escribe MEMORY.md; los subagentes informan y el usuario valida.
- Imágenes: Pillow a WebP en el backend; disco local en dev y Cloudflare R2 en producción.
- Geocodificación a través de un proxy en el backend: el navegador no puede fijar el User-Agent que exige Nominatim.

## Riesgos conocidos (detalle en la skill indicada)
- Nominatim: las calles necesitan búsqueda estructurada (street + city); el texto libre falla. → django-drf
- DRF con sesión: el anónimo recibe 403, no 401. → django-drf
- Locks de pip con hashes: regenerarlos sin --no-index y revisar el diff. → django-drf
- Caché local por proceso: con varios workers, los límites de tasa se multiplican. Antes del despliegue, caché compartida. → django-drf
- jsdom no calcula layout: el overflow y el responsive se verifican en navegador real. → testing
- Mocks de fetch: respetar AbortSignal y ordenar las claves de más a menos específica. → testing
- Leaflet captura eventos de puntero: los menús que cierran al hacer clic fuera escuchan pointerdown en fase de captura. → react-ts
- Las afirmaciones de un agente se comprueban contra el código antes de darlas por buenas.

## Aprendizajes de este proyecto
- (vacío por ahora)

## Próximos pasos
- Skill sdd y comandos /feature y /sdd-*.
- Constitución con /sdd-constitution.
- Spec 001: esqueleto del proyecto (Docker, Django, Vite).