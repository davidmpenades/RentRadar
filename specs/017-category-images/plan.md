# Plan 017 — Imágenes de categoría y categoría «Esquí»
Spec: specs/017-category-images/spec.md (aprobada)

## Resumen
La spec toca el backend, el frontend y algo de documentación. No hay dependencias nuevas, ni cambios en la API, ni modelos nuevos.

- **Backend.** Una migración de datos propia, `categories.0003_add_ski_category`, crea `ski` con el nombre «Esquí» o se lo devuelve si ya existe. Si otra categoría ya usa ese nombre (comparado en NFC y sin distinguir mayúsculas), falla antes de escribir nada. Al revertirla se borra solo `ski`, y la protección de la 005 la rechaza si `ski` tiene bienes.
- **Demostración.** El bien de la posición 23 pasa de furgoneta a esquí y conserva sus cifras y su ubicación.
- **Frontend.**
  - Las once SVG se sustituyen por doce WebP de 144 px. `categoryImage.ts` cambia solo el patrón del glob y la extensión.
  - Tres módulos de apoyo para tests, que no llegan al bundle:
    - un validador de WebP, función pura sobre bytes;
    - una comparación pura entre los ficheros de la carpeta y las claves;
    - la lista de doce claves escrita a mano.
  - Un test de la guarda contra la incrustación compila la interfaz entera con la configuración real (`vite.config.ts`) y un umbral muy alto, y comprueba que cada imagen de categoría sale como fichero emitido; lleva su control positivo con un módulo mínimo.
- **Preparación de las imágenes.** Se hace fuera del repositorio, con el Pillow del sistema (`python3 -I`, 10.2.0). Hay una hoja de revisión HTML estática y la aprobación es imagen por imagen.
- **Orden.** Primero va todo lo que no necesita las imágenes (T1 a T6). Las imágenes entran en dos commits verdes: T7 añade las WebP y T8 cambia a WebP y retira las SVG.

## Archivos y responsabilidades
| Archivo | Crea/Modifica | Responsabilidad | RF |
|---|---|---|---|
| `backend/apps/categories/migrations/0003_add_ski_category.py` | Crea | `apply_ski` y `reverse_ski` con `RunPython`, `SkiNameTakenError` y la comparación NFC + `casefold`; depende solo de `categories.0002_seed_categories` | RF-1 a RF-4 |
| `backend/apps/categories/tests/test_ski.py` | Crea | Tests de la migración con las apps históricas de la 0003 y con `migrate` real | RF-1 a RF-4 |
| `backend/apps/assets/tests/test_deletion.py` | Modifica | Constantes `SEED_SIZE = 11` y `CATALOGUE_SIZE = 12`; el test de reversión hasta antes de la semilla se reescribe; caso nuevo con un bien de Esquí | RF-4 |
| `backend/apps/assets/tests/test_leaks.py` | Modifica | Caso nuevo: revertir la 0003 con un bien de Esquí no filtra coordenadas. El caso existente no cambia | RF-4 |
| `backend/apps/assets/tests/conftest.py` | Modifica | Fixture `ski_category`, que usan los dos ficheros anteriores | RF-4 |
| `backend/apps/assets/tests/test_architecture.py` | Modifica | La 0003 tampoco está en el plan de `assets.0001` | RF-4 |
| `backend/apps/core/tests/test_database_platform.py` | Modifica | `(11, True)` pasa a `(12, True)` tras el rollback; el `(0, False)` interior no cambia | RF-1 |
| `backend/apps/assets/demo.py` | Modifica | Posición 23: categoría `ski`, título y descripción nuevos; precio, unidad, radio, ubicación y estado iguales | RF-5 |
| `backend/apps/assets/tests/test_demo_command.py` | Modifica | Dos aserciones pasan de `set(CATEGORY_SLUGS)` a semilla más `ski`; test nuevo de la posición 23 y de los invariantes | RF-5 |
| `frontend/src/panel/categoryImageBuild.test.ts` | Crea | Guarda contra la incrustación: compilación de la interfaz entera con la configuración real y compilación de control con un módulo mínimo | RF-8 |
| `frontend/src/testing/webp.ts` | Crea | `validateCategoryWebp(bytes)`: función pura que devuelve `{ ok: true }` o `{ ok: false, reason }` y nunca lanza | RF-9 a RF-12 |
| `frontend/src/panel/categoryWebp.test.ts` | Crea | Casos fabricados en el propio test (T5 y T6) y las doce imágenes reales (T7) | RF-9 a RF-12 |
| `frontend/src/assets/categories/<clave>.webp` (12) | Crea | Las imágenes aprobadas | RF-6, RF-7, RF-13 a RF-15 |
| `frontend/src/assets/categories/*.svg` (11) | Borra | Imágenes vectoriales antiguas | Sin restos |
| `frontend/src/panel/categorySvg.test.ts` | Borra | Lista blanca aplicada a las categorías | Sin restos |
| `frontend/src/panel/categoryImage.ts` | Modifica | Glob `*.webp` con `?no-inline`; `slugOf` con `".webp".length` | RF-7, RF-8 |
| `frontend/src/panel/categoryImage.test.ts` | Modifica | Doce claves, extensión `.webp`, claves hostiles nuevas (`snow`, `SKI`, `ski `, `ski.webp`) | RF-7 |
| `frontend/src/testing/categoryKeys.ts` | Crea | `CATEGORY_KEYS`: las doce claves escritas a mano. La usan los tests de RF-6, RF-7 y RF-8 | RF-6 a RF-8 |
| `frontend/src/testing/categoryFiles.ts` | Crea | `categoryFileProblems(names, keys)`: función pura que devuelve `{ missing, extra }` | RF-6 |
| `frontend/src/panel/categoryFiles.test.ts` | Crea | Casos fabricados de la función y comparación con el contenido real de la carpeta | RF-6 |
| `docs/architecture.md` | Modifica | Línea 44: la 0003 añade Esquí. Línea 87: protección también al revertir Esquí. Línea 125: «Imágenes WebP de las categorías» | Sin restos |
| `specs/016-visual-system/spec.md` | Modifica (al cerrar) | Nota de una línea, «sustituido por la 017», en «Fuera de alcance» | Cierre |
| `specs/017-category-images/validation.md` | Crea (T9) | Evidencias, aprobaciones, procedencia y recreación de la BD | Todos |

No cambian: `AssetCard.tsx`, `svgWhitelist.ts` (`icon.test.ts` usa sus seis exportaciones), `icon.test.ts`, `test_seed.py`, `backend/openapi.json`, `schema.gen.ts`, `package.json`, `package-lock.json` ni `requirements`.

