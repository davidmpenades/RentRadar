# Tareas 008 — Búsqueda y filtros por categoría en el mapa
Spec: specs/008-search-filters/spec.md (aprobada) · Plan: specs/008-search-filters/plan.md (aprobado, 24-11-2026)
Reparto: exactamente T1 a T10 de «Reparto estimado en tareas» del plan. El índice GiST, si la medición lo pide, queda fuera de estas tareas.

## Reglas comunes
- Una tarea cada vez. Al terminarla, parar y esperar aprobación antes de la siguiente. Antes de cada commit, enseñar el diff.
- Los tests se escriben primero y deben fallar por la razón esperada. Ningún commit con pytest, vitest, build o eslint en rojo.
- Parar y pedir OK antes de escribir en las tareas que tocan migraciones, seguridad, privacidad o contrato: T2, T3, T4, T5, T8 y T10. En T1, T6, T7 y T9 se implementa sin esperar y se enseña el diff antes del commit.
- Commits de una tarea, en este orden y solo los que apliquen:
  1. refactor o traslado, sin cambiar comportamiento ni ids de tests;
  2. feat (o test, o docs, según la tarea);
  3. `docs(spec-008): record Tn checks`: añade a validation.md lo comprobado en la tarea;
  4. `docs(spec-008): mark Tn done`: marca la casilla de la tarea en este fichero.
- Docker: cada orden necesita OK, una a una. Las de frontend (`npx vitest run`, `npm run build`, `npx eslint <ficheros>`, `npm run api:gen`, `npm run api:check`, `npx vitest list`) no usan Docker.
  - D1. `docker compose ps --status running --format '{{.Service}}'`
  - D2. `docker compose exec backend pytest -q <rutas>`
  - D3. `docker compose exec backend pytest -q`
  - D4. `docker compose exec backend sh -c "ruff check . && ruff format --check ."`
  - D5. `docker compose exec -u "$(id -u)" backend ruff format <ficheros>`
  - D6. `docker compose exec backend pytest --collect-only -q <rutas>`
  - D7 (T2). `docker compose run --rm --no-deps -e DB_HOST=db-inexistente.invalid -u "$(id -u)" --entrypoint "" backend python manage.py makemigrations assets`
  - D8 (T2). `docker compose exec backend pytest -q --create-db apps/assets config/tests/test_migrations.py`, y después `docker compose exec -e DJANGO_ENV=test backend python manage.py sqlmigrate assets 0005`
  - D9 (T5). `docker compose run --rm --no-deps -e DB_HOST=db-inexistente.invalid -u "$(id -u)" --entrypoint "" backend python manage.py spectacular --format openapi-json --file openapi.json --validate --fail-on-warn --lang en`
  - D10 (T1, T6). `docker compose exec backend pytest -q -s --run-measurement apps/assets/tests/test_list_query_plan.py`
  - D11 (T10, orden expresa en ese momento). Solo `docker compose exec backend python manage.py migrate` en la BD de desarrollo. No se ejecuta el comando de demostración: la columna generada se rellena sola en los bienes que ya hay. Nunca antes.
- Todas las tareas con tests (T1 a T9): inventario y comparación de la colección de tests. Los tests existentes que cambian de aserción, con el mismo id, son los de T2, T5, T7 y T9.
  - Antes de tocar nada: D6 (backend) o `npx vitest list` (frontend) sobre las rutas indicadas, guardado en la carpeta temporal de la sesión.
  - Después de cada commit de la tarea: la misma orden y `diff` contra la colección anterior.
  - El diff tiene que ser exactamente el previsto en la tarea. Si no lo es, parar y enseñarlo sin seguir.
