# Validación 017 — Imágenes de categoría y categoría «Esquí»
Spec: specs/017-category-images/spec.md · Plan: specs/017-category-images/plan.md · Tareas: specs/017-category-images/tasks.md
Rama: `feature/017-category-images`, sobre `dev` (`ae9f78b`, ancestro de HEAD).
Fecha de la validación: 13-11-2026 (puertas y recreación de la BD) y 17-11-2026 (navegador, arreglo de la imagen rota y cierre).

Registros de la validación, fuera del repositorio:
- ~/rentradar-mutaciones/017/t10/fases-a-b.md (puertas y recreación de la BD).
- ~/rentradar-mutaciones/017/t10/fase-c.md (navegador a 375 y 1280 px, con las capturas y sus sha256).

## Commits de la implementación
- T1 `583e69f` feat(categories): add ski category
- T2 `5315b34` test(assets): reject reverting ski with an asset without leaks
- T3 `354739e` feat(assets): add a ski asset to the demo data
- T4 `40a6a50` test(frontend): guard category images against inlining
- T5 `a558b2f` test(frontend): validate webp container and chunks
- T6 `4a9495f` test(frontend): validate webp dimensions and transparency
- T7 `406b9af` feat(frontend): add webp category images
- T8 `aa32271` test(frontend): disable vitest module cache, y `2599bc3` feat(frontend): switch category images to webp
- T9 `21bc6b1` docs(spec-017): switch to v3 category images (cambio de spec, plan y tareas), y `63b98cb` feat(frontend): replace category images with v3 cutouts
- T10 `53df000` docs(spec-017): note broken image fix in T10, y `566ea24` fix(frontend): hide broken category image

Las casillas de la T1 a la T9 se marcaron en commits `docs(spec-017): mark …`: T1 a T4 en `187bbf7`, T5 en `71f11d8`, T6 en `3c28284`, T7 en `390e296`, T8 en `753910d` y T9 en `fab7344`.

Cambios de spec, plan y tareas: `2c0d9e9` docs(spec-017): category images and ski category, `d428f29` docs(spec-017): plan and tasks, `02b012e` docs(spec-017): note mutation records in T9, `417425e` docs(spec-017): list test accounts lost on db recreation, `0e84a9c` docs(spec-017): add vitest cache step to T8, `21bc6b1` docs(spec-017): switch to v3 category images y `53df000` docs(spec-017): note broken image fix in T10.

La rama lleva además commits que no forman parte del contenido de la spec (memoria, reglas del repo, configuración de Claude Code y notas de la 015): `f255111` docs(memory): spec 017 approved, `7b802ae` docs(agents): limit reads outside the repo, `817b286` chore(claude): ask before deleting docker volumes, `64884b3` docs(memory): add launch legal review note, `3af5266` docs(memory): note CSP and performance follow-ups, `8f53ac3` docs(015): note missing user_logged_out signal, `b47f954` docs(memory): note vitest cache with globs y `ffd154b` docs(memory): note van category variants.

## Puertas
- pytest (BD de test, `--create-db`): 2 221 en verde, el 13-11-2026 sobre `fab7344`. El backend no ha cambiado después: `git diff --quiet fab7344 HEAD -- backend` sale con 0.
- ruff (`ruff check` y `ruff format --check`): sin errores, 144 ficheros formateados, el 13-11-2026.
- vitest (`--fsModuleCache=false`): 34 ficheros y 1 174 tests en verde, el 17-11-2026, tras el arreglo de la imagen rota (antes del arreglo, 33 y 1 172).
- build (`npm run build`): código 0, el 17-11-2026, sobre `566ea24`, con el aviso habitual del chunk de más de 500 kB.
- Tiempo de las dos compilaciones del test de la guarda (`categoryImageBuild.test.ts`), medido el 17-11-2026 con vitest (`--reporter=verbose`), en dos ejecuciones: el fichero tardó 1,16 s y 1,00 s, con la fase de tests al 86 % y al 83 % (unos 1,0 s y 0,8 s). Esa fase incluye las dos compilaciones del `beforeAll` y los cuatro tests, que suman unos 22 ms. Las dos compilaciones no se midieron por separado. El límite del plan es 30 s.
- eslint sobre los ficheros .ts y .tsx de la rama (`git diff --name-only --diff-filter=d dev...HEAD`): el 13-11-2026, los 9 .ts de entonces; el 17-11-2026, los 11 de ahora (10 .ts y `AssetCard.tsx`). Sin salida, código 0. No es eslint del proyecto entero.

## Requisitos funcionales
«Medido» es una lectura en el navegador o en la API; «leído», lo que sale de leer código o una hoja de estilos.

### RF-1. Esquí existe tras migrar
- Evidencia: `test_ski.py`: `test_migrations_leave_ski_next_to_the_eleven_seed_categories` y `test_the_ski_name_is_nfc_with_five_characters_and_passes_validation`; `test_database_platform.py` espera 12 categorías tras el rollback.
- De punta a punta: tras recrear la BD de desarrollo, `Applying categories.0003_add_ski_category... OK` y la lista pública devuelve `24 12 ['Esquí']` (medido).
- Resultado: cumple.

### RF-2. Reaplicar no duplica
- Evidencia: `test_reapplying_leaves_one_ski_with_its_name` (con `ski` borrada, «Nieve» o «esquí») y `test_applying_twice_keeps_one_ski`.
- Resultado: cumple.

### RF-3. Otro nombre igual hace fallar la migración entera
- Evidencia: `test_a_category_with_the_same_name_fails_before_writing_anything` («esquí», «ESQUÍ» y «Esquí» en NFD), `test_a_conflict_leaves_an_existing_ski_with_its_name` y `test_migrating_with_a_conflicting_name_fails_and_stays_unapplied` (con `migrate` real).
- Resultado: cumple.

### RF-4. Reversión
- Sin bienes: `test_reverting_deletes_only_ski`, `test_reverting_and_migrating_again_recreates_ski`, `test_reverting_issues_a_single_delete`, `test_ski_writes_to_the_connection_being_migrated`, `test_the_migration_depends_only_on_the_seed` y `test_ski_is_one_reversible_atomic_operation`.
- Con un bien de Esquí: `test_deletion.py` (`test_reverting_ski_with_an_asset_is_rejected_and_deletes_nothing` y `test_reverting_the_seed_with_an_asset_is_rejected_and_keeps_the_seed`), `test_leaks.py` (`test_reverting_ski_with_an_asset_does_not_leak`) y `test_architecture.py` (`test_the_asset_migration_does_not_depend_on_the_category_data_migrations`).
- Resultado: cumple.