## Modelo de datos y migraciones
No hay ningún modelo nuevo. Hay una migración de datos, `categories/0003_add_ski_category.py`:

- `dependencies = [("categories", "0002_seed_categories")]`. No declara dependencia de `assets`.
- `operations = [RunPython(apply_ski, reverse_ski)]`, con `atomic` por defecto. Nunca `noop`.
- `apply_ski(apps, schema_editor)` obtiene `Category` con `apps.get_model` y escribe con `.using(schema_editor.connection.alias)`:
  1. Lee `(slug, name)` de las categorías con otra clave.
  2. Si alguna cumple `_comparable(name) == _comparable("Esquí")`, lanza `SkiNameTakenError` antes de escribir nada.
  3. Si no, hace `update_or_create(slug="ski", defaults={"name": "Esquí"})`.
- `reverse_ski`: un único `filter(slug="ski").delete()`.
- `_comparable(name)`: `unicodedata.normalize("NFC", name).casefold()`. No se confía en la restricción `Lower(name)` de la BD, que no iguala NFD con NFC y depende de `LC_CTYPE`.
- **Rechazo de la reversión con bienes.** Hoy el estado histórico de la 0003 incluye `assets.Asset`, porque en el plan completo `assets` va antes que `categories`. Por eso, al revertir con bienes salta `ProtectedError` y no `IntegrityError`. Lo vigila un test con `migrate` real (T2). Comprobado en el código de Django 5.2.18 del contenedor: `leaf_nodes()` devuelve las hojas ordenadas alfabéticamente, `_migrate_all_backwards` construye el estado previo aplicando las migraciones aplicadas del plan completo y `unapply_migration` registra la migración como desaplicada solo después de que su transacción termine bien.
- **Cómo se crea.** A mano o con `makemigrations --empty` en la forma de AGENTS.md, nunca contra la BD de desarrollo:
  ```
  docker compose run --rm --no-deps -e DB_HOST=db-inexistente.invalid -u "$(id -u)" --entrypoint "" backend python manage.py makemigrations --empty categories -n add_ski_category
  ```
- **Aprobación.** Espera el OK del desarrollador antes de escribirse.
- **SQL.** No se revisa con `sqlmigrate`, porque es `RunPython`.

## Contrato de API
No cambia. No hay operaciones nuevas ni cambiadas: `ski` es una fila más de la lista pública (`GET /api/v1/public/assets/`) y la clave no está enumerada en `openapi.json`. Los permisos de anónimo, usuario y propietario son los de la 006. No hay recursos nuevos por identificador, así que tampoco hay casos nuevos de 404 o 403.

## Lógica
- **Backend.**
  - `_comparable(name)` es pura.
  - `apply_ski` y `reverse_ski` reciben `apps` y `schema_editor`; la conexión entra como parámetro.
  - El mensaje de `SkiNameTakenError` es fijo, en castellano y sin datos de nadie.
- **`validateCategoryWebp(bytes: Uint8Array): WebpCheck`** (`src/testing/webp.ts`) usa `DataView` y comprueba los límites antes de cada lectura. Los tamaños se leen con `getUint32(…, true)` y se operan solo con aritmética, para que `0xFFFFFFFF` siga siendo positivo. Las banderas y los campos de bits de las cabeceras se leen de valores sin signo. Cada causa de rechazo tiene su código, para que cada caso fabricado falle por su razón. Pasos, en este orden:
  1. Tamaño (T5): 0 bytes → `empty`; más de 16 384 → `too_large`. Va primero porque un WebP bien formado siempre mide un número par de bytes: con 16 385 solo puede fallar por peso si el peso se mira antes que la estructura. El test incluye también uno bien formado de 16 386 bytes.
  2. Firma (T5): `RIFF` en 0-3 y `WEBP` en 8-11 → si no, `not_webp`.
  3. Contenedor (T5): `riff + 8 === length` → si no, `container_size`.
  4. Recorrido de bloques (T5): en cada vuelta deben caber 8 bytes de cabecera y `pos + 8 + size + (size % 2) ≤ length`; si no, `chunk_overflow`. Cada vuelta avanza 8 bytes o más y el recorrido termina exactamente en `length`.
  5. Bloques admitidos (T5): solo `VP8X`, `ALPH`, `VP8 ` y `VP8L` → si no, `chunk_not_allowed`.
  6. Secuencia (T5): una de `[VP8L]`, `[VP8 ]`, `[VP8X, VP8L]`, `[VP8X, VP8 ]` o `[VP8X, ALPH, VP8 ]` → si no, `chunk_order`. Cubre los dos bloques de imagen, VP8X que no va primero, ALPH sin VP8X, ALPH con VP8L y ALPH detrás de VP8.
  7. VP8X (T5): tamaño exacto 10 (`vp8x_size`); las banderas 0x20 (ICC), 0x08 (EXIF), 0x04 (XMP) y 0x02 (animación) apagadas (`vp8x_flags`).
  8. Cabecera de imagen (T6), siempre dentro de la carga del bloque → si no, `image_header`:
     - VP8: 10 bytes o más, fotograma clave (bit 0 del byte 0 a 0), `9D 01 2A` en 3-5, y ancho y alto de 14 bits en 6-7 y 8-9.
     - VP8L: 5 bytes o más, byte 0 = `0x2F`, versión (`b >>> 29`) = 0, ancho y alto de 14 bits más 1, e indicador de alfa (bit 28).
  9. Dimensiones (T6): exactamente 144 × 144 (`dimensions`).
  10. Lienzo de VP8X (T6): 24 bits más 1 en los bytes 4-6 y 7-9 de la carga; 144 × 144 e igual a la imagen (`canvas`).
  11. Transparencia (T6) → si no, `no_alpha`:
      - con VP8X, la bandera 0x10 activa y, si la imagen es VP8, un ALPH de 2 bytes o más;
      - sin VP8X, VP8L con su indicador de alfa.
- **`categoryFileProblems(names, keys)`** es pura. Recibe los nombres relativos a la carpeta y las claves, compara distinguiendo mayúsculas y devuelve `missing` (claves sin `<clave>.webp`) y `extra` (todo lo demás: otro formato, ocultos, subcarpetas, mayúsculas o nombres que no son claves). El listado real lo aporta el test.
- **`bytesOfDataUrl(url)`** vive en `categoryWebp.test.ts`. Exige el prefijo `data:image/webp;base64,` y decodifica con `atob`.

## Interfaz
No cambia nada visible salvo la imagen. La tarjeta conserva `<img width=72 height=72 alt="" loading="lazy" decoding="async" class="size-18 … rounded-2xl object-cover">`. No hay controles nuevos ni textos nuevos, el foco no cambia y el recorrido con teclado tampoco.