- Tanda previa a cada commit de código, la de AGENTS.md. Si los tests cambian después de una tanda, se repite entera. Los commits solo de docs no la llevan.
  - Backend, cada orden de Docker con OK:
    - pytest y ruff: D3 y D4;
    - migraciones, D12: `docker compose exec backend pytest -q config/tests/test_migrations.py`;
    - desfase de openapi.json, D13: `docker compose run --rm -T --no-deps -e DB_HOST=db-inexistente.invalid --entrypoint "" backend sh -c "python manage.py spectacular --format openapi-json --file /tmp/openapi.json --validate --fail-on-warn --lang en && diff /tmp/openapi.json openapi.json"`;
    - `manage.py check`, D14: `docker compose run --rm --no-deps -e DB_HOST=db-inexistente.invalid --entrypoint "" backend python manage.py check`.
  - Frontend, desde `frontend/`: `npx vitest run`, `npm run build`, `npx eslint <ficheros tocados>` y `npm run api:check`.
- Pruebas de mecanismo (M1 a M4): cada mutación sobre una copia del fichero, con sha256 antes y después y restauración, y sin ficheros en /tmp (procedimiento de «Aprendizajes» de MEMORY.md). No se edita ningún fichero versionado fuera del alcance de la tarea.
- Los ids de los tests nuevos son los que figuran aquí. Cualquier otro id, o un test existente que cambie de id, es una desviación: parar.

---

- [x] **T1. Medición inicial del plan de la consulta.** RNF Rendimiento
  - Qué:
    - backend/conftest.py (opción `--run-measurement`);
    - apps/assets/tests/test_list_query_plan.py (sondeo del entorno, 50 000 filas sintéticas, consultas en Z1 y Z2, `EXPLAIN (ANALYZE, BUFFERS)`);
    - specs/008-search-filters/validation.md (sección «Rendimiento: antes»).
  - Tests del plan: ninguno de B1-B13 ni F1-F7. Es el test de medición del plan.
  - Mutaciones: ninguna.
  - Parar y pedir OK: D1, D6 antes y después, D3, D4 y D10.
  - Riesgo: la opción de conftest afecta a toda la suite.
    - Inventario: `docker compose exec backend pytest --collect-only -q` (toda la suite) antes y después.
    - Diff previsto: solo dos líneas añadidas, `apps/assets/tests/test_list_query_plan.py::test_probe_the_test_database_environment` y `apps/assets/tests/test_list_query_plan.py::test_measure_the_list_query_plans`. Ninguna línea eliminada ni renombrada.
    - Sin `--run-measurement`, esos dos tests se saltan y la duración de `pytest -q` no cambia de forma apreciable.
  - Commits, en orden:
    1. `test(assets): measure public list query plan`
    2. `docs(spec-008): record T1 checks` (validation.md con el sondeo y la tabla «antes»)
    3. `docs(spec-008): mark T1 done`
  - Hecho cuando: pytest y ruff en verde, el diff de la colección es el previsto y la medición «antes» (sondeo, volumen y las consultas de Z1 y Z2) está en validation.md.

- [ ] **T2. Título plegado como columna generada.** RF-2
  - Qué:
    - apps/assets/folding.py;
    - apps/assets/models.py (`title_folded`);
    - apps/assets/migrations/0005_asset_title_folded.py;
    - apps/assets/tests/test_folding.py;
    - apps/assets/tests/test_models.py (`EXPECTED_FIELDS`, `EXPECTED_COLUMNS` y la regla de nulos y valores por defecto).
  - Tests del plan: B5.
  - Mutaciones: M4 (quitar una pareja solo en Python o solo en la expresión del modelo, sobre copia) → B5 debe ponerse en rojo.
  - Parar y pedir OK antes de escribir (migración): D1, D6, D7 (generación de 0005), D8 (`--create-db`, `test_migrations` y `sqlmigrate`), D2, D3 y D4. Aplicar 0005 en la BD de desarrollo no entra aquí: es T10.
  - Riesgo: se modifican tests existentes.
    - Inventario: `apps/assets/tests/test_models.py` (`test_the_model_has_exactly_these_fields`, `test_no_field_is_nullable_or_has_a_default` y los que comparan columnas) y `config/tests/test_migrations.py`.
    - Búsqueda previa de tests que comparen el SQL del INSERT: `grep -rn -i insert` en backend/apps/assets/tests y backend/config/tests no encontró ninguno al preparar estas tareas. Se confirma ejecutando D3 entera tras añadir la columna.
    - D6 sobre `apps/assets/tests config/tests`, antes y después.
    - Diff previsto: solo tres líneas añadidas, `apps/assets/tests/test_folding.py::test_the_fold_source_and_target_have_the_same_length_and_no_repeats`, `…::test_python_and_the_database_fold_every_character_of_the_table_the_same_way` y `…::test_characters_outside_the_table_stay_the_same_in_python_and_in_the_database`. Los ids de test_models.py y de test_migrations.py no cambian: solo cambian aserciones.
  - Commits, en orden:
    1. `feat(assets): add folded title column`
    2. `docs(spec-008): record T2 checks` (SQL de 0005 revisado, B5 y M4)
    3. `docs(spec-008): mark T2 done`
  - Hecho cuando: pytest con `--create-db`, ruff y `test_migrations` en verde, el SQL de 0005 revisado con `sqlmigrate`, el diff de la colección es el previsto y M4 registrada.

