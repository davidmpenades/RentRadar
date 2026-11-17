# Plan 018 — Limpieza antes de lanzar
Spec: specs/018-prelaunch-cleanup/spec.md (aprobada)

## Resumen
Cambios de documentación y de configuración del repositorio, sin lógica de dominio, sin API, sin modelos ni migraciones. No toca el código del frontend ni del backend. Ningún commit reescribe historia: los hashes citados en specs y en la memoria siguen valiendo. Dependencias nuevas: ninguna.

## Archivos y responsabilidades
| Archivo | Crea/Modifica | Responsabilidad | RF |
|---|---|---|---|
| specs/017-category-images/validation.md | Modifica (apartado «Procedencia», párrafo de la v1 y la v2) | Historial real de las WebP de la v2 y decisión de no purgarlas | RF-1, RF-2, RF-3 |
| specs/006-public-map/validation.md | Modifica (líneas 545, 642 y 712) | Copia temporal descrita sin ruta | RF-4, RF-5 |
| specs/017-category-images/tasks.md | Modifica (línea 21) | El patrón de la orden grep deja de contener una ruta personal literal (D1) | RF-4 |
| .gitignore | Modifica (añade seis líneas al final) | Claves y volcados | RF-6, RF-7 |
| .claude/settings.json | Modifica (lista `ask`) | Preguntar antes de borrar contenedores con volúmenes | RF-8 |
| MEMORY.md | Modifica | Pendientes que salen de la revisión | RF-10 |
| specs/018-prelaunch-cleanup/validation.md | Crea | Evidencia de cada RF | RF-9, RF-11 |
| specs/018-prelaunch-cleanup/tasks.md y spec.md | Modifica | Casillas y estado | — |

## Modelo de datos y migraciones
No aplica.

## Contrato de API
No aplica: no hay endpoints nuevos ni cambiados.

## Lógica
No aplica. Los textos propuestos son estos.

**RF-1 a RF-3.** Sustituye el párrafo «Las WebP de la v1 y la v2 siguen en el historial de la rama…» de `specs/017-category-images/validation.md`. La frase anterior, sobre remove.bg, no cambia. Texto propuesto:

> En git solo entró la v2: las doce WebP de `frontend/src/assets/categories/` las añade `406b9af` (`git show --name-status 406b9af`). Según el desarrollador, once son las de la v1 y el kayak es el regenerado; git no guarda ninguna versión anterior con la que compararlas. `2599bc3` no añade ninguna WebP: borra los once SVG y cambia el código y los tests (`git show --name-status 2599bc3`). `63b98cb` sustituye las doce por las de la v3; desde ese commit el árbol no tiene otras WebP, así que el producto no sirve las de la v2 (`git ls-tree -r`).
>
> Las WebP de la v2 siguen, sin metadatos, en el historial publicado en GitHub (alcanzables desde `origin/dev`: `git branch -r --contains 406b9af`). Por decisión del desarrollador del 17-11-2026 no se purgan del historial; queda documentado aquí.

«Sin metadatos» se comprueba con git en la T1 (`git show 406b9af:<ruta>` sobre las doce, con el mismo grep de metadatos de la 017). Si alguna da positivo, se quita la afirmación y se para.

**RF-5.** En las tres líneas, la ruta pasa a «una carpeta temporal de la sesión de trabajo, fuera del repositorio (`t9-mutations/` o `t10-mutations/`)». El resto de la frase no cambia.

**RF-6 y RF-7.** Se añaden al final de `.gitignore`, sin comentario y después de `!.env.example`: `*.pem`, `*.key`, `*.p12`, `id_rsa*`, `*.sql` y `*.dump`. Ninguno coincide con `.env.example`, así que la excepción sigue valiendo.

**RF-8.** La lista `ask` gana dos entradas, con la misma sintaxis que las que ya tiene: `"Bash(docker rm -v:*)"` y `"Bash(docker compose rm -v:*)"`. `deny`, el resto de `ask` y el formato del fichero no cambian.