| Estado | Comportamiento |
|---|---|
| Carga | El hueco de 72 px está reservado por `width` y `height`; la imagen no desplaza el contenido |
| Éxito | WebP de 144 px mostrada a 72 px CSS, sin deformar, con el fondo transparente sobre el cristal o sobre la superficie sólida |
| Clave sin imagen (`snow`, vacía, `SKI`, `ski `, `__proto__`) | Imagen de «Otros» y el nombre de categoría que trae el bien |
| Falla la descarga | Hueco de 72 px vacío, sin icono de imagen rota (`alt=""`) y sin desplazamiento; la categoría se lee en el nombre |

Se verifica primero a 375 px y después a 1280 px.

## Decisiones
| Decisión | Opciones | Elegida | Qué evita | Coste |
|---|---|---|---|---|
| D1. Leer bytes y listar ficheros en vitest | A) `?inline` + `atob` para los bytes y `import.meta.glob` con `exhaustive: true`, sin `eager`, para el listado; B) `declare module "node:fs"` local; C) `@types/node` | A | Una dependencia nueva (C) y declaraciones a mano (B); `?raw` corrompe binarios | Que `?inline` dé base64 en vitest es una inferencia: se comprueba en T7 y, si falla, se pasa a B |
| D2. Mecánica de la guarda (decidida por el desarrollador) | A) `build()` de la interfaz entera con el `vite.config.ts` real y un umbral alto; B) `build()` solo del módulo que sirve las imágenes; C) buscar `?no-inline` en el código fuente; D) `assetsInlineLimit` como función en `vite.config.ts` | A, con dos compilaciones: la guardada (interfaz entera, `configFile` real, `envDir: false`, `write: false`) y la de control (`configFile: false` y un módulo mínimo que importa una imagen real sin consulta). Prueba principal: cada imagen de categoría sale como fichero emitido (`originalFileNames`) y el JS la referencia; desde la T8, además, no aparece `data:image/webp`. No se busca `data:image/svg+xml`, porque el CSS de maplibre-gl lo lleva | B deja sin cubrir un importador futuro; C no demuestra lo que sale en la compilación; D sería una segunda guarda y, al quitar solo `?no-inline`, la prueba de mecanismo ya no fallaría | Un test más lento y pesado (arrastra maplibre-gl); si en la T4 la compilación completa no funciona dentro de vitest o pasa de 30 s, se para y se decide |
| D3. Una sola guarda | `?no-inline` solo; `?no-inline` + umbral por función | `?no-inline` solo | Que la prueba de mecanismo sobreviva | Ninguno |
| D4. Herramienta de preparación | A) Pillow del sistema con `python3 -I` (10.2.0, libwebp 1.3.2); B) Pillow 11.1.0 de `~/.local`; C) ImageMagick 6; D) contenedor desechable con Pillow; E) a mano con un editor | A | B carga paquetes del usuario (sin aislamiento ante ficheros no fiables); C es legado y su ponderación por alfa no está verificada; D descarga e instala; E no es reproducible | El `_save` de 10.2 no se ha leído; lo cubren el lienzo nuevo, sin `info`, y la comprobación de bloques |
| D5. Encaje en 144 × 144 | A) contener sin deformar y centrar sobre un lienzo transparente, sin ampliar; B) `resize` directo; C) recortar antes los márgenes transparentes | A; el recorte (C) no es automático: es la opción de D22, que decide el desarrollador y se anota en la procedencia | Deformar (B) | Si un original no es cuadrado, quedan márgenes transparentes; se anota |
| D6. Codificación | A) con pérdida y alfa (VP8X + ALPH + VP8), calidad única 85 y `method=6`; B) sin pérdida (VP8L) | A, calidad 85 (confirmada por el desarrollador); solo si alguna supera 16 384 bytes se baja la calidad de las doce a la vez | El peso de B y estilos distintos entre imágenes | Artefactos leves a 2×; se juzgan en la hoja |
| D7. Quién ejecuta el script | A) se escribe fuera del repo, se enseña y se ejecuta con el OK del desarrollador en ese momento; B) lo ejecuta el desarrollador | A (decidida por el desarrollador) | Pasos manuales no reproducibles | Un OK más |
| D8. Dónde viven el script, la salida y la hoja | `~/RentRadar-recursos/herramientas/`, `~/RentRadar-recursos/preparadas/` (con la hoja dentro) y los resúmenes sha256; `/tmp`; dentro del repo ignorado | Los de `~/RentRadar-recursos/` | Que entre en el repo una herramienta de preparación (spec) y que se pierda en `/tmp` | Ninguno |
| D9. Reparto de commits de las imágenes | A) dos commits verdes: T7 (12 WebP y el test de que pasan el validador) y T8 (cambio a WebP, RF-6, RF-7, retirada de SVG); B) un solo commit | A | Un commit enorme y un build en rojo entre medias | Durante un commit conviven SVG y WebP |
| D10. Dureza del analizador | A) lo que dice la spec, aceptando como riesgo los bits reservados de VP8X, la escala de VP8, el relleno no nulo y `alpha_is_used` bajo VP8X; B) endurecer con `/sdd-change` | A (decidida por el desarrollador: las imágenes salen de nuestro propio script y los canales de pocos bits quedan como riesgo aceptado) | Exigir más de lo que dice la spec sin cambiarla | Canales de datos ocultos de pocos bits sin cubrir |
| D11. ALPH «con datos» | 1 byte o más; 2 bytes o más | 2 bytes o más (cabecera más al menos un byte) | Un ALPH de solo cabecera | Ninguno |
| D12. Tests de reversión | Aserciones tras el `set_rollback`; aserciones dentro del bloque | Dentro del bloque, antes del `set_rollback`, más el estado completo después | Que el rollback deshaga también la reversión de Esquí y el test no pruebe nada | Dos constantes |
| D13. RF-3 | Restricción `Lower(name)` de la BD; comparación en Python antes de escribir | Python, con NFC + `casefold` | Falsos negativos con NFD y la dependencia de `LC_CTYPE` | Diez líneas |
| D14. Posición 23 | Título y descripción de esquí propuestos: «Equipo de esquí de pista completo» y «Esquís con fijaciones, botas y bastones en varias tallas de adulto, revisados y listos para la temporada.» | Esos, con precio 49.90 por día y la ubicación y el radio de la furgoneta (confirmados por el desarrollador) | Datos personales o coordenadas en el texto | Ninguno |
| D15. Lista de claves | Repetida en tres tests; módulo de apoyo `src/testing/categoryKeys.ts` | Módulo | Tres listas que se separan (se extrae en la tercera repetición) | Un fichero |
| D16. Comprobar que el glob ve ocultos y subcarpetas | A) prueba temporal en `assets/categories/` (`.probe` y `sub/probe.webp`), el test debe fallar, se borran y se comprueba `git status` limpio; B) fiarse de la documentación | A, decidida por el desarrollador, tratada como una prueba de mecanismo: crear los ficheros, ejecutar el test y borrarlos van en un solo comando que borra aunque el test falle; después, `git status --porcelain` no los muestra (comando exacto en la T8) | Un test de RF-6 ciego a los ocultos | Dos ficheros temporales dentro del repo durante lo que dura un comando |
| D17. Esquinas de RF-13 | 8 × 8 px del fichero de 144; 8 × 8 px CSS (16 × 16 del fichero) | 8 × 8 px del fichero, como dice la spec | Interpretar la spec | Ninguno |
| D18. Imagen bloqueada en el navegador | Bloqueo por URL de la herramienta; cambiar el `src` de una tarjeta a una URL del mismo origen que da 404 | El bloqueo si la herramienta lo permite; si no, el cambio de `src` | Depender de una función que puede no existir | Ninguno |
| D19. Recrear la BD de desarrollo | `docker volume rm` del volumen; `down -v`; `manage.py flush`; `migrate … zero` | `docker compose down` y después `docker volume rm rentradar_db-data`, en pasos separados | Que `-v` borre más de lo nombrado, que `flush` vacíe las categorías sembradas y que `zero` choque con los bienes protegidos | Se pierde todo el contenido (sección Recreación) |
| D20. Perfil ICC de un original (decidida por el desarrollador) | A) sRGB → se descarta; otro perfil → el script se para y avisa; B) convertir siempre a sRGB; C) descartar siempre | A | Cambiar los colores sin que el desarrollador lo sepa (C) y convertir sin necesidad (B) | El script decide por la descripción del perfil, leída con `PIL.ImageCms`: si empieza por «sRGB», es sRGB; sin perfil se trata como sRGB (valor por defecto de WebP); cualquier otro, parada |
| D21. Imágenes regeneradas (decidida por el desarrollador) | A) carpeta nueva `~/RentRadar-recursos/categorias-v2/` con las doce completas (las que no cambian, copiadas de `categorias/`) y su `fuentes.md` propio, que escribe el desarrollador diciendo cuáles se regeneraron; el script se ejecuta sobre ella; B) sustituir ficheros en `categorias/` | A | Modificar `categorias/`, que la spec no deja | Una carpeta más; la tabla de originales vale igual para ella |
| D22. Objeto que ocupa poco lienzo (decidida por el desarrollador) | A) el script informa de la caja del alfa en porcentaje y, si alguno ocupa poco, el desarrollador decide entonces entre regenerar y recortar el margen transparente a las doce por igual, como paso automático anotado en la procedencia; B) regenerar siempre; C) recortar siempre | A | Imágenes diminutas a 72 px sin que nadie lo haya visto | El script lleva ya escrita la opción de recorte, apagada por defecto |
| D23. Quién ejecuta los pasos de la BD (decidida por el desarrollador) | A) el desarrollador ejecuta en su terminal los pasos 1, 2 y 3 y `npm run dev`, y la sesión principal le da el comando exacto y comprueba después; los pasos 0, 4, 5 y 6 los hace la sesión principal con su orden en ese momento; B) todo lo hace la sesión principal | A | Que la sesión principal pare o levante el stack | Un relevo manual |