### RF-5. Bien de Esquí en la demostración
- Evidencia: `test_demo_command.py`: `test_every_demo_category_is_one_of_the_seed_or_ski`, `test_the_ski_asset_is_the_one_that_was_the_third_van`, `test_only_two_vans_are_left_in_the_demo_data`, `test_the_pair_member_and_the_paused_asset_keep_their_place_and_data` y `test_the_command_creates_one_active_ski_asset`.
- De punta a punta: `create_demo_assets` imprime «Creados 25 bienes de demostración (24 activos, 1 pausado).» y la tarjeta «Equipo de esquí de pista completo» sale en el panel con «Esquí» (medido a 375 y 1280 px).
- Resultado: cumple.

### RF-6. Una imagen por categoría
- Evidencia: `categoryFiles.test.ts`, 12 tests: los casos fabricados de `categoryFileProblems` y la carpeta real contra `CATEGORY_KEYS` en los dos sentidos.
- Prueba del glob (D16) con `.probe` y `sub/probe.webp`: el test falla nombrando los dos y no quedan restos (acta de la T8, apartado C).
- Resultado: cumple.

### RF-7. Imagen de la categoría en la tarjeta
- Evidencia: `categoryImage.test.ts`, 31 tests: cada una de las doce claves da su imagen, las doce son distintas y las claves desconocidas y hostiles dan la de «Otros».
- Navegador (medido a 375 y 1280 px): 24 tarjetas a 72 × 72 CSS, tamaño natural 144 × 144, `alt=""`, `object-fit: cover`, 12 `src` distintos del propio origen, uno por categoría; la de Esquí, con «Esquí».
- Resultado: cumple.

### RF-8. Imágenes como ficheros del propio sitio
- Evidencia: `categoryImageBuild.test.ts`, 4 tests: cada imagen sale como fichero emitido aunque el umbral sea muy alto, el JS referencia cada fichero, no hay `data:image/webp` en el JS ni en el CSS, y el control (una imagen importada sin la guarda) sí se incrusta.
- Pruebas de mecanismo: quitar `?no-inline` hace fallar la guarda en la T4, la T8 y la T9.
- Compilación, el 17-11-2026: `grep -rl "data:image/webp" frontend/dist` sin resultados (código 1) y doce `.webp` en `frontend/dist/assets`.
- Navegador en desarrollo (medido a 375 y 1280 px): las doce piden `http://localhost:5173/src/assets/categories/<clave>.webp?no-inline`; ningún `src` ni hoja de estilos con `data:image/webp`; las únicas peticiones `data:` son dos `data:image/svg+xml` del zoom de maplibre-gl.
- Resultado: cumple.

### RF-9 a RF-12. Validación de los ficheros
- Evidencia: `categoryWebp.test.ts`, 103 tests: los casos fabricados de la spec, cada uno con su código de rechazo, y las doce imágenes reales, que pasan el validador.
- Pruebas de mecanismo: 9 mutaciones en la T5 y 5 en la T6; ninguna sobrevive.
- Resultado: cumplen.

### RF-13. Fondo transparente
- Esquinas (medido a 375 y 1280 px): las doce URLs reales, en un lienzo de 144 × 144 del mismo origen, dan alfa máximo 0 en los cuatro cuadrados de 8 × 8 y 255 en toda la imagen (control positivo); los sha256 de los bytes servidos coinciden con los del repo.
- A ojo: aprobadas las doce en la hoja de la v3 (13-11-2026). Sin halo sobre `#0B1220` (una vez, a 375 px, con una capa sintética que no depende del viewport) y sin halo ni recuadro sobre el cristal y sobre la superficie sólida, a 375 y 1280 px (17-11-2026).
- Resultado: cumple.

### RF-14 y RF-15. Contenido y reconocimiento
- Evidencia: aprobación imagen por imagen en la hoja de la v3, el 13-11-2026 (Aprobaciones).
- Resultado: cumplen.

### Caso límite: falla la descarga de una imagen
- Evidencia: `AssetCard.test.ts`, 2 tests: tras un error la imagen queda oculta y conserva los atributos `width` y `height` de 72 (el hueco se mide en el navegador); si después cambia el `src` y la imagen carga, vuelve a verse.
- Rojo: fallan 2 de 2 porque la tarjeta no tiene `onError`. sha256 del test al aprobar el rojo, 4e00b44aaf11663aea4eac8b34ccfc1a532685926c60c42abc6323cc31e0f7d9, en ~/rentradar-mutaciones/017/t10/AssetCard.test.sha256; tras el arreglo, `sha256sum -c` de esa huella sale con código 0.
- Navegador, simulación (medido a 375 y 1280 px): ver Navegador.
- Resultado: cumple desde `566ea24`.

## Navegador
Chrome DevTools MCP sobre `http://localhost:5173/map`, con la demostración recreada. Primero a 375 px (`375x812x2,mobile,touch`) y después a 1280 px (`1280x800x1`). Detalle, capturas y sha256 en ~/rentradar-mutaciones/017/t10/fase-c.md.

### Imagen que no llega (D18, simulación)
- La herramienta no bloquea peticiones por URL, así que se cambió el `src` de una tarjeta a una URL del mismo origen que falla: `/src/assets/categories/no-existe-d18.webp?no-inline` (Vite responde 200 `text/html`) y `/api/v1/no-existe-d18.webp` (404 real).
- Primera pasada a 375 px: el hueco se mantenía en 72 × 72 y nada se movía, pero Chrome pintaba el icono de imagen rota con un contorno gris aunque `alt=""`. No cumplía el caso límite.
- Arreglo (`566ea24`): `onError` pone `visibility: hidden` en la imagen y `onLoad` la devuelve a `visible`, sin estado de React.
- Tras el arreglo, a 375 y 1280 px: en los dos intentos, evento `error`, `naturalWidth` 0 y `visibility` `hidden`; la imagen, su tarjeta y la siguiente conservan su posición y su tamaño. Control positivo: con el `src` real, evento `load`, `visible` y 144 × 144. Juicio a ojo, 17-11-2026: sin icono roto ni contorno gris.

### Resto de lecturas, a 375 y 1280 px
- Consola: ningún error. Solo mensajes de depuración de Vite, el aviso de React DevTools y dos avisos del estilo de teselas de OpenFreeMap (`highway-shield-non-us` y `highway-shield-us-interstate`), que son de terceros.
- Desbordamiento: `scrollWidth ≤ clientWidth` (375 ≤ 375 y 1280 ≤ 1280), sin y con `prefersContrast: "more"`, comprobando antes con `matchMedia` y `getComputedStyle` que cada modo estaba activo (cristal: `blur(22px)`; sólida: `rgb(237, 243, 255)` y `backdrop-filter: none`).
- Teclado, con Tab real: marca, «Registrarse», mapa, tres enlaces de atribución, «Acercar», «Alejar» y la lista del panel. Ninguna imagen ni nada dentro de una tarjeta recibe el foco. Es el mismo orden que la 016, con la acción de sesión que corresponde a no tener sesión. La lista recibe el foco por ser un contenedor con desplazamiento, sin `tabindex` (leído en `ResultsPanel.tsx`).
- Respuesta pública por el proxy: 24 bienes, 12 claves y una vez `"category_slug":"ski","category_name":"Esquí"`.
- En la red, `GET /api/v1/auth/session/` aparece una vez como `net::ERR_ABORTED` antes de la buena: es el doble montaje de StrictMode en desarrollo y no ocurre en el build de producción [leído, no medido]. Es código anterior a la 017.
- El halo sobre `#0B1220` se comprobó una vez, a 375 px, con una capa sintética que no depende del viewport.