**RF-9.** Página oficial: `https://openfreemap.org/`, sección «Attribution», descargada con curl el 17-11-2026 a las 16:05 UTC (HTTP 200, sha256 `3408380cd0ce061b06441e5a8c5cdf4ee67d618907e71edee74f23efdd616934`). Texto literal, comprobado con `grep -F`:
- «Attribution is required. If you are using MapLibre, they are automatically added, you have nothing to do.»
- «If you are using alternative clients, or if you are using this in printed media or video, you must add the following attribution:»
- `<a href="https://openfreemap.org" target="_blank">OpenFreeMap</a> <a href="https://www.openmaptiles.org/" target="_blank">© OpenMapTiles</a> Data from <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a>`
- «You do not need to display the OpenFreeMap part, but it is nice if you do.»

Los términos del servicio (`/tos/`) y la guía de inicio (`/quick_start/`) no mencionan la atribución (grep sin resultados). La T5 repite la descarga y registra la cita con su fecha y su huella.

El texto de `MAP_ATTRIBUTION_HTML` (`frontend/src/map/style.ts`) no cambia. La validación de la 018 registra la excepción al punto 8 de la constitución: «Data from» queda en inglés porque es parte del texto que el proveedor da como atribución.

**RF-10.** Cambios en `MEMORY.md`, que sigue con 50 líneas como máximo; se reescriben líneas existentes, sin añadir nuevas:
- «Estado actual»: la 017 pasa a la lista de mergeadas con «(PR #10)»; la spec activa es la 018.
- «Hoja de ruta»: sale «revisión antes de lanzar (legal, rendimiento y secretos) →». Queda: 018 limpieza antes de lanzar → 015 entrada → 007 interacción → /sdd-change de la 005 → 010 → 013 → 014 → fotos de registro y entrada → 008 portada y búsqueda → 011 → 012 → pagos.
  - 015 entrada: notas en `specs/015-login/notes.md`, con el aviso pendiente de `user_logged_out`; sin fondos con fotos.
  - Fotos de registro y entrada: spec pequeña justo antes de la 008, porque la portada también necesitará fotos y la procedencia se hace una sola vez; con la licencia de cada foto anotada.
- Línea de la 014: pendientes de licencias, sin resolverlos: el aviso de la licencia OFL-1.1 de la fuente Bricolage Grotesque, y cuatro skills versionadas sin licencia anotada (grill-me, grilling, systematic-debugging y web-design-guidelines).
- Línea de la 011: «No hay servidor de producción: Compose usa runserver y gunicorn no está en requirements».
- Línea de la 007 (D4): «La lista pública filtra por ST_X y ST_Y sobre un cast a geometry y no puede usar el GiST de public_location; antes de cambiarla, medir con EXPLAIN en la BD de test con decenas de miles de filas sintéticas, sin romper los tests de fugas de la ubicación pública».
- «Pendientes sueltos»:
  - salen «añadir docker rm -v y docker compose rm -v a ask» (hecho en la T4), la duda de purgar las WebP (decidida y documentada en la validación de la 017) y «comprobar índice espacial y consultas N+1 de la lista pública» (la revisión no encontró N+1; el índice pasa a la 007);
  - se conservan la revisión legal (términos, descarga de datos, DSA, edad mínima, contratos), la duda del C2PA y el resto de pendientes de rendimiento de la 011.

## Interfaz
Sin cambios.

## Decisiones
| Decisión | Opciones | Elegida | Qué evita | Coste |
|---|---|---|---|---|
| D1. La orden grep que contiene una ruta personal literal (`specs/017-category-images/tasks.md:21`, y la que usarían los documentos de la 018) | A) escribir el patrón como `/hom[e]/`, que encuentra lo mismo pero no coincide consigo mismo; B) excluir esos ficheros de la comprobación; C) buscar solo la ruta con el usuario y no cualquier ruta personal | A | B deja un hueco permanente en la comprobación; C cambia el criterio que pediste | Toca una línea de la 017 fuera de las tres de la 006 |
| D2. Atribución del mapa | A) se conserva el texto literal del proveedor, en inglés, como excepción registrada al punto 8 de la constitución; B) se traduce «Data from» por «Datos de», con test | A | B se aparta del texto que la página da como «the following attribution» | A deja tres palabras en inglés en la interfaz. El test `style.test.ts:122` ya fija el texto, así que nadie lo traduce sin ver el motivo |
| D3. Dónde se anota la decisión de D2 | A) solo en la validación de la 018; B) además, un comentario en `style.ts` | A | B toca código para algo que el test ya protege | Para saber por qué está en inglés hay que buscar en specs/ |
| D4. Dónde va la nota de la consulta de la lista pública | A) en la 007; B) en la 011 | A | La 007 es la siguiente que toca esa consulta (filtro por bien, recuentos por celda) | Ninguno |
| D5. Comprobación de lo preparado antes de cada commit | A) grep solo sobre las líneas añadidas (`^+`); B) sobre todo el diff | A | En la T2 las líneas borradas contienen la ruta y B daría siempre positivo | Ninguno |