- [ ] **T3. Validación pura de los filtros y unión con la zona.** RF-3, RF-4
  - Qué: apps/assets/filters.py (`Filters`, `NO_FILTERS`, `parse_filters`, `parse_public_query`) y apps/assets/tests/test_filters.py.
  - Tests del plan: B7.
  - Mutaciones: ninguna (las cuatro del plan están en T2 y T4).
  - Parar y pedir OK antes de escribir (validación de entrada): D1, D2, D4 y D6.
  - Riesgo: ninguno sobre tests existentes. zone.py y test_zone.py no se tocan.
    - D6 sobre `apps/assets/tests`, antes y después.
    - Diff previsto: solo líneas añadidas, todas de `apps/assets/tests/test_filters.py::`. Ninguna línea eliminada ni renombrada.
  - Commits, en orden:
    1. `feat(assets): validate public list filters`
    2. `docs(spec-008): record T3 checks`
    3. `docs(spec-008): mark T3 done`
  - Hecho cuando: pytest y ruff en verde y el diff de la colección es el previsto.

- [ ] **T4. Selector con filtros.** RF-1, RF-2, RF-4, RF-5, RF-6
  - Depende de T2 y T3.
  - Qué: apps/assets/selectors.py (`filters=NO_FILTERS`) y apps/assets/tests/test_selectors.py.
  - Tests del plan: B1, B2, B3, B4, B6, B10 y B11 (partes del selector) y B12 (partes del selector).
  - Mutaciones, sobre copia de selectors.py:
    - M1: quitar `status="active"` u `owner__is_active=True` → B1 en rojo.
    - M2: buscar también en `description` → B3 en rojo.
    - M3: comparar con un LIKE sin escapar, `.extra(where=["title_folded LIKE %s"], params=[f"%{fragment}%"])`, en lugar de `contains` → B2 en rojo, porque «%» devuelve todos los bienes.
  - Parar y pedir OK antes de escribir (privacidad): D1, D6 antes y después, D2, D3, D4 y la tanda previa al commit.
  - Riesgo: los tests de fugas existentes no se tocan, ni su código ni su id, porque la spec pide que sigan pasando sin modificarse.
    - Inventario de los tests existentes de test_selectors.py que no se tocan: `test_a_paused_asset_is_not_returned_even_if_its_owner_is_active` (207), `test_an_active_asset_of_an_owner_with_a_deactivated_account_is_not_returned` (213), `test_a_row_has_exactly_the_whitelisted_keys` (278), `test_the_exact_location_appears_nowhere_in_the_query` (491), `test_the_select_clause_has_no_user_or_owner_columns` (495) y `test_the_select_clause_has_no_columns_outside_the_whitelist` (513, ya parametrizado por columnas).
    - Los tests nuevos con filtros llevan sus propias aserciones, compartidas solo entre ellos con un ayudante nuevo del mismo módulo.
    - D6 sobre `apps/assets/tests`, antes y después. Diff previsto: 45 ids añadidos y ninguno eliminado ni renombrado, todos de `apps/assets/tests/test_selectors.py::`:
      - `test_a_paused_asset_is_not_returned_with_any_filter[category|text|both]` (3)
      - `test_an_asset_of_a_deactivated_account_is_not_returned_with_any_filter[category|text|both]` (3)
      - `test_a_text_match_outside_the_zone_is_not_returned[text|both]` (2)
      - `test_the_category_filter_returns_only_that_category` (1)
      - `test_category_and_text_return_only_the_assets_that_meet_both` (1)
      - `test_a_well_formed_unknown_category_returns_nothing_and_is_complete` (1)
      - `test_the_wildcards_and_quotes_of_the_text_are_literal[percent|underscore|backslash|dot-star|quote]` (5)
      - `test_the_text_is_not_searched_in_the_description_the_owner_the_coordinates_or_the_category_name[description|owner-email|coordinate|category-name]` (4)
      - `test_a_text_of_only_format_or_combining_characters_does_not_return_every_asset[zero-width-space|right-to-left-override|combining-acute]` (3)
      - `test_the_text_ignores_case_and_accents_but_not_the_enye[esqui|bici|upper-esqui|start|middle|end|nfd|enye]` (8)
      - `test_the_limit_applies_after_the_filter[201-match|5-of-201-match]` (2)
      - `test_a_row_has_exactly_the_whitelisted_keys_with_any_filter[category|text|both]` (3)
      - `test_the_exact_location_appears_nowhere_in_the_query_with_any_filter[category|text|both]` (3)
      - `test_the_select_clause_has_no_user_or_owner_columns_with_any_filter[category|text|both]` (3)
      - `test_the_select_clause_has_no_columns_outside_the_whitelist_with_any_filter[category|text|both]` (3)
  - Commits, en orden:
    1. `feat(assets): filter public assets by category and title`
    2. `docs(spec-008): record T4 checks` (SQL capturado con cada filtro y M1-M3)
    3. `docs(spec-008): mark T4 done`
  - Hecho cuando: pytest (incluido `test_architecture`) y ruff en verde, el diff de la colección es el previsto y M1, M2 y M3 están registradas.