## Aprobaciones
Imágenes v3, aprobadas una a una el 13-11-2026 con una hoja con las doce a 144 y 72 px sobre claro, cristal y `#1E2230`. Cada una cumple RF-13 (a ojo), RF-14 y RF-15, y su asignación a la clave es la correcta:
- `barbecue`: 13-11-2026.
- `boat`: 13-11-2026.
- `canoe`: 13-11-2026.
- `caravan`: 13-11-2026.
- `ebike`: 13-11-2026.
- `kayak`: 13-11-2026.
- `motorhome`: 13-11-2026.
- `other`: 13-11-2026.
- `pool`: 13-11-2026.
- `ski`: 13-11-2026.
- `sports-area`: 13-11-2026.
- `van`: 13-11-2026.

En el navegador, el 17-11-2026: sin halo sobre `#0B1220` (una vez, a 375 px, con una capa sintética que no depende del viewport) y sin halo ni recuadro sobre el cristal y sobre la superficie sólida, a 375 y 1280 px.

Historial: la v1 tenía doce imágenes; once se aprobaron el 12-11-2026 y el kayak se rechazó ese día porque a 72 px se confundía con `canoe`. La v2, las once de la v1 con un kayak regenerado, aprobado el 13-11-2026, entró en la T7 y la T8, y la sustituye la v3 en la T9.

## Procedencia
### Por qué se sustituyeron la v1 y la v2
Su fondo se quitó con remove.bg en su versión gratuita, que es solo para uso no comercial.

Las WebP de la v1 y la v2 siguen en el historial de la rama (`406b9af` y `2599bc3`), sin metadatos; el producto no las sirve desde `63b98cb`. Se revisa antes del lanzamiento si hay que purgarlas del historial.

### Generación
- Herramienta: Gemini. Versión del modelo: no registrado.
- Once imágenes (todas menos `kayak`) generadas entre el 11-11-2026 y el 12-11-2026; no consta qué imagen es de qué día. `kayak`, generada el 13-11-2026; es el de la v2.
- Las doce, con fondo, se volvieron a descargar de esas mismas conversaciones el 13-11-2026. Según el desarrollador, son las mismas imágenes generadas que dieron la v1 y la v2; no se puede comprobar con huellas, porque la v1 y la v2 se guardaron sin fondo.
- Ficha de fuentes: ~/RentRadar-recursos/categorias-v3-con-fondo/fuentes.md, sha256 e6935135a0146c8f29a9f87e015553b088cc40d6994dd0db155998da8b936e58. El prompt no está en el repositorio.
- Términos de uso de Gemini sobre el uso comercial de las imágenes generadas: PENDIENTE de comprobar. Sin esa comprobación y su fecha, la spec no se cierra.

### Preparación
- Fondo quitado fuera del producto, sin servicios web de recorte, con herramientas libres ejecutadas en el entorno de trabajo de Claude, no en el portátil: `recortar_fondo.py`, modelo de segmentación ISNet (`isnet-general-use`) por medio de rembg y matting con pymatting.
- Las sombras de las imágenes originales están eliminadas.
- Excepción: en la imagen del esquí, el contorno de la cola del esquí blanco está dibujado a mano, porque el blanco es casi igual que el fondo. Es un parámetro dentro de `recortar_fondo.py` (`OVERRIDES`), no un retoque del fichero final.
- `a_webp.py` pasa los PNG a WebP de 144 × 144 px, calidad 85, `method=6`, sin metadatos. Ejecutado de nuevo en el mismo entorno, reproduce byte a byte las doce.
- Versiones, de ~/RentRadar-recursos/paquete-webp-v3/herramientas/versiones.txt (entorno del 13-11-2026), y licencias declaradas por cada proyecto, consultadas el 17-11-2026:
  - Python 3.13.18
  - rembg 2.0.87, modelo `isnet-general-use`: MIT (PyPI, `pypi.org/pypi/rembg/2.0.87/json`).
  - pesos `isnet-general-use.onnx`: 178 648 008 bytes, sha256 60920e99c45464f2ba57bee2ad08c919a52bbf852739e96947fbb4358c0d964a; descargados de las publicaciones de rembg. Apache-2.0 según el `LICENSE.md` de la rama `main` del repositorio de DIS (`github.com/xuebinqin/DIS`), que no habla de los pesos por separado.
  - pymatting 1.1.16: MIT (PyPI, `pypi.org/pypi/pymatting/1.1.16/json`).
  - onnxruntime 1.29.0: MIT (PyPI, `pypi.org/pypi/onnxruntime/1.29.0/json`).
  - numpy 2.5.3: BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0, la licencia del paquete con los componentes que incluye (PyPI, `pypi.org/pypi/numpy/2.5.3/json`).
  - scipy 1.18.1: BSD-3-Clause (PyPI, `pypi.org/pypi/scipy/1.18.1/json`: texto de la licencia con tres cláusulas y clasificador «BSD License»).
  - scikit-image 0.26.0: BSD-3-Clause (PyPI, `pypi.org/pypi/scikit-image/0.26.0/json`).
  - Pillow 12.3.0: MIT-CMU (PyPI, `pypi.org/pypi/pillow/12.3.0/json`).
  - libwebp 1.6.0: BSD-3-Clause (`COPYING` de la etiqueta `v1.6.0` en `chromium.googlesource.com/webm/libwebp`).
- Los scripts y las versiones viven en ~/RentRadar-recursos/paquete-webp-v3/herramientas/; ninguno entra en el repositorio.