## Preparación de las imágenes
Ninguna imagen se abre, copia ni modifica antes de la T7. Nada se instala: se usa el Pillow del sistema, cargado con `python3 -I`. El script, su salida y la hoja de revisión viven fuera del repositorio, y este plan describe el script sin incluir su código, porque la spec no deja entrar en el repo herramientas de preparación. Las rutas se escriben siempre con `~`.

**Lecturas fuera del repo.** Ningún agente lee fuera de este repo, salvo sus temporales, `~/rentradar-mutaciones/` y, en la T7, `~/RentRadar-recursos/`. El código de una librería se lee en el contenedor o con Context7, nunca en el entorno de otro proyecto.

1. **Confirmar la tabla** (Puerta). El desarrollador confirma o corrige la tabla de originales y claves. La columna de confirmación se rellena entonces y entra en el commit de la T7.
2. **Huella de los originales, antes de nada.**
   ```
   mkdir -p ~/RentRadar-recursos/herramientas
   cd ~/RentRadar-recursos/categorias && sha256sum -- * > ~/RentRadar-recursos/herramientas/originales.sha256
   ```
   Si dos originales tienen el mismo sha256, se para. Ya está comprobado que `furgoneta.webp` y `zonaDeportiva.webp`, que pesan lo mismo (16 448 bytes), tienen sha256 distintos (cambian 16 324 de sus 16 448 bytes); la comprobación se queda para cualquier otra pareja y para `categorias-v2/`.
3. **Script** `~/RentRadar-recursos/herramientas/prepare_category_images.py`. Se enseña antes de ejecutarlo (D7). Recibe la carpeta de entrada y la de salida como argumentos, y la correspondencia original → clave va escrita en el script según la tabla confirmada. Hace esto:
   - imprime `PIL.__version__` y `PIL.features.version("webp")`, y aborta si Pillow no es la 10.2.0;
   - aborta si en la entrada no están exactamente los doce originales de la tabla más `fuentes.md`, o si la carpeta de salida ya existe. La crea vacía. Nunca escribe en `categorias/` ni lee `fuentes.md`;
   - por cada original:
     1. `Image.open(ruta, formats=["WEBP"])`;
     2. informa del tamaño, el modo, `n_frames` y qué claves de `info` trae (`icc_profile`, `exif`, `xmp`);
     3. aborta esa imagen si `n_frames != 1`, si no tiene alfa, si mide menos de 144 px por algún lado (no se amplía) o más de 4096, o si trae un perfil ICC que no es sRGB (la descripción del perfil, leída con `PIL.ImageCms`, no empieza por «sRGB»): informa y para, y decide el desarrollador. Un perfil sRGB se descarta y se anota; sin perfil se trata como sRGB (D20);
     4. informa de la caja del alfa (`getbbox()` del canal alfa): su ancho y su alto en porcentaje del lienzo original y el área que ocupa, antes del encaje. Si algún objeto ocupa poco, decide el desarrollador (D22) entre regenerar y activar la opción `--recortar-margen`, apagada por defecto, que recorta cada imagen a su caja del alfa y la encaja con un margen fijo de 6 px; se aplica a las doce por igual y se anota en la procedencia;
     5. `convert("RGBA")`, `ImageOps.contain(…, (144, 144), Image.Resampling.LANCZOS)` y pegado centrado sobre `Image.new("RGBA", (144, 144), (0, 0, 0, 0))`. El lienzo nuevo no hereda `info`;
     6. `save(<salida>/<clave>.webp, "WEBP", quality=85, method=6)`, sin pasar metadatos y nunca `**im.info`;
   - lee cada salida con `struct` (biblioteca estándar) e imprime la longitud, `riff + 8`, y por cada bloque su FourCC, su tamaño y sus 10 primeros bytes en hexadecimal. Marca cualquier bloque que no sea VP8X, ALPH, `VP8 ` o VP8L, un peso por encima de 16 384 y un recorrido que no acabe exactamente en la longitud. La estructura esperada es `VP8X` (bandera 0x10) + `ALPH` + `VP8 `;
   - vuelve a abrir cada salida con Pillow y comprueba 144 × 144, RGBA y la opacidad máxima de los cuadrados de 8 × 8 de las cuatro esquinas. Es un aviso temprano: la verificación de RF-13 es la del navegador;
   - aborta si dos salidas son idénticas y escribe `<salida>/SHA256SUMS`;
   - genera `<salida>/hoja-revision.html` (siguiente punto).