- [ ] **T5. Endpoint con filtros y contrato.** RF-1, RF-2, RF-3, RF-4, RF-5, RF-6
  - Depende de T4. Vista y contrato van en un solo commit de código, porque la tanda previa comprueba el desfase de openapi.json.
  - Qué:
    - apps/assets/views.py (parseo dentro de `get`, `category` y `q` con `required=False`);
    - apps/assets/tests/test_public_list_api.py;
    - backend/openapi.json y frontend/src/api/schema.gen.ts (`npm run api:gen`);
    - docs/architecture.md.
  - Tests del plan: B1 (API), B8, B9, B10 (API), B11 (API), B12 (API) y B13.
  - Mutaciones: ninguna propia (M1 a M4 están en T2 y T4).
  - Parar y pedir OK antes de escribir (contrato y seguridad): D1, D6 antes y después, D2, D3, D4, D9 y la tanda previa al commit. El cambio de contrato (parámetros `category` y `q` y códigos nuevos dentro de `params`) está aprobado en el plan.
  - Riesgo: tres tests existentes cambian de contenido y los de fugas no se tocan.
    - Cambian de aserciones, con el mismo id:
      - `test_unknown_parameters_are_ignored` (381-389): `category=pool` y `q=taladro` dejan de ser desconocidos y se sustituyen por nombres desconocidos y por `Category` y `Q`.
      - `test_the_openapi_description_is_valid_and_documents_the_list` (871-902): el conjunto de parámetros pasa a seis y `required` es True solo en los cuatro límites.
      - `test_input_errors_are_not_stored_and_do_not_echo_the_values_or_log_them` (361): `sent` gana un `category` y un `q` inválidos y centinela, que no deben salir en el cuerpo ni en `caplog`. `assert_error_format` (153) no cambia: ya admite `sent_values`.
    - No se tocan, ni su código ni su id: `test_every_kind_of_visitor_receives_the_same_body_without_hidden_assets` (169), `test_a_paused_asset_never_appears_not_even_for_its_owner_with_a_session` (191), `test_an_active_asset_of_a_deactivated_account_is_hidden` (200), `test_the_root_and_every_asset_have_exactly_the_planned_keys` (233) y `test_the_body_never_contains_the_exact_location` (245). Los tests nuevos con filtros llevan sus propias aserciones, compartidas solo entre ellos con un ayudante nuevo del mismo módulo.
    - D6 sobre `apps/assets/tests/test_public_list_api.py`, `apps/assets/tests/test_public_list_session.py` y `config/tests`, antes y después.
    - Diff previsto de la colección: 28 ids añadidos y ninguno eliminado ni renombrado, todos de `apps/assets/tests/test_public_list_api.py::`:
      - `test_the_category_filter_returns_only_that_category` (1)
      - `test_a_well_formed_unknown_category_returns_200_and_an_empty_complete_list` (1)
      - `test_category_and_text_together_return_only_the_assets_that_meet_both` (1)
      - `test_the_limit_applies_after_the_filter[201-match|5-of-201-match]` (2)
      - `test_every_kind_of_visitor_receives_the_same_body_with_any_filter[<filtro>-<visitante>]`, con filtro en category, text y both y visitante en anonymous, owner y staff (9)
      - `test_a_paused_asset_never_appears_with_any_filter[category|text|both]` (3)
      - `test_an_active_asset_of_a_deactivated_account_is_hidden_with_any_filter[category|text|both]` (3)
      - `test_the_root_and_every_asset_have_exactly_the_planned_keys_with_any_filter[category|text|both]` (3)
      - `test_the_body_never_contains_the_exact_location_with_any_filter[category|text|both]` (3)
      - `test_with_the_limit_exceeded_invalid_filters_are_still_429` (1)
      - `test_a_successful_request_with_a_text_does_not_leave_it_in_the_logs` (1; con los logs al nivel de producción, INFO)
    - El mismo commit lleva `openapi.json`, `schema.gen.ts` y `docs/architecture.md`, que no cambian la colección de tests.
  - Commits, en orden:
    1. `feat(api): accept category and text filters`
    2. `docs(spec-008): record T5 checks`
    3. `docs(spec-008): mark T5 done`
  - Hecho cuando: pytest, ruff, vitest, build y `npm run api:check` en verde, `spectacular --validate --fail-on-warn` limpio y sin desfase de `openapi.json`, el diff de la colección es el previsto y la tabla de errores y la descripción OpenAPI de `category` y `q` están revisadas.