### Cadena de huellas
1. Originales JPEG con fondo, 1024 × 1024: ~/RentRadar-recursos/categorias-v3-con-fondo/, huella ~/RentRadar-recursos/herramientas/originales-v3.sha256. Las entradas del recorte tienen el mismo sha256 en las doce.
   - autocaravana.jpeg 51d71cd9c8a52a77adc8538369a7b9c2408eada4f86393605abb417391b89edd
   - barbacoa.jpeg dbc07f02fc3184093ac9f577e595004cea4022cea0dfa341d5508e2eba2fb66e
   - barco.jpeg fd2555a480f40dfb866fee01884a1f6893389086e1a6c34a0bdb78cd5d139094
   - caravana.jpeg b15edeb9b748c9e8c7f490240b6ac8462fc2cf0e5056a04cc5360328425b5687
   - ebike.jpeg 3906ca56541ef9012d19a91d233f560d2898d0274166ed36a4364c4d28cb0c4e
   - furgoneta.jpeg 55c9d44d06a147a5c9e7aec8ed29dc7aebf07471331cd2695ee7471d02d56060
   - kanoa.jpeg e74f808e2abcb8f8cb84fe75d6547a29af0098349f9210d9e7ee814f8673992e
   - kayak.jpeg 0cc35f38531b7fab1752598f3da76277986aebc1f77aeab1fc77191e0501fd2f
   - otros.jpeg eed649adc05b492e16e627654e8bf8f22946bd33ec79f72bdf2512e8b9ba3100
   - piscina.jpeg b6b0660a35871c4a66863d6224b8d4bfc62a7cf5837a9acee6076b14004c437a
   - ski.jpeg 92713fb1f6b8e52ea09a4de5d4c15d0527913c368792f935350f4cf121127c28
   - zonaDeportiva.jpeg 1c3937581e2bfb83472db8a97085cefa6df5862432ebb195582b8b6900142853
2. PNG intermedios de 1024 px con alfa: ~/RentRadar-recursos/recorte-local-v3/categorias-v3/, huella ~/RentRadar-recursos/recorte-local-v3/SHA256SUMS.
   - autocaravana.png bd16cf467aa2411acfeb1837f235f9e533e2ae3859bdb1f5fae3bf1803183b2c
   - barbacoa.png b0f39873898411cbb7d42c99d8633f63f3a6c7e5a6a485c1a16bca6cd7a6d3d1
   - barco.png 8597dc5bda1a8409ed8a107a5831b966c718d3d3a01344186cbd939e07c5c48c
   - caravana.png 8604744d4be60cf5dfe7427558aaa998df62c014c7129d2d42aca7a119c9d26a
   - ebike.png e81ea29dd4cb58df42e97c3040a959230bcca7150ffc268e9625a3215ee33735
   - furgoneta.png 6c0358d4cc2f8af1a30eba522f3a2f7725186cb1220852c0a12808b526aa8aee
   - kanoa.png d119546bac99f50ecdfa0ff35a20055a412dc5bc1a1fd3575dd3b73b3e35f03b
   - kayak.png 576e02b602f18e4cbc774aea4fdaabb5f9c8ddd89200266fa4fa3669f4bf8ef4
   - otros.png 04a65a8e9cf21f70b241f4a7bbb02a971bf3178c0ecc72e3ca89fd96fe37da15
   - piscina.png f1118a953fc5897b7ddd7cf929b07def7a01a058089fb59946e6acae995f7924
   - ski.png 9dc0ace5f1fac949cf0d92618f5517512f9e4d5de07d8e0f076d83c91cca6318
   - zonaDeportiva.png 54248759e9929e8dcc26ce5bc6021e0d5a5f797970a5abdf5acd500d974c3cb5
3. WebP de 144 px: ~/RentRadar-recursos/paquete-webp-v3/preparadas-3/, huella ~/RentRadar-recursos/paquete-webp-v3/SHA256SUMS; son las doce de `frontend/src/assets/categories/`.
   - barbecue.webp 026e3074584465ded34a8ecbdd54c0afa1bc1e9da613ec59778285aa98825b9c
   - boat.webp c854d37473af85bbe094802a70969406bfc4b92794ad05cccca61e63dc023d0e
   - canoe.webp 85afce86f97fb66d45708c0d237822c3f028759c11a47314c8fa898b6f8d5ca3
   - caravan.webp 63b2b6b0a9ccd56257b842744d83751a56c115fe33c1c6f30bd5bda50603d9d7
   - ebike.webp 3624606e41aaa3ba7022ab82d7b84d63c3d80a228f168ade9d0081f30ca0bc26
   - kayak.webp 247a8440b28ddfa3406ccec4c9421f66e1ca64a309833ecee506da03ed1c503f
   - motorhome.webp 133b32659c0910cc2fccc49b191f2d565d250c6a8756c5d355f2cfcdcc59fa39
   - other.webp 2f52b58f0f6871425c13d0ca3e3ff5fa51e96e513aa12502187eb14f161dff6d
   - pool.webp 57efd9d868856bd96dab1b94d2fbf195fbbf6e7bf27669cb466cfffb4fbe7c03
   - ski.webp 44c1b45180dba7bcbdaca4d9c0dbbe71a87ebc6fa5480ae44f971c3f71473d3f
   - sports-area.webp ede2bec649f6c13f3cbde3df5bdcf96c0c01735860ab0fc729c88298c02473fc
   - van.webp 3b3be979c44f0d9260502a340b5ed8083182d2de365ed750e5f5c560572b10aa

Comprobaciones del 17-11-2026, juzgadas por su código de salida:
- `sha256sum -c ~/RentRadar-recursos/herramientas/originales-v3.sha256` en ~/RentRadar-recursos/categorias-v3-con-fondo/: código 0.
- `sha256sum -c ../SHA256SUMS` en ~/RentRadar-recursos/recorte-local-v3/categorias-v3/: código 0.
- `sha256sum -c ~/RentRadar-recursos/paquete-webp-v3/SHA256SUMS` en ~/RentRadar-recursos/paquete-webp-v3/preparadas-3/: código 0.
- `sha256sum -c ~/RentRadar-recursos/paquete-webp-v3/SHA256SUMS` en `frontend/src/assets/categories/`: código 0.

Metadatos, el 17-11-2026: `grep -a -l -E` sobre las doce `.webp` de `frontend/src/assets/categories/`, buscando `EXIF`, `XMP `, `ICCP`, `c2pa`, `jumb`, `Gemini`, rutas de usuario y el nombre de usuario: ningún fichero, código 1.

## Recreación de la BD de desarrollo
13-11-2026. Pasos 0 a 6 del plan, cada uno con su orden en ese momento. Detalle en ~/rentradar-mutaciones/017/t10/fases-a-b.md.
- Paso 0: la etiqueta del volumen es `rentradar db-data` (código 0).
- Paso 1, `docker compose down`: sin contenedores y el volumen `rentradar_db-data` sigue.
- Paso 2, `docker volume rm rentradar_db-data`: 0 volúmenes con ese nombre. Se pierden las cuentas `t9-a`, `t9-b`, `t9-d`, `t9-e`, `t16-a` y `demo@example.com` con sus 25 bienes.
- Paso 3, `docker compose up -d`: `db` healthy y `backend` arriba; `http://localhost:5173/map` responde 200. El entrypoint solo espera a la BD (`wait_for_db`) y no migra: el log del backend muestra 24 migraciones pendientes.
- Paso 4, `docker compose exec backend python manage.py migrate`: las 24, entre ellas `Applying categories.0003_add_ski_category... OK`; código 0.
- Paso 5, `docker compose exec backend python manage.py create_demo_assets`: «Creados 25 bienes de demostración (24 activos, 1 pausado).»; código 0.
- Paso 6, en dos órdenes, con el cuerpo guardado en un temporal para leer además el código HTTP: `curl -s -w "\n%{http_code}\n" "http://localhost:8000/api/v1/public/assets/?south=39.42&west=-0.44&north=39.52&east=-0.31"` (código 0, HTTP 200: `ALLOWED_HOSTS` admite `localhost:8000`) y, sobre el cuerpo, `python3 -I -c 'import json, sys; r = json.load(sys.stdin)["results"]; print(len(r), len({a["category_slug"] for a in r}), sorted({a["category_name"] for a in r if a["category_slug"] == "ski"}))'` (código 0, `24 12 ['Esquí']`).

