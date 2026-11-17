# Validación 018 — Limpieza antes de lanzar
Spec: specs/018-prelaunch-cleanup/spec.md · Plan: specs/018-prelaunch-cleanup/plan.md · Tareas: specs/018-prelaunch-cleanup/tasks.md
Rama: `feature/018-prelaunch-cleanup`, sobre `dev` (`7a19d14`).
Fecha de la validación: 17-11-2026. Las órdenes de RF-1 a RF-8 y RF-10 se repitieron sobre `d9ff5e6`.

## Commits
- Spec, plan y tareas: `1ab1f82` docs(spec-018): prelaunch cleanup, `c3d9f83` docs(spec-018): plan y `0601115` docs(spec-018): tasks.
- T1 `8d912bf` docs(spec-017): correct webp history in provenance
- T2 `3d77f1e` docs(specs): remove home paths from records
- T3 `5ee1d19` chore(git): ignore key files and dumps
- T4 `db58b48` chore(claude): ask before removing containers with volumes
- T5 `f36cad1` docs(spec-018): record map attribution check
- T6 `b222c61` docs(memory): note prelaunch review follow-ups
- Casillas: T1 `0085436`, T2 `f430980`, T3 `230607e`, T4 `585be15`, T5 `fe1bfb7` y T6 `d9ff5e6`.

## RF-1 — Solo la v2 entró en git
- `git show --name-status --format= 406b9af | grep -c '^A.*\.webp$'`: 12.
- `git show --name-status --format= 2599bc3 | grep -c '\.webp$'`: 0.
- El apartado «Procedencia» de `specs/017-category-images/validation.md` lo dice así desde `8d912bf`.

## RF-2 — Siguen en el historial publicado y el producto no las sirve
- `git branch -r --contains 406b9af`: `origin/dev` y `origin/feature/017-category-images`.
- `git ls-tree -r --name-only` en `63b98cb` y en `HEAD`, filtrando `.webp` fuera de `frontend/src/assets/categories/`: 0 y 0. `63b98cb` modifica las doce de esa carpeta.
- Grep de metadatos de la 017 (`EXIF|XMP |ICCP|c2pa|jumb|Gemini`) sobre las doce `git show 406b9af:<ruta>`: ningún positivo. Por eso el texto mantiene «sin metadatos».
- La decisión de no purgarlas está escrita en el mismo apartado, con su fecha.

## RF-3 — Lo no comprobable con git, como «según el desarrollador»
- Lectura del párrafo: lleva esa marca la afirmación de que once WebP son las de la v1 y el kayak es el regenerado, que git no puede comprobar. La decisión de no purgar figura como del desarrollador. El resto cita la orden de git que lo comprueba.

## RF-4 — Sin rutas personales ni el usuario del sistema
- `git grep -nIE '/hom[e]/'`: sin resultados, código 1.
- `git grep -nIiw "$(id -un)"`: sin resultados, código 1.
- Antes de la T2 salían las tres líneas de `specs/006-public-map/validation.md` (545, 642 y 712) y `specs/017-category-images/tasks.md:21`.
- Prueba de mecanismo, sin escribir ficheros:
  - `/hom[e]/` encuentra una línea fabricada con `printf` (código 0) y no un texto sin ruta (código 1).
  - `-iw` con el usuario encuentra la ruta fabricada (código 0) y no la cuenta de GitHub de los enlaces (código 1).

## RF-5 — La copia temporal de la 006, sin ruta
- `grep -c` de «carpeta temporal de la sesión de trabajo, fuera del repositorio (`t» en `specs/006-public-map/validation.md`: 3.

## RF-6 — git ignora claves y volcados
- `git check-ignore --no-index a.pem backend/b.key x/c.p12 id_rsa id_rsa.pub d/e.sql f.dump`: las 7 rutas, código 0.
- `git ls-files -ci --exclude-standard`: 0 ficheros versionados coinciden.
- `git status --short --ignored` antes y después del cambio: la misma lista de ignorados (en la T3).

## RF-7 — `.env.example` no se ignora
- `git check-ignore -q --no-index .env.example`: código 1; `… frontend/.env.example`: código 1.
- `git check-ignore --no-index .env backend/.env frontend/.env.local`: las 3 siguen ignoradas.

## RF-8 — Pregunta antes de borrar contenedores con volúmenes
- `python3 -I -m json.tool .claude/settings.json`: código 0. La lista `ask` lleva `"Bash(docker rm -v:*)"` y `"Bash(docker compose rm -v:*)"`; el diff de `db58b48` solo cambia esa lista.
- Primera ejecución de `docker rm -v rentradar-no-existe-t4-018`: se ejecutó sin pregunta y falló con «Error response from daemon: No such container: rentradar-no-existe-t4-018», código 1, sin efectos.
- Prueba de control, según el desarrollador: al ejecutar `git merge rentradar-no-existe-t4-018`, que coincide con la regla previa `Bash(git merge:*)`, apareció la pregunta; la denegó y la orden no se ejecutó.
- Segunda ejecución de `docker rm -v rentradar-no-existe-t4-018`, repetida minutos después de la primera: apareció la pregunta, el desarrollador la denegó y la orden no se ejecutó.
- Según el desarrollador, en `/permissions` las dos reglas nuevas aparecen en la pestaña Ask.
- Nota: después de editar la configuración, una regla nueva puede tardar en actuar; hay que repetir la prueba antes de darla por buena.

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

## RF-10 — Memoria del proyecto
Commit `b222c61`. Comprobado sobre `MEMORY.md`:
- `wc -l`: 50.
- La 017 lleva «(PR #10)» y la spec activa es la 018.
- Hoja de ruta: 018 → 015 entrada (con el aviso pendiente de `user_logged_out`, sin fondos con fotos) → 007 → … → 014 → fotos de registro y entrada → 008 → 011 → 012 → pagos.
- Notas nuevas: servidor de producción en la 011, consulta de la lista pública y EXPLAIN en la 007, y licencias (OFL-1.1 y cuatro skills) en la 014.
- Salen de «Pendientes sueltos»:
  - la duda de purgar las WebP, sin sustituirla;
  - «añadir docker rm -v…», hecho en la T4;
  - «comprobar índice espacial y consultas N+1», porque no hay N+1 y el índice pasa a la 007.
- `grep -cE '406b9af|2599bc3' MEMORY.md`: 0.

## RF-11 — Esta validación
RF-1 a RF-10 tienen arriba su orden y su resultado.

## Puertas
Sobre `d9ff5e6`, el 17-11-2026, con el stack ya levantado:
- `docker compose exec backend pytest -q`: 2 221 en verde.
- `docker compose exec backend sh -c "ruff check . && ruff format --check ."`: «All checks passed!» y 144 ficheros formateados.
- `npx vitest run`: 34 ficheros y 1 174 tests en verde.
- `npm run build`: código 0. Sigue el aviso de chunks de más de 500 kB, el de maplibre-gl, que ya está anotado para la 011.
- `npx eslint .`: código 0, sin avisos.

## Veredicto
La spec 018 se cumple: RF-1 a RF-11 tienen evidencia y las puertas están en verde. No cambia código del producto. Queda fuera de alcance lo que recoge la memoria (011, 007 y 014).
