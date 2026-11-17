# Tareas 018 — Limpieza antes de lanzar
Spec: specs/018-prelaunch-cleanup/spec.md · Plan: specs/018-prelaunch-cleanup/plan.md

Antes de proponer cada commit:
- `git add` por ruta exacta, nunca con `.` ni `-A`.
- `git diff --cached --name-status`: solo las rutas de la tarea.
- `git diff --cached -U0 | grep '^+' | grep -nE '/hom[e]/'` y `git diff --cached -U0 | grep '^+' | grep -niw "$(id -un)"`: sin resultados (D5).
- Diff completo a la vista y OK expreso. Un commit cada vez; después, `git log --oneline -3`.
- La casilla de cada tarea se marca en un commit propio: `docs(spec-018): mark Tn done`.

Sin push, PR ni merge. Sin migrate ni acceso a la BD de desarrollo.

- [ ] **T1. Historial real de las WebP de la v2 en la procedencia de la 017.** RF-1, RF-2, RF-3
  - Qué: `specs/017-category-images/validation.md`, apartado «Procedencia», párrafo «Las WebP de la v1 y la v2 siguen en el historial…». Se sustituye por el texto del plan («Lógica», RF-1 a RF-3).
  - Cómo se prueba:
    - `git show --name-status 406b9af` y `git show --name-status 2599bc3`.
    - `git branch -r --contains 406b9af`.
    - `git ls-tree -r --name-only 63b98cb` y `HEAD`, filtrando `.webp`.
    - El grep de metadatos de la 017 sobre las doce `git show 406b9af:<ruta>`. Si alguna da positivo, se para.
  - Commit: `docs(spec-017): correct webp history in provenance`
  - Hecho cuando: el párrafo dice solo lo que dan esas órdenes, más lo marcado «según el desarrollador», y ningún hash citado cambia.

- [ ] **T2. Sin rutas personales en lo versionado.** RF-4, RF-5
  - Qué:
    - `specs/006-public-map/validation.md`, líneas 545, 642 y 712: la copia temporal se describe sin ruta.
    - `specs/017-category-images/tasks.md:21`: el patrón de su grep pasa a `/hom[e]/` (D1).
  - Prueba de mecanismo, sin escribir ficheros: el patrón `/hom[e]/` y el `-iw` con `$(id -un)` encuentran una línea fabricada con `printf`. El `-iw` no encuentra la cuenta de GitHub de los enlaces.
  - Commit: `docs(specs): remove home paths from records`
  - Hecho cuando: `git grep -nIE '/hom[e]/'` y `git grep -nIiw "$(id -un)"` salen vacíos (código 1) en todo lo versionado, incluidos los ficheros de la 018.

- [ ] **T3. git ignora claves y volcados.** RF-6, RF-7
  - Qué: `.gitignore`, seis líneas al final: `*.pem`, `*.key`, `*.p12`, `id_rsa*`, `*.sql`, `*.dump`.
  - Cómo se prueba:
    - `git check-ignore --no-index` sobre las rutas inventadas del plan: todas ignoradas.
    - `.env.example` y `frontend/.env.example`: no ignorados (código 1).
    - `.env`, `backend/.env` y `frontend/.env.local`: ignorados.
    - `git ls-files -ci --exclude-standard` vacío.
    - `git status --short --ignored` antes y después: no desaparece ningún ignorado.
  - Commit: `chore(git): ignore key files and dumps`
  - Hecho cuando: todas las comprobaciones dan lo esperado.

- [ ] **T4. Claude Code pregunta antes de borrar contenedores con volúmenes.** RF-8
  - Qué: `.claude/settings.json`, lista `ask`: `"Bash(docker rm -v:*)"` y `"Bash(docker compose rm -v:*)"`. Nada más.
  - Cómo se prueba:
    - `python3 -I -m json.tool .claude/settings.json` sin error.
    - El diff solo cambia la lista `ask`.
    - Con tu OK en ese momento, `docker rm -v` sobre un contenedor inexistente: debe aparecer la pregunta y tú la deniegas.
  - Commit: `chore(claude): ask before removing containers with volumes`
  - Hecho cuando: el JSON carga y la pregunta aparece.

- [ ] **T5. Atribución del mapa conforme a OpenFreeMap.** RF-9
  - Qué:
    - Se repite la descarga de `https://openfreemap.org/` con curl a la carpeta temporal de la sesión; sha256 y `grep -F` de las frases del plan.
    - Se crea `specs/018-prelaunch-cleanup/validation.md` con el apartado de la atribución: cita, fecha, huella y la excepción al punto 8 de la constitución («Data from» queda en inglés, D2 = A).
    - No se toca ningún código.
  - Commit: `docs(spec-018): record map attribution check`
  - Hecho cuando: la cita registrada coincide con la página descargada y `git diff --quiet 7a19d14 HEAD -- frontend` sale con 0.

- [ ] **T6. Memoria del proyecto con lo que deja la revisión.** RF-10
  - Qué: `MEMORY.md`, con los cambios del plan («Lógica», RF-10). Incluye:
    - la hoja de ruta reordenada: la 015 antes de la 007, sin fondos con fotos y con el aviso de `user_logged_out`; las fotos de registro y entrada, en una spec pequeña justo antes de la 008, con su licencia anotada;
    - en la línea de la 014, los pendientes de licencias (OFL-1.1 de la fuente y las cuatro skills sin licencia anotada), sin resolverlos.
  - Cómo se prueba: `wc -l MEMORY.md` ≤ 50 y lectura del diff.
  - Commit: `docs(memory): note prelaunch review follow-ups`
  - Hecho cuando: están las seis notas del RF-10, la 015 va antes que la 007, las fotos justo antes de la 008, y la memoria no pasa de ~50 líneas.

- [ ] **T7. Validación y cierre.** RF-11
  - Qué:
    - `specs/018-prelaunch-cleanup/validation.md`, con RF-1 a RF-10 y la orden y el resultado de cada uno.
    - vitest, build y eslint del frontend, y pytest si el stack ya está levantado; si no lo está, te pido permiso antes de levantarlo.
    - Spec en estado «implementada».
    - Cierre de la 018 en `MEMORY.md`.
  - Commits: `docs(spec-018): validation`, `docs(spec-018): mark spec implemented` y `docs(memory): close spec 018`.
  - Hecho cuando: todos los RF tienen evidencia y las puertas están en verde.