## Blast radius
- `.gitignore`: hoy no hay ningún fichero versionado que coincida con los seis patrones (comprobado con `git ls-files`). Los ficheros nuevos con esas extensiones dejarán de aparecer en `git status`; un futuro `.sql` que haya que versionar necesitaría `git add -f` o una excepción.
- `.claude/settings.json`: solo añade preguntas. Las órdenes `docker compose rm` sin `-v` y `docker rm` sin `-v` siguen sin preguntar.
- `style.test.ts:122` y `loadStyle.test.ts:70` fijan el texto de la atribución y no cambian.
- Las specs 006 y 017 están cerradas: el cambio es solo de texto y no toca hashes ni evidencias medibles.

## Riesgos
| Riesgo | Mitigación |
|---|---|
| El patrón `/hom[e]/` no encuentra lo que debe | Prueba de mecanismo en la T2: el patrón se aplica con `printf … \| grep` a una línea fabricada con una ruta personal y debe encontrarla; no se escribe ningún fichero |
| La regla nueva de `ask` no se activa (sintaxis o recarga de la configuración) | En la T4, con tu OK en ese momento, se intenta `docker rm -v` sobre un contenedor inexistente: debe aparecer la pregunta, que tú deniegas. Si no aparece, la orden solo falla con «No such container» |
| La página de OpenFreeMap cambia | Se registran la cita, la fecha y el sha256 |
| `MEMORY.md` pasa de ~50 líneas | Se reescriben líneas existentes; `wc -l` en la T6 |

## Estrategia de tests
| RF | Cómo se verifica |
|---|---|
| RF-1 | `git show --name-status 406b9af` (12 `A` de `.webp`) y `git show --name-status 2599bc3` (ningún `.webp`), registrados en la validación |
| RF-2 | `git branch -r --contains 406b9af` incluye `origin/dev`; `git ls-tree -r --name-only 63b98cb` y `HEAD` sin otras `.webp` |
| RF-3 | Lectura del párrafo: cada afirmación no comprobable con git lleva «según el desarrollador» |
| RF-4 | `git grep -nIE '/hom[e]/'` y `git grep -nIiw "$(id -un)"` vacíos (código 1), más la prueba de mecanismo del patrón |
| RF-5 | Lectura de las tres líneas |
| RF-6 | `git check-ignore --no-index` sobre rutas inventadas, en la raíz y en subcarpetas (`a.pem`, `backend/b.key`, `x/c.p12`, `id_rsa`, `id_rsa.pub`, `d/e.sql`, `f.dump`): todas ignoradas. `git ls-files -ci --exclude-standard` vacío |
| RF-7 | `git check-ignore -q --no-index .env.example` y `… frontend/.env.example`: código 1 (no ignorado); `.env`, `backend/.env` y `frontend/.env.local` siguen ignorados |
| RF-8 | `python3 -I -m json.tool .claude/settings.json` sin error; el diff solo cambia `ask`; la prueba con un contenedor inexistente |
| RF-9 | Descarga con curl, sha256 y `grep -F` de las frases citadas; `git diff --quiet 7a19d14 HEAD -- frontend` sale con 0 |
| RF-10 | `wc -l MEMORY.md` ≤ 50 y lectura del diff; en la hoja de ruta, la 015 va antes que la 007 |
| RF-11 | La validación cubre RF-1 a RF-10 |

## Afirmaciones no verificadas
- Que Claude Code aplica la regla nueva de `ask` sin reiniciar la sesión (se comprueba en la T4).
- Que la sintaxis `Bash(<orden>:*)` coincide con `docker rm -v <nombre>`: es la que ya usan las entradas existentes, pero no se ha probado con esta orden.

## Skills que aplican
sdd. Ninguna del stack.
