# Tareas 017 — Imágenes de categoría y categoría «Esquí»
Spec: specs/017-category-images/spec.md · Plan: specs/017-category-images/plan.md

Máximo 10 tareas: hay 9 (la T9 lleva dos commits), en orden de dependencia:
- T1 → T2 → T3;
- T4 no depende de ninguna;
- T5 → T6 → T7;
- T8 necesita T4 y T7;
- T9 va tras todas.

Lo que no necesita las imágenes va primero (T1 a T6). Ninguna imagen de `~/RentRadar-recursos/` se abre, lee, copia ni modifica antes de la T7.

Reglas comunes de todas las tareas:
- **Puertas verdes.** Cada tarea deja en verde lo que toca. Backend, siempre dentro del contenedor: `docker compose exec backend pytest -q` y `docker compose exec backend sh -c "ruff check . && ruff format --check ."`; las tareas con migraciones, además con `pytest -q --create-db`. Frontend: `npx vitest run`, `npm run build` y `npx eslint <ficheros tocados>`.
- **Tests primero.** El test se escribe primero y falla por la razón esperada; las excepciones se dicen en su tarea.
- **Sin dependencias nuevas.** `package.json`, `package-lock.json` y `requirements` no cambian.
- **Stack.** Levantar, parar o reiniciar el stack y `npm run dev` los ejecuta el desarrollador en su terminal, en cualquier tarea, como en la T9; si hace falta, la sesión principal se lo pide.
- **Lecturas fuera del repo.** Ningún agente lee fuera de este repo, salvo sus temporales, `~/rentradar-mutaciones/` y, en la T7, `~/RentRadar-recursos/`. El código de una librería se lee en el contenedor o con Context7.
- **Commits.**
  - Antes de proponer un commit: `git diff --cached --name-only` (solo las rutas de la tarea) y `git diff --cached | grep -nE "/home/|$(id -un)"`, que no debe dar resultados.
  - Se añade con `git add -- <rutas exactas>` y se hace commit solo con el OK del desarrollador, con el diff a la vista.
  - Después del commit, `git log --oneline -3`.
- **Pruebas de mecanismo**, solo en la T4, la T5, la T6 y la T8:
  - copia de seguridad del fichero en `~/rentradar-mutaciones/017/` y su `sha256sum`;
  - mutación en el fichero de la tarea y ejecución del test, que debe fallar;
  - restauración con `cp` desde la copia y `sha256sum` igual al de antes;
  - nunca `git checkout` ni `git restore`.

  Si una mutación sobrevive, se explica o se añade el test que falta.

## Tareas

