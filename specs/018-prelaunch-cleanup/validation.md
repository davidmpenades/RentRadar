# Validación 018 — Limpieza antes de lanzar
Spec: specs/018-prelaunch-cleanup/spec.md · Plan: specs/018-prelaunch-cleanup/plan.md · Tareas: specs/018-prelaunch-cleanup/tasks.md
Rama: `feature/018-prelaunch-cleanup`, sobre `dev` (`7a19d14`).

## RF-9 — Atribución del mapa
Fecha de la consulta: 17-11-2026, 16:46 UTC. Descarga con `curl -sS -L` a una carpeta temporal de la sesión de trabajo, fuera del repositorio.

Páginas descargadas:
- `https://openfreemap.org/`: HTTP 200, 12 771 bytes, sha256 `3408380cd0ce061b06441e5a8c5cdf4ee67d618907e71edee74f23efdd616934`. Es la misma huella que en la consulta del plan (17-11-2026, 16:05 UTC).
- `https://openfreemap.org/tos/`: HTTP 200, 6 333 bytes, sha256 `27327213fb5dd57ac76119a3f8b9251e682eb44ee4fad04fec67138383aaed02`. `grep -F -i -c 'attribution'`: 0.
- `https://openfreemap.org/quick_start/`: HTTP 200, 17 401 bytes, sha256 `b069069e6ca9bb7778f8958e3be628730b10c9fbe9c56e54e20bb63046f000d0`. `grep -F -i -c 'attribution'`: 0.

Cita de la página principal, sección «Attribution», comprobada con `grep -F -c` frase a frase:
- «Attribution is required. If you are using MapLibre, they are automatically added, you have nothing to do.»: 1 línea.
- «If you are using alternative clients, or if you are using this in printed media or video, you must add the following attribution:»: 1 línea.
- `<a href="https://openfreemap.org" target="_blank">OpenFreeMap</a> <a href="https://www.openmaptiles.org/" target="_blank">© OpenMapTiles</a> Data from <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a>`: 2 líneas. Son la 41, la de la sección «Attribution», y la 7, la del mapa de demostración de la propia página.
- «You do not need to display the OpenFreeMap part, but it is nice if you do.»: 1 línea.

Excepción al punto 8 de la constitución (interfaz en castellano): la atribución del mapa conserva «Data from» en inglés, porque es parte del texto que la página da como atribución (D2 = A del plan). `frontend/src/map/style.ts:5` mantiene ese texto y `frontend/src/map/style.test.ts:122` lo fija.

El código no cambia: `git diff --quiet 7a19d14 HEAD -- frontend` sale con 0.