4. **Ejecución**, con el OK del desarrollador en ese momento. Se lanza desde `~` con `-I`, sin ejecutar nada desde la carpeta de los originales:
   ```
   cd ~ && python3 -I ~/RentRadar-recursos/herramientas/prepare_category_images.py ~/RentRadar-recursos/categorias ~/RentRadar-recursos/preparadas
   ```
   Si alguna supera 16 384 bytes, se repiten las doce con una calidad menor, la misma para todas, en una carpeta nueva (`preparadas-2`).
5. **Originales intactos.**
   ```
   cd ~/RentRadar-recursos/categorias && sha256sum -c ~/RentRadar-recursos/herramientas/originales.sha256
   ```
   Deben salir trece «OK».
6. **Hoja de revisión** `~/RentRadar-recursos/preparadas/hoja-revision.html`:
   - HTML estático, sin scripts, sin red y sin recursos externos, con las imágenes por ruta relativa (`ski.webp`) y fondo `#EDF3FF`, la superficie sólida del panel de la 016;
   - cada una de las doce, rotulada con su clave, a 72 px CSS (con radio de 16 px, como en la tarjeta) y a 144 px CSS;
   - un bloque de parejas confundibles a 72 px: kayak junto a piragua (`kayak`, `canoe`), y caravana, autocaravana y furgoneta (`caravan`, `motorhome`, `van`);
   - una fila a 72 px sin rótulos, en un orden que se da al pie, para juzgar RF-15 «sin el nombre al lado»;
   - una fila con las doce a 144 px CSS sobre fondo oscuro (`#0B1220`), para ver halos que sobre `#EDF3FF` no se ven.
7. **Aprobación** (Puerta). El desarrollador abre la hoja en su navegador y aprueba cada imagen por separado: RF-13 a ojo (sin recuadro, sombra, halo ni restos), RF-14, RF-15 y su asignación a la clave, con fecha. Las fechas se anotan en `tasks.md`, junto a la T7, y pasan a la validación. Si una imagen no se aprueba, la tarea se para: el desarrollador la regenera fuera del producto, sin retocarla a mano, y las regeneradas van a `~/RentRadar-recursos/categorias-v2/` (D21), con las doce completas (las que no cambian, copiadas de `categorias/`) y su propio `fuentes.md`, que él escribe diciendo cuáles se regeneraron. El script se ejecuta sobre esa carpeta, con salida en una carpeta nueva (`preparadas-2`), y se repiten los pasos 2 a 7. `categorias/` no se toca.
8. **Copia al repositorio**, solo de las aprobadas y con nombres exactos:
   ```
   cp -n -- ~/RentRadar-recursos/preparadas/{barbecue,boat,canoe,caravan,ebike,kayak,motorhome,other,pool,ski,sports-area,van}.webp frontend/src/assets/categories/
   cd frontend/src/assets/categories && sha256sum -c ~/RentRadar-recursos/preparadas/SHA256SUMS
   grep -a -l -E "EXIF|XMP |ICCP|c2pa|jumb|Gemini|/home" -- *.webp
   ```
   Deben salir doce «OK» y el `grep` no debe imprimir nada.

**Reparto.**
- El desarrollador confirma la tabla, da el OK para escribir y ejecutar el script, decide si hay que recortar el margen (D22) o qué hacer con un perfil ICC que no es sRGB, abre la hoja, aprueba imagen por imagen, escribe el `fuentes.md` de `categorias-v2/` si hay regeneradas, aporta los datos de la procedencia y comprueba los términos de uso.
- La tarea escribe el script fuera del repo, lo ejecuta con ese OK, transcribe el informe con rutas `~`, copia y comprueba.

## Tabla de originales y claves
Correspondencia supuesta solo por el nombre del fichero: no se ha abierto ninguna imagen. Nada se copia al repositorio hasta que el desarrollador confirme esta tabla. Después, la hoja de revisión, rotulada con la clave, confirma la asignación a ojo; `kanoa` y `kayak` son la pareja confundible.

| Original (`~/RentRadar-recursos/categorias/`) | Bytes | Clave | Nombre en el catálogo | Confirmado por el desarrollador |
|---|---|---|---|---|
| `autocaravana.webp` | 18 696 | `motorhome` | Autocaravana | 12-11-2026 |
| `barbacoa.webp` | 16 170 | `barbecue` | Barbacoa | 12-11-2026 |
| `barco.webp` | 12 560 | `boat` | Barco | 12-11-2026 |
| `caravana.webp` | 16 718 | `caravan` | Caravana | 12-11-2026 |
| `ebike.webp` | 43 598 | `ebike` | Bicicleta eléctrica | 12-11-2026 |
| `furgoneta.webp` | 16 448 | `van` | Furgoneta | 12-11-2026 |
| `kanoa.webp` | 15 390 | `canoe` | Piragua | 12-11-2026 |
| `kayak.webp` | 10 190 (v2; el de la v1, de 14 168, se rechazó) | `kayak` | Kayak | 13-11-2026 |
| `otros.webp` | 8 536 | `other` | Otros | 12-11-2026 |
| `piscina.webp` | 8 908 | `pool` | Piscina | 12-11-2026 |
| `ski.webp` | 22 008 | `ski` | Esquí | 12-11-2026 |
| `zonaDeportiva.webp` | 16 448 | `sports-area` | Zona deportiva | 12-11-2026 |
| `fuentes.md` | 311 | — (no se copia ni se lee) | — | |