- [ ] **T6. Medición después y decisión sobre el índice.** RNF Rendimiento
  - Depende de T5.
  - Qué: apps/assets/tests/test_list_query_plan.py (las consultas candidatas pasan a usar el selector real, y se borran) y specs/008-search-filters/validation.md («Rendimiento: después», criterios y recomendación).
  - Tests del plan: ninguno de B1-B13 ni F1-F7.
  - Mutaciones: ninguna.
  - Parar y pedir OK: D1, D6 antes y después, D10 (con `--create-db` si cambió el esquema), D3 y D4.
  - Riesgo: el módulo de medición solo cambia de contenido.
    - D6 sobre `apps/assets/tests/test_list_query_plan.py`, antes y después.
    - Diff previsto: vacío (mismos dos ids que T1).
  - Commits, en orden:
    1. `test(assets): measure the real selector with filters`
    2. `docs(spec-008): record T6 checks` (mediciones antes y después, criterios y la decisión sobre el índice)
    3. `docs(spec-008): mark T6 done`
  - Hecho cuando: las mediciones «antes» y «después» y la decisión están en validation.md, los criterios del plan están evaluados (si uno falla, se registra con su propuesta y no bloquea) y pytest está en verde. Si la medición recomienda el índice GiST funcional, solo se anota: es un cambio aparte.