Las actas siguientes se transcriben de ~/rentradar-mutaciones/017/tN/resultado.md tal como se escribieron en su fecha: los recuentos de entonces (por ejemplo, las once claves y los 3 tests de la T4, cuando aún no existían la imagen de Esquí ni las WebP) no son los de ahora. La T5 se mutó sobre `webp.ts` con sha256 `6febf93d…` (anterior a la T6) y la T6 sobre `064b839b…`; no se repiten.

## Prueba de mecanismo de la T4 (spec 017)
Fecha: 2026-11-12. Fichero mutado: frontend/src/panel/categoryImage.ts, en una copia del árbol en ~/rentradar-mutaciones/017/t4/frontend (node_modules enlazado al del repo). El repo no se toca.

### Mutación
Quitar la línea `  query: "?no-inline",` del glob de `categoryImage.ts`. Es la única línea que cambia.

### Línea base (sin mutar, en la copia)
`npx vitest run src/panel/categoryImageBuild.test.ts`: 1 fichero, 3 tests pasan.

### Mutada
Salida del proceso: 1. Fallan 2 de 3 tests; el de control sigue pasando.
- «cada imagen de categoría sale como fichero emitido, aunque el umbral sea muy alto»: se esperaban las once claves (barbecue … van) y se recibió `[]`.
- «el JS hace referencia a cada fichero emitido de una imagen de categoría»: `expected 0 to be greater than 0`.
Salida completa: ~/rentradar-mutaciones/017/t4/salida_mutada.txt.

### sha256 de categoryImage.ts
- Repo, antes: 4549d633545f8ebe6e36b5feec6566f3ddf9a50dc49663ff4d45f750d32a7bfd
- Repo, después: 4549d633545f8ebe6e36b5feec6566f3ddf9a50dc49663ff4d45f750d32a7bfd (igual)
- Copia, antes de mutar: 4549d633545f8ebe6e36b5feec6566f3ddf9a50dc49663ff4d45f750d32a7bfd
- Copia, mutada: 5088de841d54aa701de66cd33bbb2eff029be3db5182e8a8ae71828a932573ea

`git status --porcelain` del repo, vacío después.

### Resultado
La mutación no sobrevive: la guarda contra la incrustación falla sin `?no-inline`.
El test de control pasa con la mutación porque no importa `categoryImage.ts`; el resultado esperado era exactamente 2 de 3 en rojo, y es el que salió.

## Pruebas de mecanismo de la T5 (spec 017)
Fecha: 2026-11-12. Fichero mutado: frontend/src/testing/webp.ts, en una copia del árbol en ~/rentradar-mutaciones/017/t5/frontend (node_modules enlazado al del repo). El repo no se toca. Cada mutación parte de ~/rentradar-mutaciones/017/t5/webp.base.ts (copia del fichero sin mutar) y se aplica con un script que exige que el texto a cambiar aparezca exactamente una vez. Test: `npx vitest run src/panel/categoryWebp.test.ts --reporter=verbose`. Las salidas completas están en ~/rentradar-mutaciones/017/t5/salidas/ (base.txt, mN.txt y mN.cambio.txt).

### Línea base (copia sin mutar)
Salida 0: 1 fichero, 51 tests pasan.

### Mutaciones
Todas salen con código 1. Ninguna sobrevive.

| # | Cambio en webp.ts | Resultado | Test que la detecta |
|---|---|---|---|
| 1 | Admitir `EXIF` en ALLOWED_CHUNKS | 1 falla, 50 pasan | chunk_not_allowed: EXIF |
| 2 | Admitir `XMP ` | 1 falla, 50 pasan | chunk_not_allowed: XMP |
| 3 | Admitir `ICCP` | 1 falla, 50 pasan | chunk_not_allowed: ICCP |
| 4 | El paso 5 nunca rechaza (la condición pasa a `false`) | 7 fallan, 44 pasan | los 7 de chunk_not_allowed: EXIF, XMP, ICCP, desconocido con y sin VP8X, ANIM y ANMF |
| 5 | Añadir `["VP8X", "ALPH", "VP8L"]` a las secuencias válidas | 1 falla, 50 pasan | chunk_order: ALPH con VP8L y VP8X |
| 6 | `!== bytes.length` pasa a `> bytes.length` (ignora los datos detrás) | 2 fallan, 49 pasan | container_size: datos detrás del contenedor; contenedor que declara 2 bytes de menos |
| 7 | `getUint32` pasa a `getInt32` en el tamaño del bloque | 1 falla, 50 pasan | chunk_overflow: bloque de 0xFFFFFFFF |
| 8 | Quitar `+ (size % 2)` (ignora el relleno impar) | 19 fallan, 32 pasan | entre otros: «un ALPH de tamaño impar con su relleno» (aceptación), chunk_overflow: bloque impar sin su relleno y los casos con VP8L, que mide 5 bytes de carga |
| 9 | Quitar `0x02` de las banderas prohibidas | 1 falla, 50 pasan | vp8x_flags: bandera de animación sin su bloque (el caso de las cuatro banderas a la vez sigue en verde porque las otras tres bastan) |

Los cambios exactos están en ~/rentradar-mutaciones/017/t5/salidas/mN.cambio.txt.

### sha256 de webp.ts
- Repo, antes: 6febf93d92aac21c33b7796cbfdb4de40b593b041934eac525d9556d4a30bfe6
- Repo, después: 6febf93d92aac21c33b7796cbfdb4de40b593b041934eac525d9556d4a30bfe6 (igual)
- Copia, base: 6febf93d92aac21c33b7796cbfdb4de40b593b041934eac525d9556d4a30bfe6
- Copia, tras restaurar al terminar: 6febf93d92aac21c33b7796cbfdb4de40b593b041934eac525d9556d4a30bfe6 (igual)
- Copia mutada, primeros 16 caracteres: M1 58905108f71e0127, M2 4b3437bda34da256, M3 cbc839a2690d820b, M4 2ef14af49eb07273, M5 c79979d9e0ff167c, M6 8bc373a1f6693978, M7 1ddbcd177fed7392, M8 dbee9e02a948db5d, M9 903675b9045778ea.