Si se regeneran imágenes (D21), `~/RentRadar-recursos/categorias-v2/` lleva las doce con los mismos nombres de fichero y su `fuentes.md` propio; esta tabla vale igual para ella y `categorias/` no se toca.

## Recreación de la BD de desarrollo
Va en la T9, después de todos los commits de código, y nunca la hace un implementer. Cada paso **espera la orden expresa del desarrollador en ese momento**, y nunca se hace por SQL ni por consola. Reparto (D23):
- **Los ejecuta el desarrollador en su terminal:** los pasos 1, 2 y 3 y `npm run dev`. La sesión principal le da el comando exacto y comprueba el resultado después.
- **Los ejecuta la sesión principal, con la orden del desarrollador en ese momento:** los pasos 0, 4, 5 y 6.

**Qué se pierde:** todo el contenido de la BD de desarrollo:
- las cuentas de prueba `t9-a`, `t9-b`, `t9-d`, `t9-e` y `t16-a` (todas `@example.com`), cualquier otra de validaciones anteriores y `demo@example.com` con sus 25 bienes;
- las sesiones;
- cualquier dato que haya metido el desarrollador.

El propietario de demostración y sus bienes se recrean en el paso 5; su contraseña es aleatoria y no se imprime.

| Paso | Comando | Qué se comprueba después |
|---|---|---|
| 0. Solo lectura (espera la orden expresa del desarrollador) | `docker compose ps` y `docker volume inspect rentradar_db-data --format '{{ index .Labels "com.docker.compose.project" }} {{ index .Labels "com.docker.compose.volume" }}'` | La salida es `rentradar db-data`; si no, se para |
| 1. Parar (lo ejecuta el desarrollador en su terminal) | `docker compose down` | La sesión principal comprueba con `docker compose ps` que no hay contenedores. Quita los contenedores y la red y conserva el volumen |
| 2. Borrar el volumen (lo ejecuta el desarrollador en su terminal) | `docker volume rm rentradar_db-data` | Imprime el nombre; la sesión principal comprueba con `docker volume ls --filter name=rentradar_db-data` que sale vacío. Falla sin daño si el nombre no existe o si algo lo usa |
| 3. Levantar (lo ejecuta el desarrollador en su terminal) | `docker compose up -d` y, en otra terminal, `cd frontend && npm run dev` | La sesión principal comprueba con `docker compose ps` que `db` está `healthy` (con `start_period` de 30 s) y `backend` en marcha, y que `http://localhost:5173/map` responde. El entrypoint no migra |
| 4. Migrar (espera la orden expresa del desarrollador) | `docker compose exec backend python manage.py migrate` | Aparece `Applying categories.0003_add_ski_category... OK` y termina sin error |
| 5. Demostración (espera la orden expresa del desarrollador) | `docker compose exec backend python manage.py create_demo_assets` | Mensaje exacto: «Creados 25 bienes de demostración (24 activos, 1 pausado).» |
| 6. Punta a punta, solo HTTP público de lectura (espera la orden expresa del desarrollador) | ver debajo | `24 12 ['Esquí']`; después, en el navegador, con la pestaña Network |

```
curl -s "http://localhost:8000/api/v1/public/assets/?south=39.42&west=-0.44&north=39.52&east=-0.31" | python3 -I -c 'import json, sys; r = json.load(sys.stdin)["results"]; print(len(r), len({a["category_slug"] for a in r}), sorted({a["category_name"] for a in r if a["category_slug"] == "ski"}))'
```
Es la zona del test del selector público (24 activos y el pausado fuera; área 0,013, por debajo de 6; límite de 60 peticiones por minuto). La misma petición se repite en el navegador a través del proxy de Vite (`http://localhost:5173/map`), en la pestaña Network: la respuesta trae un bien con `"category_slug":"ski"` y `"category_name":"Esquí"`.

Nota: `docker volume rm` no estaba en `ask` ni en `deny` de `.claude/settings.json`; la barrera era la orden en el chat. Ver «Cambios de entorno fuera de las tareas».

## Qué se toca y cuándo
| Tarea | `~/RentRadar-recursos/` | `frontend/src/assets/categories/` | BD de desarrollo |
|---|---|---|---|
| T1 a T6 | No se toca: ni se abre, ni se lee, ni se copia ninguna imagen | Solo las once SVG de siempre (lectura en tests) | No se toca |
| T7 | Huella sha256 de los originales; el script los lee con Pillow y escribe solo en `preparadas/` (si se regeneran imágenes, lee `categorias-v2/`, que prepara el desarrollador, y escribe en `preparadas-2/`); la hoja la abre el desarrollador | Entran las doce WebP aprobadas | No se toca |
| T8 | No se toca | Salen las once SVG; quedan las doce WebP | No se toca |
| T9 | No se toca (la procedencia la aporta el desarrollador) | No cambia | Recreación por pasos, con orden expresa |

## Blast radius
- **Backend.**
  - Código: migración nueva y `demo.py` (una entrada).
  - Tests que cambian:
    - `test_deletion.py`: el test de reversión hasta antes de la semilla pasa de «no se borra nada» a «`ski` desaparece, las once siguen, la semilla sigue aplicada y el bien sigue»;
    - `test_database_platform.py`: un literal;
    - `test_demo_command.py`: dos aserciones.
  - Tests que se añaden: `test_leaks.py`, `test_architecture.py` y `test_ski.py`.
  - Sin cambios: `test_seed.py`, `test_services.py` (cuenta diferencias, no totales) y el resto. CI aplica la 0003 al crear la BD de test.
- **Frontend.**
  - `categoryImage.ts`: glob y extensión.
  - `categoryImage.test.ts`: patrón, número y claves hostiles.
  - Se borran `categorySvg.test.ts` y las once SVG.
  - Nuevos: tres módulos en `src/testing/` y tres ficheros de test.
  - `AssetCard.tsx` no cambia. `svgWhitelist.ts` queda solo para `icon.test.ts`, que usa sus seis exportaciones.
  - CI: el job `frontend-quality` ejecuta las dos compilaciones del test de la guarda (tiempo no medido).
- **Docs**: `docs/architecture.md`, líneas 44, 87 y 125. No se tocan la 006 ni `prototypes/`. Al cerrar, una nota de una línea en la 016.
- **Contratos**: ninguno. `openapi.json` y `schema.gen.ts`, sin cambios.
- **BD de desarrollo**: recreada en la T9. Se pierde su contenido.