- [ ] **T7. Estado de filtros y petición filtrada.** RF-8, RF-9, RF-10, RF-12
  - Depende de T5.
  - Qué:
    - frontend/src/search/filters.ts y src/search/categories.ts, y sus tests;
    - src/api/publicAssets.ts (tercer argumento opcional);
    - src/map/loadAssets.ts;
    - src/i18n/es.ts (nombres de las 12 categorías).
  - Tests del plan: F1, F2, F3 y F5.
  - Mutaciones: ninguna (el plan no pide ninguna en el frontend).
  - Parar y pedir OK: ninguno de Docker. Implementar sin esperar y enseñar el diff antes del commit.
  - Riesgo: un test existente cambia de aserción.
    - Inventario: `src/map/loadAssets.test.ts` (línea 58, `toHaveBeenCalledExactlyOnceWith(box, controller.signal)`), `src/api/publicAssets.test.ts` (152-221) y los de `src/i18n`.
    - `npx vitest list src/search src/map src/api src/i18n`, antes y después.
    - Diff previsto: solo líneas añadidas, de `src/search/filters.test.ts`, `src/search/categories.test.ts` y un `it` nuevo en `src/map/loadAssets.test.ts`. Ninguna eliminada ni renombrada. En `loadAssets.test.ts` cambia solo la aserción de la línea 58, que pasa a esperar el tercer argumento de filtros. `publicAssets.test.ts` no cambia.
  - Commits, en orden:
    1. `feat(search): add filter state and filtered request`
    2. `docs(spec-008): record T7 checks`
    3. `docs(spec-008): mark T7 done`
  - Hecho cuando: vitest, build y eslint de los ficheros tocados en verde, `CATEGORY_CHIPS` igual a `CATEGORY_KEYS` y el diff de la colección es el previsto.

- [ ] **T8. Barra de filtros: buscador «Qué» y chips.** RF-7, RF-8, RF-9, RF-10
  - Depende de T7.
  - Qué:
    - frontend/src/search/FilterBar.tsx y su test;
    - src/pages/MapPage.tsx (estado y ref de filtros, disposición en columna, barra no pintada con el estilo fallido);
    - src/styles/buttons.css (`.chip`);
    - src/i18n/es.ts;
    - docs/architecture.md.
  - Tests del plan: F6.
  - Mutaciones: ninguna.
  - Parar y pedir OK antes de escribir (privacidad: la URL y el almacenamiento del navegador): ninguno de Docker.
  - Riesgo: ninguno sobre tests existentes.
    - `npx vitest list src/search src/pages`, antes y después. Diff previsto: solo líneas añadidas, de `src/search/FilterBar.test.ts`.
  - Verificación en navegador (Chrome DevTools a 375 y 1280 px): teclado, 44 px, una petición por cambio, la URL no cambia, `localStorage` y `sessionStorage` vacíos, posición del aviso flotante y consola sin errores.
    - Los datos reales con filtro de texto no se pueden comprobar hasta aplicar 0005 en la BD de desarrollo, que es T10. Aquí se comprueban la maquetación, el teclado y los estados de error y de vacío simulados.
  - Commits, en orden:
    1. `feat(map): add category chips and search box`
    2. `docs(spec-008): record T8 checks`
    3. `docs(spec-008): mark T8 done`
  - Hecho cuando: vitest, build y eslint en verde, el diff de la colección es el previsto y la verificación en navegador está en validation.md sin errores de consola.