- [x] **T1. Migración de Esquí.** RF-1, RF-2, RF-3, RF-4 (sin bienes)
  - Ficheros:
    - Crea `backend/apps/categories/migrations/0003_add_ski_category.py` con `apply_ski`, `reverse_ski`, `_comparable` (NFC + `casefold`) y `SkiNameTakenError`; `dependencies = [("categories", "0002_seed_categories")]`. Se crea a mano o con `makemigrations --empty categories -n add_ski_category` en la forma de AGENTS.md (`-e DB_HOST=db-inexistente.invalid -u "$(id -u)"`), nunca contra la BD de desarrollo.
    - Crea `backend/apps/categories/tests/test_ski.py`.
    - Modifica `backend/apps/assets/tests/test_deletion.py`: añade `SEED_SIZE = 11` y `CATALOGUE_SIZE = 12`, y reescribe el test de reversión hasta antes de la semilla. Dentro del bloque, antes del `set_rollback`: `ski` no existe, quedan 11, la semilla sigue aplicada, la 0003 no y el bien sigue. Después del bloque: 12, con las dos aplicadas.
    - Modifica `backend/apps/core/tests/test_database_platform.py`: `(11, True)` pasa a `(12, True)`.
    - Modifica `docs/architecture.md`: línea 44 (la 0003 añade Esquí) y línea 87 (protección también al revertir Esquí).
  - Tests (`test_ski.py`, con las apps históricas de la 0003 y un `schema_editor` sustituto; los de `migrate` real, dentro de `transaction.atomic()` con aserciones antes del `set_rollback`):
    - `ski` con «Esquí», NFC y 5 caracteres, y pasa `save_category`;
    - RF-2: con `ski` borrada, «Nieve» o «esquí», y aplicada dos veces;
    - RF-3: otra clave con «esquí», «ESQUÍ» o «Esquí» en NFD (el test la construye con `unicodedata.normalize("NFD", …)`, sin caracteres invisibles literales) → `SkiNameTakenError` y las categorías iguales antes y después; con `ski` en «Nieve», `ski` conserva «Nieve»; con `migrate` real, la 0003 queda sin aplicar;
    - RF-4 sin bienes: `reverse_ski` borra solo `ski` y conserva una categoría ajena y las once; revertir y volver a migrar la recrea;
    - un único `DELETE`;
    - `ConnectionDoesNotExist` con un alias inexistente, en las dos funciones;
    - `RunPython` reversible, no `noop`, `atomic`, y dependencias solo de la 0002.
  - Fallan primero porque la 0003 no existe: no se importa el módulo, `ski` no existe y los recuentos dan 11.
  - Commit: `feat(categories): add ski category`
  - Hecho cuando: los tests fallan primero y luego pasan; `pytest -q --create-db`, el `pytest -q` completo, `config/tests/test_migrations.py` y ruff en verde; `test_seed.py` no cambia.
  - Puerta: espera el OK del desarrollador antes de escribir la migración.

- [x] **T2. Reversión de Esquí con un bien: rechazo y fugas.** RF-4 (con bienes)
  - Ficheros:
    - Modifica `backend/apps/assets/tests/conftest.py`: fixture `ski_category`.
    - Modifica `test_deletion.py`:
      - con un bien de Esquí, `migrate categories 0002_seed_categories` → `ProtectedError`; dentro del bloque, 12 categorías, la 0003 aplicada y el bien intacto;
      - con un bien de Esquí, hasta `0001_initial` también falla ya en la 0003 y no se borra nada.
    - Modifica `test_leaks.py`: el mismo rechazo con el bien centinela en Esquí no filtra coordenadas, ni en el error ni en el log (`assert_no_leak`). El caso existente no cambia.
    - Modifica `test_architecture.py`: `("categories", "0003_add_ski_category")` no está en el plan de `assets.0001`.
  - Tests: son guardas y no fallan primero, porque la protección es de la 005 y ya existe. Vigilan que el estado histórico de la 0003 incluya `Asset`. El detector de fugas ya tiene sus controles positivos, así que no hay prueba de mecanismo propia: la spec no la pide aquí.
  - Commit: `test(assets): reject reverting ski with an asset without leaks`
  - Hecho cuando: los tests nuevos pasan con `pytest -q --create-db`; el `pytest -q` completo y ruff en verde.

- [x] **T3. Bien de Esquí en la demostración.** RF-5
  - Ficheros:
    - Modifica `backend/apps/assets/demo.py`: la posición 23 pasa a `ski`, con el título y la descripción de D14 del plan, confirmados por el desarrollador, y con 49.90, `day`, 1000 y (39.4605, −0.3760), activa.
    - Modifica `test_demo_command.py`:
      - `SKI = "ski"`;
      - las dos aserciones con `set(CATEGORY_SLUGS)` pasan a `set(CATEGORY_SLUGS) | {SKI}`;
      - test nuevo: la 23 es `ski` con sus cifras, su radio y su ubicación sin cambiar, quedan 2 furgonetas, y la 11 y la 24 no cambian;
      - test con BD: el comando crea un bien activo de Esquí.
  - Tests: el de la posición 23 falla primero porque es `van`.
  - Commit: `feat(assets): add a ski asset to the demo data`
  - Hecho cuando: los tests fallan primero y luego pasan; `DEMO_ASSETS[:11] == CATEGORY_SLUGS` sigue valiendo; `pytest -q` y ruff en verde.