## Riesgos
| Riesgo | Mitigación |
|---|---|
| La reversión de la 0003 con bienes da `IntegrityError` y no `ProtectedError` si cambia el orden del plan de migraciones | Test con `migrate` real (T2); no se declara dependencia de `assets` |
| `import { build } from "vite"` no compila con `tsc -b` sin `@types/node` | Primer paso de la T4: test mínimo y `npm run build`; si falla, se para y se decide |
| `?inline` no da base64 en vitest | El test exige el prefijo `data:image/webp;base64,`; si falla, D1-B |
| El glob no ve ocultos ni subcarpetas | D16 (prueba temporal con OK) |
| Rolldown deduplica imágenes idénticas y salen menos de doce ficheros | El test recoge `originalFileNames` de todos los assets; el script aborta si hay dos salidas idénticas |
| Dos originales iguales | Comprobado: `furgoneta` y `zonaDeportiva` pesan lo mismo (16 448 bytes) pero sus sha256 son distintos (cambian 16 324 de sus 16 448 bytes). La comprobación de sha256 del paso 2 se queda para cualquier otra pareja y para `categorias-v2/`; la hoja lo revela |
| Un original sin alfa, animado, con ICC o no cuadrado | El script aborta o informa y decide el desarrollador; si no es cuadrado, márgenes transparentes |
| Cuantización del alfa: esquinas casi transparentes pero no a 0 | `alpha_quality` por defecto (100), aviso del script y medición en el navegador |
| `rounded-2xl` recorta un objeto que llega al borde | Se ve en la hoja (72 px con radio) y en el navegador |
| Un objeto pequeño en un lienzo grande se ve diminuto a 72 px | El script informa de la caja del alfa y el desarrollador decide entre regenerar y recortar el margen (D22); si no se reconoce, no se aprueba |
| La compilación de la interfaz entera con la configuración real no funciona dentro de vitest, o pasa de 30 s (arrastra maplibre-gl) | Se prueba en el primer paso de la T4; si falla o pasa de 30 s, se para y se decide |
| Falso positivo por los `data:image/svg+xml` del CSS de maplibre-gl | La prueba principal es que cada imagen sale como fichero emitido; desde la T8 solo se busca `data:image/webp` |
| Tiempo de las compilaciones del test en CI | `timeout` explícito en `beforeAll` (30 s); se mide en la T4 |
| Recrear la BD borra cuentas de prueba de otras specs | Pasos separados con orden expresa; MEMORY ya lo recoge |
| Datos ocultos en las cargas de VP8 y ALPH, bits reservados, escala o relleno | Riesgo aceptado (D10); sin metadatos por bloque |

## Estrategia de tests
| RF | Cómo se verifica |
|---|---|
| RF-1 | pytest (`test_ski.py`): `ski` existe con «Esquí» (NFC, 5 caracteres) y pasa `save_category`; la semilla no cambia (`test_migrations_leave_the_eleven_seed_categories` sigue en verde); `test_database_platform` espera 12 tras el rollback |
| RF-2 | pytest: reaplicar `apply_ski` con `ski` borrada, con `ski` llamada «Nieve» y con `ski` llamada «esquí»; aplicar dos veces deja una sola `ski` |
| RF-3 | pytest: otra clave llamada «esquí», «ESQUÍ» o «Esquí» en NFD (la «i» seguida de U+0301, que el test construye con `unicodedata.normalize("NFD", …)` para no llevar caracteres invisibles literales) → `SkiNameTakenError` y las categorías iguales antes y después; con `ski` llamada «Nieve» más el conflicto, `ski` conserva «Nieve»; con `migrate` real (revertir la 0003, crear el conflicto, migrar) falla, la 0003 queda sin aplicar y no cambia nada |
| RF-4 | pytest: sin bienes, `reverse_ski` borra solo `ski` y conserva una categoría ajena y las once; revertir y volver a migrar la recrea; con un bien de Esquí, `migrate categories 0002_seed_categories` → `ProtectedError`, 12 categorías, 0003 aplicada y el bien intacto; lo mismo hasta `0001` con un bien de Esquí; hasta `0001` con un bien en Piscina → `ski` desaparece, quedan 11, la semilla sigue aplicada y el bien sigue (dentro del bloque), y 12 tras el rollback; test de fugas sin coordenadas en el error ni en el log; `test_architecture`: la 0003 no está en el plan de `assets.0001` |
| RF-5 | pytest (`test_demo_command.py`): 25 bienes, 24 activos y el último pausado; las categorías son las de la semilla más `ski`; la 23 es `ski` con 49.90, `day`, 1000 m y (39.4605, −0.3760), activa, con título y descripción de esquí; quedan 2 furgonetas; la 11 y la 24 no cambian; el comando crea un bien activo de Esquí; los tests de 4 km, de la pareja y de fugas siguen en verde |
| RF-6 | vitest (`categoryFiles.test.ts`): casos fabricados de `categoryFileProblems` (`.oculto`, `ski.png`, `Ski.webp`, `sports_area.webp`, `snow.webp`, `sub/x.webp`, `other.svg`, falta uno, exacto) y la carpeta real (`exhaustive: true`) contra `CATEGORY_KEYS`, en los dos sentidos |
| RF-7 | vitest (`categoryImage.test.ts`): cada una de las doce da su imagen `.webp` y todas son distintas; las desconocidas y hostiles dan la de «Otros». Navegador: 72 × 72 CSS, tamaño natural 144 × 144, `alt=""` y sin deformar |
| RF-8 | vitest (`categoryImageBuild.test.ts`), con la interfaz entera, el `vite.config.ts` real y el umbral alto: cada imagen de categoría sale como fichero emitido (`originalFileNames`) y el JS la referencia por `/assets/<fileName>`; desde la T8, además, no aparece `data:image/webp` en el JS ni en el CSS; control positivo: un módulo mínimo que importa una imagen real sin consulta sale como `data:`. Compilación real: `grep -rl "data:image/webp" frontend/dist` vacío y doce `.webp` en `dist/assets`. Navegador en desarrollo: en Network, peticiones de tipo webp al propio origen y ninguna `data:` |
| RF-9 | vitest (`categoryWebp.test.ts`): PNG, JPEG y SVG con extensión `.webp`; 0 bytes; truncado (con y sin `riff` ajustado); datos detrás del contenedor; tamaño de contenedor incorrecto; bloque de 0xFFFFFFFF; 16 384 aceptado; 16 385 y 16 386 rechazados; relleno impar correcto aceptado; las doce reales pasan |
| RF-10 | vitest: EXIF, `XMP `, ICCP, bloque desconocido, animado (ANIM y ANMF), banderas ICC, EXIF, XMP y animación activas sin su bloque, VP8X de tamaño distinto de 10, dos bloques de imagen, VP8L con ALPH (con y sin VP8X), ALPH detrás de VP8, ALPH sin VP8X y VP8X que no va primero |
| RF-11 | vitest: 144 × 143, 145 × 145, 288 × 288 y 1024 × 1024 (en VP8 y en VP8L); lienzo distinto de la imagen; cabeceras VP8 y VP8L inválidas |
| RF-12 | vitest: VP8 simple; VP8X sin bandera de alfa; bandera de alfa sin ALPH; ALPH de 1 byte; VP8L sin indicador de alfa |
| RF-13 | Navegador: en las doce, opacidad de los cuadrados de 8 × 8 px del fichero en las cuatro esquinas (lienzo del mismo origen, `getImageData`), registrada en la validación. Hoja: sin recuadro, sombra, halo ni restos, aprobada por imagen. Navegador: sobre el cristal y sobre la superficie sólida (`prefersContrast: "more"`) |
| RF-14 | Hoja de revisión: aprobación por imagen con fecha |
| RF-15 | Hoja de revisión: asignación a la clave, reconocible a 72 px sin rótulo, parejas confundibles y estilo común; aprobación por imagen con fecha |
| Seguridad y privacidad | Pruebas de mecanismo de la T4, la T5, la T6 y la T8; `grep` de metadatos sobre las doce; listado de bloques; `git diff --cached` sin rutas absolutas ni nombre de usuario |
| Dependencias | `git diff` de `package.json`, `package-lock.json` y `requirements` vacío |
| Sin restos | Ninguna `.svg` en `assets/categories`; `categorySvg.test.ts` no existe; `icon.test.ts` en verde; `docs/architecture.md` actualizado |
| Accesibilidad y móvil | Navegador a 375 y 1280 px: sin desbordamiento horizontal, consola sin errores propios, recorrido con teclado sin cambios, imagen bloqueada sin icono roto y sin desplazamiento |
| Punta a punta | Recreación de la BD, paso 6, más la tarjeta de Esquí con su imagen en el navegador |