### Resultado
Las 9 mutaciones de tasks.md hacen fallar al menos un test, y cada una el que se esperaba.

## Pruebas de mecanismo de la T6 (spec 017)
Fecha: 2026-11-12. Fichero mutado: frontend/src/testing/webp.ts, en una copia del árbol en ~/rentradar-mutaciones/017/t6/frontend (node_modules enlazado al del repo). El repo no se toca. Cada mutación parte de ~/rentradar-mutaciones/017/t6/webp.base.ts (copia del fichero sin mutar) y se aplica con un script que exige que el texto a cambiar aparezca exactamente una vez. Test: `npx vitest run src/panel/categoryWebp.test.ts --reporter=verbose`. Las salidas completas están en ~/rentradar-mutaciones/017/t6/salidas/ (base.txt, mN.txt y mN.cambio.txt).

Las mutaciones 1, 2 y 3 son las de tasks.md. La 4 y la 5 están añadidas fuera de tasks.md, porque vigilan la entrada hostil (cargas más cortas que la cabecera).

### Línea base (copia sin mutar)
Salida 0: 1 fichero, 90 tests pasan.

### Mutaciones
Todas salen con código 1. Ninguna sobrevive.

1. No comprobar el lienzo de VP8X: la condición `canvas.width !== header.width || canvas.height !== header.height` pasa a `false`. Fallan 7, pasan 83. Los 7 casos de `canvas` (los cinco de VP8 y los dos de VP8L), todos con `expected { ok: true } to deeply equal { ok: false, code: 'canvas' }`.
2. No exigir ALPH con VP8: `return alpha !== undefined && alpha.size >= ALPH_MIN_BYTES;` pasa a `return true;`. Fallan 3, pasan 87. `no_alpha`: bandera de alfa sin ALPH, ALPH de 1 byte y ALPH de 0 bytes.
3. No comprobar el ancho: `header.width !== IMAGE_SIZE || header.height !== IMAGE_SIZE` pasa a `header.height !== IMAGE_SIZE`. Fallan 4, pasan 86. `dimensions`: VP8 y VP8L de 143 × 144 y de 145 × 144, los casos solo de ancho (los demás de dimensions fallan también por el alto y no la detectan).
4. (Añadida) Quitar la longitud mínima de la carga de VP8: se borra la línea `if (size < VP8_HEADER_BYTES) return null;`. Fallan 2, pasan 88.
   - `image_header: VP8 de 0 bytes`: la función lanza `RangeError: Offset is outside the bounds of the DataView`.
   - `image_header: VP8 de 9 bytes`: cambia el resultado. La función lee el byte de relleno como parte de la cabecera y devuelve `{ ok: true }` en lugar de `image_header`.
5. (Añadida) Quitar la longitud mínima de la carga de VP8L: se borra `size < VP8L_HEADER_BYTES || `. Fallan 2, pasan 88. `image_header: VP8L de 0 bytes` y `image_header: VP8L de 4 bytes`: en los dos la función lanza `RangeError: Offset is outside the bounds of the DataView`.

Los cambios exactos están en ~/rentradar-mutaciones/017/t6/salidas/mN.cambio.txt.

### sha256 de webp.ts
- Repo, antes: 064b839bc32f62f5affdc912964e28159bfa8ae23523ddde6d4dd88e2e05065e
- Repo, después: 064b839bc32f62f5affdc912964e28159bfa8ae23523ddde6d4dd88e2e05065e (igual)
- Copia, base: 064b839bc32f62f5affdc912964e28159bfa8ae23523ddde6d4dd88e2e05065e
- Copia, tras restaurar al terminar: 064b839bc32f62f5affdc912964e28159bfa8ae23523ddde6d4dd88e2e05065e (igual)
- Copia mutada, primeros 16 caracteres: M1 f6b1973ab2e14358, M2 8531a3f97aaa7816, M3 f68fb2b2954c8c21, M4 8fc96913fb1d8ea1, M5 9417b6f30b4830ab.

### Resultado
Las 5 mutaciones hacen fallar al menos un test, y cada una el que se esperaba.

## Pruebas de mecanismo de la T8 (spec 017)
Fecha: 2026-11-13. Las copias del árbol viven en ~/rentradar-mutaciones/017/t8/frontend, con node_modules enlazado al del repo; el repo no se toca. Todas las ejecuciones de vitest llevan --fsModuleCache=false.
Huellas del rojo: ~/rentradar-mutaciones/017/t8/t8-rojo.sha256 (copia de la huella guardada al aprobar el rojo).

### A. Comprobación del rojo: categoryFileProblems vacía
Mutación (copia del árbol en el estado rojo): el cuerpo de categoryFileProblems pasa a `return { missing: [], extra: [] }`.
Ejecución: `npx vitest run --fsModuleCache=false src/panel/categoryFiles.test.ts`. Salida del proceso: 1 (~/rentradar-mutaciones/017/t8/salida_mutada_categoryFiles.txt).
- Fallan 9 de los 10 casos fabricados: falta una, un fichero oculto, otro formato, una SVG heredada, una clave que no existe, una subcarpeta, mayúsculas en el nombre, guion bajo en vez de guion y ninguna.
- Pasa «exacto», que es el único que espera `{ missing: [], extra: [] }`.
- Pasan también las dos pruebas de la carpeta real: con la función vacía no ven nada. Los casos fabricados son lo que protege la función.
sha256 de frontend/src/testing/categoryFiles.ts:
- Repo, antes: 88798587c282e4a1ef71c6f8336f186c419475671e33168617900bc63b014700
- Repo, después: 88798587c282e4a1ef71c6f8336f186c419475671e33168617900bc63b014700 (igual)
- Copia, antes de mutar: 88798587c282e4a1ef71c6f8336f186c419475671e33168617900bc63b014700
- Copia, mutada: 3264fcef694f7a8bf3cfa2af5aca4132fadff727429989756f72f401e0db53bc
Borrado de la copia: `unlink` del enlace a node_modules y después `rm -rf` de frontend; node_modules del repo, 165 entradas antes y 165 después.
Huellas del rojo contra el repo (sha256sum -c): salida 0.