- [x] **T4. Guarda contra la incrustación.** RF-8
  - Antes de empezar: un test mínimo con `import { build } from "vite"` y `npm run build` (`tsc -b`). Si no compila sin `@types/node`, se para y se decide. Después, comprobar que la compilación de la interfaz entera funciona dentro de vitest y tarda menos de 30 s: si falla o pasa de 30 s, se para y se decide.
  - Ficheros:
    - Crea `frontend/src/panel/categoryImageBuild.test.ts`, con dos compilaciones en `beforeAll(…, 30_000)`:
      - raíz: `decodeURIComponent(new URL("../..", import.meta.url).pathname)`;
      - guardada (la interfaz entera): `build()` con `configFile` apuntando al `vite.config.ts` real, `envDir: false`, `logLevel: "silent"`, `mode: "production"`, `build.write: false`, `minify: false` y `build.assetsInlineLimit` muy alto (1 MB); entrada por defecto (`index.html`);
      - control: `configFile: false`, `envDir: false`, `publicDir: false`, `logLevel: "silent"`, `mode: "production"`, `build.write: false`, `minify: false`, `assetsInlineLimit` muy alto y `build.rolldownOptions.input` con un módulo virtual (plugin con `resolveId` y `load`) que importa `/src/assets/categories/other.svg` sin consulta. Sin `build.lib`.
  - Tests:
    - en la guardada, cada imagen de categoría (hoy las once SVG: `originalFileNames` terminados en `/assets/categories/<clave>.svg`) sale como fichero emitido y el JS referencia su `/assets/<fileName>`; no se busca `data:image/svg+xml`, porque el CSS de maplibre-gl lo lleva;
    - en el control, el JS contiene `data:image/`.

    Se escriben antes que nada: el de la guardada pasa desde el principio porque la guarda ya existe; la prueba de mecanismo demuestra que puede fallar.
  - Commit: `test(frontend): guard category images against inlining`
  - Hecho cuando: vitest, build y eslint en verde; el tiempo de las dos compilaciones queda anotado y la de la interfaz entera tarda menos de 30 s; `git status` limpio tras ejecutar el test (no escribe `dist`).
  - Prueba de mecanismo: quitar `query: "?no-inline"` de `categoryImage.ts` hace que las imágenes se incrusten con el umbral alto, dejan de emitirse como fichero y el test falla; se restaura con sha256 igual. Se repite en la T8 con las WebP.

- [x] **T5. Validador WebP: contenedor y bloques.** RF-9, RF-10
  - Ficheros:
    - Crea `frontend/src/testing/webp.ts`: `validateCategoryWebp(bytes)`, pasos 1 a 7 de la sección Lógica del plan; nunca lanza y devuelve el código de rechazo.
    - Crea `frontend/src/panel/categoryWebp.test.ts`, con constructores fabricados en el propio test (`chunk`, `webp`, `vp8x`, `vp8`, `vp8l`, `alph`) y sin ficheros hostiles versionados.
  - Tests:
    - se aceptan las dos estructuras válidas fabricadas, un fichero de 16 384 bytes y un ALPH de tamaño impar con su relleno;
    - cada caso negativo de RF-9 y RF-10 de la Estrategia de tests se rechaza con su código: PNG, JPEG y SVG; 0 bytes; truncado; datos detrás; contenedor incorrecto; 0xFFFFFFFF; 16 385 y 16 386; EXIF, `XMP `, ICCP y desconocido; animado; banderas ICC, EXIF, XMP y animación; VP8X que no mide 10; dos imágenes; ALPH con VP8L, con y sin VP8X; ALPH detrás de VP8; ALPH sin VP8X; VP8X que no va primero.

    Fallan primero porque el módulo no existe o devuelve siempre `ok`.
  - Commit: `test(frontend): validate webp container and chunks`
  - Hecho cuando: los tests fallan primero y luego pasan; vitest, build y eslint en verde.
  - Prueba de mecanismo, en `webp.ts`, una mutación cada vez:
    - admitir EXIF; admitir `XMP `; admitir ICCP; admitir un bloque desconocido;
    - admitir `[VP8X, ALPH, VP8L]`;
    - ignorar los datos detrás del contenedor;
    - admitir el tamaño 0xFFFFFFFF (aritmética con signo);
    - ignorar el relleno impar;
    - no comprobar la bandera de animación.

    Cada una hace fallar al menos un test.