## Afirmaciones no verificadas
Comprobadas al redactar:
- la ruta pública y sus parámetros (`apps/assets/urls.py`, `zone.py` y `views.py`), y la zona del test del selector;
- `#EDF3FF` en `surfaces.css`;
- que no hay `@types/node` en `node_modules`;
- `include: ["src/**/*.test.ts"]` y `environment: "node"` en vitest;
- `types: ["vite/client"]` y `skipLibCheck` en `tsconfig.app.json`;
- el fixture `category` = `pool`;
- la posición 23 de `DEMO_ASSETS`;
- que `test_architecture.py` ya comprueba que la 0002 no está en el plan de `assets.0001`;
- `ask` de `.claude/settings.json`;
- los pasos de CI;
- en el código de Django 5.2.18 del contenedor (leído con `docker compose run --rm --no-deps --entrypoint ""`, sin BD): `unapply_migration` ejecuta cada migración en su propio `schema_editor(atomic=migration.atomic)` y registra la desaplicación solo después, así que una excepción la deja aplicada; `leaf_nodes()` devuelve las hojas ordenadas alfabéticamente; `_migrate_all_backwards` calcula el estado previo con las migraciones aplicadas del plan completo, de modo que el de la 0003 incluye `Asset`. Esto confirma lo que el informe de documentación había leído en otro proyecto y no cambia el plan.

Pendientes:
- Que `import { build } from "vite"` compila con `tsc -b` dentro de `src` (T4, primer paso).
- Que `build()` con el `vite.config.ts` real (plugins de React y Tailwind incluidos) funciona dentro del proceso de vitest con `build.write: false`, `envDir: false` y `assetsInlineLimit` alto, tarda menos de 30 s y devuelve `output` con `originalFileNames`; y que el control con `configFile: false` y un módulo virtual (`build.rolldownOptions.input`) también funciona (T4).
- Que `?no-inline` gana al `assetsInlineLimit` alto en Vite 8.3.5 (lo demuestra la prueba de mecanismo de la T4).
- Que el control con una SVG sale como `data:image/svg+xml` (T4) y con una WebP como `data:image/webp;base64` (T8).
- Que `?inline` da base64 en vitest (T7).
- Que `exhaustive: true` lista ocultos y subcarpetas (D16, T8).
- Que Pillow 10.2.0 admite `Image.open(…, formats=["WEBP"])`, `ImageOps.contain` y `save(…, quality, method)` con `alpha_quality` 100 por defecto, y que RGBA con pérdida da VP8X + ALPH + VP8 sin metadatos. Lo confirman el informe y el listado de bloques (T7).
- Las dimensiones, el modo, el alfa y el ICC de los originales, y si son cuadrados: no se han abierto.
- Que `curl` a `localhost:8000` pasa `ALLOWED_HOSTS` en desarrollo (T9).
- Que el MCP de Chrome DevTools puede bloquear una petición por URL (D18).
- Que la etiqueta del volumen es `rentradar db-data` (paso 0).
- El tiempo de las dos compilaciones del test de la guarda.
- Que la descripción del perfil ICC de un original sRGB empieza por «sRGB» (D20); si no, el script se para y decide el desarrollador.
- Qué parte del lienzo ocupa cada objeto: no se ha medido; lo informa el script (D22).

## Cambios de entorno fuera de las tareas
Cada uno va en su propio commit, con el OK del desarrollador, y no pertenece a la T1 a la T9:
- `AGENTS.md`, sección «Límites»: una línea nueva: ningún agente lee fuera de este repo, salvo sus temporales, `~/rentradar-mutaciones/` y la carpeta que la tarea nombre expresamente.
- `.claude/settings.json`: añade `Bash(docker volume rm:*)`, `Bash(docker volume prune:*)` y `Bash(docker system prune:*)` a `permissions.ask`, porque hasta ahora solo `docker compose down` pedía confirmación y la recreación de la BD borra un volumen (`docker system prune` con `--volumes` también los borra).

## Skills que aplican
`sdd` (plan, tareas, validación) y `django-drf` (migración de datos con `apps.get_model`, `.using(alias)`, `update_or_create` y un único `delete()`; tests con apps históricas, `schema_editor` sustituto, prueba del alias y tests de fugas). En el frontend no hay skill propia todavía; se aplican las notas de testing de MEMORY.md: tests sin entorno de navegador, el layout se comprueba en el navegador y TS1149 con mayúsculas.