### B. Mutación de ?no-inline en categoryImage.ts (guarda de RF-8, con las WebP)
Copia del árbol hecha desde el estado verde (sin SVG), con node_modules enlazado. Mutación: se quita la línea `  query: "?no-inline",` del glob de categoryImage.ts; es la única línea que cambia.
Línea base en la copia (sin mutar): `npx vitest run --fsModuleCache=false src/panel/categoryImageBuild.test.ts`: 4 tests, salida 0 (~/rentradar-mutaciones/017/t8/salida_base_noinline.txt).
Mutada: salida 1, fallan 3 de 4 (~/rentradar-mutaciones/017/t8/salida_mutada_noinline.txt); el control sigue pasando porque no importa categoryImage.ts.
- «cada imagen de categoría sale como fichero emitido»: se esperaban las doce .webp y se recibió [].
- «el JS hace referencia a cada fichero emitido»: se esperaban 12 y hay 0.
- «ninguna WebP queda incrustada como data: en el JS ni en el CSS»: un fragmento de JS contiene data:image/webp.
sha256 de frontend/src/panel/categoryImage.ts:
- Repo, antes: 97060941d96389e113e481f2a920fa979e5176dd68f98366900b73cd5c52f3d2
- Repo, después: 97060941d96389e113e481f2a920fa979e5176dd68f98366900b73cd5c52f3d2 (igual)
- Copia, antes de mutar: 97060941d96389e113e481f2a920fa979e5176dd68f98366900b73cd5c52f3d2
- Copia, mutada: 669b70a8d40d2f58c31e921e18c6919fb25e146c4f860fb20023e477b448d982
git status --porcelain del repo, hash antes y después: 742427c15ce2fffe675cabe826c5bccb5522776999f5f8c779e2733640cbca10 / 742427c15ce2fffe675cabe826c5bccb5522776999f5f8c779e2733640cbca10 (igual).
Borrado de la copia: unlink del enlace a node_modules y rm -rf de frontend; node_modules del repo, 165 entradas antes y 165 después.
Resultado: la mutación no sobrevive.

### C. Prueba del glob (D16), en el repo, con el comando de tasks.md
Comando de tasks.md con --fsModuleCache=false añadido a npx vitest. Se ejecuta sobre la carpeta real porque es lo que prueba; borra .probe y sub/ aunque el test falle (trap EXIT) y no empieza si ya existen.
- Antes: categoryFiles.test.ts en verde, 12 tests.
- Sonda (~/rentradar-mutaciones/017/t8/salida_sonda_glob.txt): salida del test 1. Falla «no tiene ningún fichero de más» con `expected [ '.probe', 'sub/probe.webp' ] to deeply equal []`; pasan los otros 11. El glob con exhaustive: true ve ocultos y subcarpetas.
- Después: categoryFiles.test.ts en verde, 12 tests; no queda ninguno de los dos ficheros y git status --porcelain no los muestra.

## Prueba de mecanismo de la T9 (spec 017)
Fecha: 2026-11-13. La copia del árbol vivió en ~/rentradar-mutaciones/017/t9/frontend, hecha desde el estado actual del repo (con las doce WebP de la v3 copiadas y sin commitear), con node_modules enlazado al del repo; el repo no se toca. Las dos ejecuciones de vitest llevan --fsModuleCache=false.
La copia lleva las WebP v3: sus sha256 coinciden con ~/RentRadar-recursos/paquete-webp-v3/SHA256SUMS (comprobado en la copia, ninguna línea sin coincidir).

### Las doce WebP del repo antes de la copia (~/rentradar-mutaciones/017/t9/sha_repo_antes.txt)
Hechas con `sha256sum -- *.webp` en frontend/src/assets/categories/ del repo, antes del `cp --`; salida 0, doce líneas. Son las de la T7 (commit 406b9af):
- 602932c6fc793edc5914b04a997aae6bf09884083d3439d004a7b35789df8395  barbecue.webp
- f8bc853ccd98b898eb13aa336ac3199c9d78fc625d71ab7d618f6723d9dbfedc  boat.webp
- 7bd4fcbeb35762ad0fc410172f8493910ab223ef96e6015d91bda7440577bf94  canoe.webp
- c3b3e39dc89f109f2e0a1197c1eed734f66e07574adc6a2bdc55747ef56ecc3d  caravan.webp
- d70fbe08d6e54bad4bab737c6ab122772add3085e2f3a07f989aee614ca8f177  ebike.webp
- f3fb74e75a48f9a99a0a14eb808b4d3bfe0ae345d11a016c8b2e0f698baed25e  kayak.webp
- f1f76e0a9b013365989cf537cd8729cdb9ed69b6572cf31fc52bd72c7825933d  motorhome.webp
- a12b4e23d18367b343f39a4b63e87bbf1d1338cb3a390f1487da13bf7940ac96  other.webp
- c4b1451311ed3224cdf2d0b9a840b1113ecb6836130cad862c8212d1e0f06256  pool.webp
- 9931077db81dd90b939aef3d97a21e36b7d65cee6ceeb828619562dfa78804e2  ski.webp
- 4dca7343312b16b346cd6f95f6085ce3f42214022a7a6f26e5e0e099857037c2  sports-area.webp
- d5327d7bd0d7f430135f41eff8fb32b99305465fe45c9238d18e225a03c8a7c9  van.webp

Tras el `cp --` (salida 0), `sha256sum -c ~/RentRadar-recursos/paquete-webp-v3/SHA256SUMS` en la carpeta del repo dio doce «La suma coincide» (salida 0): las del repo son ahora las de la v3.

### Mutación de ?no-inline en categoryImage.ts (guarda de RF-8, con las WebP v3)
Mutación: se quita la línea `  query: "?no-inline",` del glob de categoryImage.ts en la copia. Antes de mutar había exactamente una línea con esa cadena (la 4). Es la única línea que cambia: `diff` del repo contra la copia mutada da una sola línea, `4d3`.
Línea base en la copia (sin mutar): `npx vitest run --fsModuleCache=false src/panel/categoryImageBuild.test.ts`: 4 tests, salida 0 (~/rentradar-mutaciones/017/t9/salida_base_noinline.txt).
Mutada: salida 1, fallan 3 de 4 (~/rentradar-mutaciones/017/t9/salida_mutada_noinline.txt); el control sigue pasando porque no importa categoryImage.ts.
- «cada imagen de categoría sale como fichero emitido, aunque el umbral sea muy alto»: `expected [] to deeply equal [ 'barbecue.webp', 'boat.webp', …(10) ]`; se esperaban las doce y se recibió [].
- «el JS hace referencia a cada fichero emitido de una imagen de categoría»: `expected [] to have a length of 12 but got +0`.
- «ninguna WebP queda incrustada como data: en el JS ni en el CSS»: `expected [ Array(1) ] to deeply equal []`; la salida vuelca fragmentos de JS que contienen `data:image/webp`.
sha256 de frontend/src/panel/categoryImage.ts:
- Repo, antes: 97060941d96389e113e481f2a920fa979e5176dd68f98366900b73cd5c52f3d2
- Repo, después: 97060941d96389e113e481f2a920fa979e5176dd68f98366900b73cd5c52f3d2 (igual)
- Copia, antes de mutar: 97060941d96389e113e481f2a920fa979e5176dd68f98366900b73cd5c52f3d2
- Copia, mutada: 669b70a8d40d2f58c31e921e18c6919fb25e146c4f860fb20023e477b448d982 (el mismo que en la T8: el fichero no ha cambiado entre las dos pruebas)
git status --porcelain del repo (12 líneas, las doce .webp modificadas), hash antes y después: 2d5a1c360f494f4e5ba5c1d78f2eadaf8d2db53eeee2d629dff126bdb4557ce9 / 2d5a1c360f494f4e5ba5c1d78f2eadaf8d2db53eeee2d629dff126bdb4557ce9 (igual).
Borrado de la copia: unlink del enlace a node_modules y después rm -r de frontend; node_modules del repo, 165 entradas antes y 165 después.
Resultado: la mutación no sobrevive.