- [ ] **T6. Validador WebP: dimensiones y transparencia.** RF-11, RF-12
  - Ficheros:
    - Modifica `frontend/src/testing/webp.ts`: pasos 8 a 11 de la sección Lógica del plan, con lecturas limitadas a la carga del bloque.
    - Modifica `categoryWebp.test.ts`.
  - Tests:
    - 144 × 143, 145 × 145, 288 × 288 y 1024 × 1024, en VP8 y en VP8L;
    - lienzo de VP8X distinto de la imagen y lienzo que no mide 144;
    - cabecera VP8 sin la firma `9D 01 2A` o sin fotograma clave, y VP8L sin `0x2F` o con versión distinta de 0;
    - VP8 simple; VP8X sin bandera de alfa; bandera de alfa sin ALPH; ALPH de 1 byte; VP8L sin indicador de alfa.

    Los válidos de la T5 siguen aceptándose. Los nuevos fallan primero porque hoy se aceptan.
  - Commit: `test(frontend): validate webp dimensions and transparency`
  - Hecho cuando: los tests fallan primero y luego pasan; vitest, build y eslint en verde.
  - Prueba de mecanismo, en `webp.ts`: no comprobar el lienzo de VP8X, no exigir ALPH con VP8 y no comprobar el ancho; cada una hace fallar al menos un test.

- [ ] **T7. Preparación, revisión y entrada de las doce WebP.** RF-9 a RF-15 (imágenes reales)
  - Pasos: los de «Preparación de las imágenes» del plan, en orden. Es la primera tarea que toca `~/RentRadar-recursos/`.
  - Puerta: confirma la tabla de originales; la columna «Confirmado por el desarrollador» del plan se rellena y entra en este commit.
  - Puerta: el script se escribe en `~/RentRadar-recursos/herramientas/`, se enseña al desarrollador y solo se ejecuta con su OK en ese momento, con `python3 -I` (Pillow 10.2.0 del sistema; nada se instala).
  - Puerta: si el script se para por un perfil ICC que no es sRGB, o informa de algún objeto que ocupa poco lienzo (caja del alfa en porcentaje), el desarrollador decide: regenerar en `categorias-v2/` o activar `--recortar-margen` para las doce por igual, anotado en la procedencia. Un perfil sRGB se descarta sin parar.
  - Comprobaciones:
    - `sha256sum -c` de los originales y de `fuentes.md` antes y después (trece «OK»);
    - el informe del script, transcrito con rutas `~`: versiones de Pillow y libwebp, perfil ICC de cada original, caja del alfa en porcentaje, bloques `VP8X` + `ALPH` + `VP8 `, pesos de 16 384 bytes o menos y esquinas a 0.
  - Puerta: aprobación imagen por imagen en `~/RentRadar-recursos/preparadas/hoja-revision.html` (incluida la fila de las doce a 144 px sobre fondo oscuro): RF-13 a ojo, RF-14, RF-15 y la asignación a la clave, con fecha. Las fechas se anotan aquí, bajo la T7. Si una imagen no se aprueba, la tarea se para: el desarrollador la regenera y las regeneradas van a `~/RentRadar-recursos/categorias-v2/`, con las doce completas (las que no cambian, copiadas de `categorias/`) y su propio `fuentes.md`, que él escribe diciendo cuáles se regeneraron; el script se ejecuta sobre esa carpeta, con salida en `preparadas-2/`, y `categorias/` no se toca.
  - Ficheros:
    - Crea `frontend/src/assets/categories/<clave>.webp` (las doce), copiadas con `cp -n --` y nombres exactos.
    - Modifica `categoryWebp.test.ts`: glob `../assets/categories/*.webp` con `eager` y `query: "?inline"`; hay doce, cada una empieza por `data:image/webp;base64,` y pasa `validateCategoryWebp`.

    El test se escribe antes de copiar y falla porque no hay ninguna.
  - Commit: `feat(frontend): add webp category images`
  - Hecho cuando:
    - `sha256sum -c ~/RentRadar-recursos/preparadas/SHA256SUMS` da doce «OK» en la carpeta del repo;
    - `grep -a -l -E "EXIF|XMP |ICCP|c2pa|jumb|Gemini|/home" -- *.webp` no imprime nada;
    - las doce pasan el validador;
    - siguen en verde `categoryImage.test.ts`, `categorySvg.test.ts` y el test de la guarda (las SVG conviven);
    - vitest, build y eslint en verde.

    El test «doce imágenes = doce claves» no entra aquí.