- [ ] **T9. Panel con filtros y encabezados de la pantalla.** RF-11, RF-12, RF-13
  - Depende de T8.
  - Qué:
    - frontend/src/state/viewState.ts;
    - src/panel/header.ts y src/panel/ResultsPanel.tsx;
    - src/pages/MapPage.tsx (`h1` oculto);
    - src/i18n/es.ts;
    - sus tests.
  - Tests del plan: F4 y F7.
  - Mutaciones: ninguna.
  - Parar y pedir OK: ninguno de Docker. Implementar sin esperar y enseñar el diff antes del commit.
  - Riesgo: varios tests existentes cambian de aserción.
    - Inventario:
      - `src/state/viewState.test.ts`: los `toEqual` exactos de `results` (línea 47-51) y de `empty` (63-69, 75-84), que ganan `filtered`;
      - `src/panel/header.test.ts`: la tabla de `statusText` (37-52);
      - `src/panel/ResultsPanel.test.ts`: los de la región de estado y la cabecera (107-121, 139-148), por el cambio de `<p>` a `<h2>`.
    - `npx vitest list src/state src/panel`, antes y después.
    - Diff previsto: solo líneas añadidas (los `it` nuevos de F4 y F7 en `viewState.test.ts`, `header.test.ts` y `ResultsPanel.test.ts`). Ninguna eliminada ni renombrada: los ids existentes no cambian.
    - Si el tipo de `filtered` se vuelve obligatorio, las tablas de los tests existentes se actualizan para que `tsc -b` compile.
  - Verificación en navegador (Chrome DevTools a 375 y 1280 px): vacío y error con filtros (simulados), «Reintentar» con los mismos filtros y el árbol de accesibilidad con un `h1` y un `h2`; con el estilo bloqueado, solo el `h1`.
  - Commits, en orden:
    1. `feat(panel): add filtered states and headings`
    2. `docs(spec-008): record T9 checks`
    3. `docs(spec-008): mark T9 done`
  - Hecho cuando: vitest, build y eslint en verde, el diff de la colección es el previsto y la verificación en navegador está en validation.md sin errores de consola.

- [ ] **T10. Validación de punta a punta y en el navegador.** RF-1 a RF-13
  - Depende de T9.
  - Qué: specs/008-search-filters/validation.md (RF por RF, mutaciones M1-M4, navegador a 375 y 1280 px y medición).
  - Tests del plan: ninguno nuevo. Se ejecutan todos.
  - Mutaciones: se recogen las de T2 y T4.
  - Parar y pedir OK antes de escribir: D11 (solo `migrate` en la BD de desarrollo, orden expresa en ese momento), D1, D3 y D4.
  - Riesgo: ninguno sobre tests existentes. Ninguno se toca en esta tarea.
  - Comprobación, con los bienes de demostración que ya hay en la BD de desarrollo: en la vista inicial, un chip deja solo sus tarjetas y círculos; «esqui» encuentra «Equipo de esquí de pista completo»; «Quitar filtros» devuelve las 24 tarjetas; recorrido con teclado, anuncios, 44 px, sin limón; URL y almacenamiento sin cambios; red solo al propio origen y a OpenFreeMap.
  - Commits, en orden:
    1. `docs(spec-008): record T10 checks`
    2. `docs(spec-008): mark T10 done`
  - Hecho cuando: pytest, ruff, vitest, build y eslint en verde y validation.md completo con el veredicto y lo que quede abierto (índice, alfabeto de la tabla de plegado).

---

## Avisos y desviaciones
- Reparto: ninguna desviación. Son T1 a T10 del plan, con los mismos RF.
- Fuera del plan (cada elemento, con su motivo):
  - `npx vitest list` como equivalente de `pytest --collect-only` en el frontend. Motivo: aplicar el mismo inventario y diff a T7 y T9.
  - Ids concretos de los tests nuevos, para que el diff de la colección sea exacto. Son un detalle de tarea, no un requisito de la spec.
  - Varios commits por tarea (feat, record y mark), según lo pedido para esta fase. La plantilla de la skill propone un commit por tarea.
- Hasta T10, la BD de desarrollo no tiene `title_folded`. El mapa sin filtro y con categoría funciona en desarrollo, pero cualquier búsqueda con texto falla con un error de columna inexistente.
- T4, T5 y T8 pueden pasar de 30 minutos; si se alargan, se avisa al llegar.
- La validación formal de la spec (`/sdd-validate`) y el cierre del estado de la spec y de MEMORY.md van después de T10 y no son una de estas tareas.