### Pesos frente al umbral de incrustación
Con la v3, bajo 4096 bytes, el umbral por defecto de Vite, hay dos WebP: pool (3 362) y other (3 410). kayak pesa 4 158 y queda por encima. Sin la guarda, esas dos se incrustarían incluso con el umbral por defecto; la prueba de arriba usa un umbral muy alto, así que no depende del peso.

## Incidencias de la preparación de imágenes
Transcripción de ~/RentRadar-recursos/herramientas/incidencias.md, con las rutas completas.

### 13-11-2026, 07:34: se sobrescribió ~/RentRadar-recursos/categorias/kayak.webp
- Qué pasó: por error, el kayak nuevo se guardó en `~/RentRadar-recursos/categorias/kayak.webp` y sobrescribió el original de la v1. El original no tiene copia y se da por perdido.
- Qué se conserva: el sha256 del original sigue en `~/RentRadar-recursos/herramientas/originales.sha256` (`f4cb0a3a1ad4ed14bf691a400595e5f08e320e2d87939366154482677c3cd958`), que se queda como registro de la v1 y no se regenera.
- Su salida, `~/RentRadar-recursos/preparadas/kayak.webp`, fue rechazada en la revisión del 12-11-2026 (a 72 px se confundía con canoe) y nunca entró en el repo.
- Cómo se corrigió: el fichero se movió con `mv` (sin sobrescribir) a `~/RentRadar-recursos/categorias-v2/kayak.webp`; el sha256 es el mismo antes y después del movimiento. Las otras doce líneas de la huella v1 (once imágenes y `fuentes.md`) siguen coincidiendo con `~/RentRadar-recursos/categorias/`.

### Comprobación del 17-11-2026
`sha256sum -c ~/RentRadar-recursos/herramientas/originales.sha256` en ~/RentRadar-recursos/categorias/, código de salida 1:
```
autocaravana.webp: La suma coincide
barbacoa.webp: La suma coincide
barco.webp: La suma coincide
caravana.webp: La suma coincide
ebike.webp: La suma coincide
fuentes.md: La suma coincide
furgoneta.webp: La suma coincide
kanoa.webp: La suma coincide
sha256sum: kayak.webp: No existe el archivo o el directorio
kayak.webp: FAILED open or read
otros.webp: La suma coincide
piscina.webp: La suma coincide
ski.webp: La suma coincide
zonaDeportiva.webp: La suma coincide
sha256sum: ATENCIÓN: no se pudo leer 1 fichero listado
```
Las doce líneas que quedan coinciden; el código 1 lo da solo el kayak perdido, como dice la incidencia.

## Manifiestos de dependencias
`git diff --exit-code --stat dev...HEAD` sobre `frontend/package.json`, `frontend/package-lock.json`, `backend/requirements*` (`requirements.in`, `requirements.txt`, `requirements-dev.in` y `requirements-dev.txt`), `backend/openapi.json` y `frontend/src/api/schema.gen.ts`: vacío, código 0.

## Sin restos
- `frontend/src/assets/categories/` tiene solo las doce `.webp`; ninguna `.svg`.
- `frontend/src/panel/categorySvg.test.ts` no existe.
- `icon.test.ts` sigue en verde (dentro de los 1 174 de vitest).
- `docs/architecture.md`: la línea 44 dice que la 0003 añade Esquí; la 87, que la protección vale también al revertir; la 125, «Imágenes WebP de las categorías».
- `AssetCard.tsx` solo cambia en `566ea24`, que añade `onError` y `onLoad`; sus clases y sus atributos `width`, `height`, `alt`, `loading` y `decoding` siguen iguales (`git diff fab7344 -- frontend/src/panel/AssetCard.tsx`).
- `test_seed.py` no cambia: `git diff --exit-code --stat dev...HEAD -- backend/apps/categories/tests/test_seed.py` vacío, código 0.
- El caso existente del test de fugas no cambia: `git diff --numstat dev...HEAD -- backend/apps/assets/tests/test_leaks.py` da 14 líneas añadidas y 0 quitadas (el caso nuevo de Esquí).
- `spec.md:250` cuenta el test de fugas de la 005 entre los que pasan a esperar doce categorías, pero ese test no cuenta categorías: no cambia, como ya dicen `plan.md` y `tasks.md`.

## Rutas absolutas y nombre de usuario
- Búsqueda de rutas de usuario y del nombre de usuario en `git diff dev...HEAD`: una sola coincidencia, en `specs/017-category-images/tasks.md`, que es el texto del propio comando de búsqueda en las reglas comunes de las tareas; no es una ruta. Ninguna en `AGENTS.md` ni en el resto de ficheros.
- La misma búsqueda en los mensajes de commit de la rama (`git log --format=%B dev..HEAD`): sin coincidencias (código 1), y ningún `Co-Authored-By`.

## Riesgos aceptados
- D10: el validador no cubre los bits reservados de VP8X, la escala de VP8, el relleno no nulo ni `alpha_is_used` bajo VP8X; son canales de pocos bits y las imágenes salen de un script propio.
- Las esquinas transparentes (RF-13) no tienen test automático: necesitaría un decodificador de WebP, que es una dependencia nueva. Se miden en el navegador.
- En pantallas de densidad 3, la imagen de 144 px se amplía a 216 píxeles físicos y pierde algo de nitidez.
- La versión del modelo de Gemini no está registrada.

## Veredicto
- Los RF-1 a RF-15 y el caso límite de la imagen que no llega se cumplen (ver Requisitos funcionales y Navegador).
- Revisión con tres revisores (calidad, seguridad y documentación) el 17-11-2026: el código y los tests, sin hallazgos bloqueantes; los dos bloqueantes de texto de este fichero (el halo sobre `#0B1220` y las licencias de Procedencia) están corregidos; los opcionales se aplicaron, se aceptaron o se aplazaron fuera de la 017.
- Pendiente para cerrar la spec: comprobar los términos de uso de Gemini sobre el uso comercial de las imágenes generadas y anotar la fecha.