- [ ] **T8. Cambio a WebP y retirada de las SVG.** RF-6, RF-7, RF-8
  - Ficheros:
    - Modifica `frontend/src/panel/categoryImage.ts`: glob `../assets/categories/*.webp` con `?no-inline`; `slugOf` con `".webp".length`.
    - Crea `frontend/src/testing/categoryKeys.ts` (`CATEGORY_KEYS`, las doce escritas a mano), `frontend/src/testing/categoryFiles.ts` (`categoryFileProblems`) y `frontend/src/panel/categoryFiles.test.ts`.
    - Modifica `categoryImage.test.ts`: `CATEGORY_KEYS`, extensión `.webp` y «12 categorías»; las claves hostiles incluyen `snow`, `SKI`, `ski `, `ski.webp` y `../ski`.
    - Modifica `categoryImageBuild.test.ts`: lo esperado pasa a `CATEGORY_KEYS` en `.webp` (cada una sale como fichero emitido y el JS la referencia), el control importa `other.webp` sin consulta y, desde aquí, la guardada tampoco contiene `data:image/webp` en el JS ni en el CSS (los `data:image/svg+xml` de maplibre-gl se ignoran).
    - Borra con `git rm -- frontend/src/assets/categories/{barbecue,boat,canoe,caravan,ebike,kayak,motorhome,other,pool,sports-area,van}.svg frontend/src/panel/categorySvg.test.ts`, con rutas exactas: un `*.svg` también tocaría `frontend/public/icon.svg`.
    - Modifica `docs/architecture.md`, línea 125: «Imágenes WebP de las categorías».
  - Tests:
    - casos fabricados de `categoryFileProblems`: `.oculto`, `ski.png`, `Ski.webp`, `sports_area.webp`, `snow.webp`, `sub/x.webp`, `other.svg`, falta uno y exacto;
    - la carpeta real, con `import.meta.glob("../assets/categories/**/*", { query: "?url", exhaustive: true })`, contra `CATEGORY_KEYS` en los dos sentidos.

    Fallan primero mientras quedan las SVG y `categoryImage.ts` apunta a `.svg`.
  - Prueba de mecanismo del glob (D16, decidida): crear `frontend/src/assets/categories/.probe` y `frontend/src/assets/categories/sub/probe.webp`, ejecutar el test y borrarlos va en un solo comando, que borra aunque el test falle y no empieza si alguno de los dos ya existe:
    ```
    bash -c 'cd frontend && [ ! -e src/assets/categories/.probe ] && [ ! -e src/assets/categories/sub ] || exit 1; trap "rm -rf -- src/assets/categories/.probe src/assets/categories/sub" EXIT; mkdir src/assets/categories/sub && touch src/assets/categories/.probe src/assets/categories/sub/probe.webp; npx vitest run src/panel/categoryFiles.test.ts; echo "salida del test: $?"'
    ```
    La salida del test debe ser distinta de 0 y el fallo debe nombrar `.probe` y `sub/probe.webp` entre los sobrantes (el test compara `extra` con `[]`, para que el mensaje los muestre). Si falla por otra cosa, la prueba no vale; si la salida es 0, el glob es ciego. En los dos casos se para. Después, `git status --porcelain` no muestra ninguno de los dos ficheros.
  - Commit: `feat(frontend): switch category images to webp`
  - Hecho cuando:
    - vitest, build y eslint en verde, y `icon.test.ts` sigue en verde;
    - no queda ninguna `.svg` en `assets/categories`;
    - tras `npm run build`, `grep -rl "data:image/webp" frontend/dist` sale vacío y hay doce `.webp` en `frontend/dist/assets`;
    - `git diff --cached --name-only` muestra solo las rutas de la tarea.
  - Prueba de mecanismo: se repite la de la T4 con las WebP: quitar `query: "?no-inline"` hace fallar el test de la guarda, aunque las doce pesen más que el umbral por defecto.

- [ ] **T9. Validación de punta a punta y cierre.** Todos los RF
  - Puerta: «Recreación de la BD de desarrollo» del plan, pasos 0 a 6. Los pasos 1, 2 y 3 (`docker compose down`, `docker volume rm rentradar_db-data`, `docker compose up -d`) y `npm run dev` los ejecuta el desarrollador en su terminal: la sesión principal le da el comando exacto y comprueba después. Los pasos 0, 4, 5 y 6 los ejecuta la sesión principal, cada uno con la orden expresa del desarrollador en ese momento. Se transcriben el comando y la salida, con rutas `~`.
  - Navegador (con `npm run dev` en marcha en la terminal del desarrollador, `http://localhost:5173/map`), a 375 y a 1280 px, con la consola sin errores propios:
    - tarjetas de las doce categorías, la de Esquí con «Esquí» y su imagen;
    - 72 × 72 CSS, tamaño natural 144 × 144 y sin deformar;
    - fondo transparente sobre el cristal y sobre la superficie sólida (`prefersContrast: "more"`);
    - en Network, peticiones de tipo webp al propio origen y ninguna `data:`;
    - las esquinas de 8 × 8 px de las doce, leídas con `getImageData`;
    - una imagen bloqueada (D18) no muestra el icono roto y la tarjeta no se desplaza;
    - sin desbordamiento horizontal y recorrido con teclado sin cambios.
  - Puerta: el desarrollador aporta los datos de la procedencia (herramienta, fechas y versión del modelo, si la muestra) y confirma que los términos de uso permiten el uso comercial.
  - Ficheros:
    - Crea `specs/017-category-images/validation.md`:
      - cada RF con su verificación;
      - la aprobación de cada imagen con su fecha;
      - la línea de procedencia (sin prompt ni rutas absolutas);
      - las versiones de Pillow y libwebp;
      - los sha256 de los originales antes y después;
      - las pruebas de mecanismo, transcritas de los `resultado.md` de `~/rentradar-mutaciones/017/t4/`, `t5/`, `t6/` y `t8/`;
      - la recreación de la BD;
      - el punta a punta;
      - el diff vacío de los manifiestos.
    - Modifica `specs/016-visual-system/spec.md`: nota de una línea, «sustituido por la 017», en «Fuera de alcance».
  - Commits, en este orden:
    1. `docs(spec-017): validation`
    2. `docs(spec-016): note category whitelist superseded by 017`
  - Hecho cuando: todos los RF tienen su evidencia; las doce están aprobadas; pytest, ruff, vitest, build y eslint en verde; la spec pasa a «implementada». Al cerrar, MEMORY.md se actualiza, incluida la línea de la 008 en la hoja de ruta.
