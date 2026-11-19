# Validación — 015-login
Rama: `feature/015-login` · Entorno: backend en Docker Compose (contenedores sueltos sin BD para las comprobaciones de lectura; stack levantado para los tests), frontend en el host

## Comprobaciones en el contenedor (2026-11-18)
Lectura del código de Django y DRF que el plan supone, antes de las tareas de código. Ninguna orden necesita la BD ni el stack levantado: cada una lanza un contenedor suelto con `--no-deps -e DB_HOST=db-inexistente.invalid`.

### Versiones
`docker compose run --rm --no-deps -e DB_HOST=db-inexistente.invalid --entrypoint "" backend python -c "import django, rest_framework, drf_spectacular; print(django.get_version(), rest_framework.VERSION, drf_spectacular.__version__)"` → `5.2.18 3.18.3 0.30.0`: Django 5.2.18, DRF 3.18.3 y drf-spectacular 0.30.0, las versiones que supone el plan.

### Orden de lectura
- La orden original del plan, con `inspect.getsource`, falla antes de imprimir nada: importar `django.contrib.auth.backends` carga `django.contrib.auth.models` y, sin ajustes, Django lanza `ImproperlyConfigured: Requested setting INSTALLED_APPS, but settings are not configured`.
- Se sustituye por una lectura con `ast` de los ficheros fuente, sin importar Django, que además da los números de línea. Es la orden de «Comprobaciones en el contenedor» del plan, corregida en `6250f43`. Lee 16 objetos: los 9 de la orden original más `make_password`, `check_password` (de `hashers`), `ModelBackend.user_can_authenticate`, `AbstractBaseUser.set_password`, `AbstractBaseUser.check_password`, `authenticate` y `login`, necesarios para contar los hashes y seguir las señales. La salida (323 líneas) no se versiona; se reproduce con la orden del plan (`6250f43`).

### Resultado punto por punto
Las rutas son relativas a `site-packages/`.
Las rutas que empiezan por `backend/` son del repo, con las líneas de `8d68801`.

**Recuento de hashes** (confirmado: un hash en cada caso de credenciales erróneas, con la contraseña guardada al coste actual):

| Caso | Recorrido | Hashes |
|---|---|---|
| Email desconocido consultable | `django/contrib/auth/backends.py:65-69`: `DoesNotExist` → `UserModel().set_password(password)` → `base_user.py:97` `make_password` → `hashers.py:113` `hasher.encode` | 1 |
| Contraseña errónea | `backends.py:71` → `base_user.py:112` → `hashers.py:80` → `verify_password`: `fake_runtime` falso, `must_update` falso → `hashers.py:60` `hasher.verify` | 1 |
| Cuenta desactivada | `backends.py:71`: `check_password` se evalúa antes que `user_can_authenticate` (`backends.py:96`, `is_active`), con la contraseña correcta o errónea | 1 |
| Contraseña inutilizable | `hashers.py:42` (`not is_password_usable`) → `hashers.py:51-56`: `make_password(get_random_string(...))` con el hasher por defecto | 1 |
| Email o contraseña `None` | `backends.py:60-63`: el email sale de `kwargs[USERNAME_FIELD]` y la función vuelve antes, sin hash | 0 |

- **Coste antiguo, contraseña errónea** (confirmado): `hashers.py:66-67` llama a `harden_runtime` solo con contraseña errónea, `must_update` y el mismo algoritmo; con un hasher distinto del preferido (`hashers.py:58`) no endurece. Recogido en «Riesgos aceptados» de la spec.
- **Rehash con la contraseña correcta** (confirmado): `hashers.py:81-82` y `base_user.py:106-110` (`set_password` y `save(update_fields=["password"])`), antes de comprobar `is_active` (`backends.py:71`), así que también en una cuenta desactivada.
- **Falso verde del test de recuento** (confirmado): una cuenta con un hasher fuera de la lista cae en `hashers.py:45-49` y de ahí en la rama falsa, con un hash.

**Resto de puntos:**
- **`BaseThrottle.get_ident` con `NUM_PROXIES=0`** (confirmado): `rest_framework/throttling.py:31` lee `api_settings.NUM_PROXIES`, no un atributo de la clase; `throttling.py:33-35` devuelve `REMOTE_ADDR` con 0 e ignora `X-Forwarded-For`. Sin `REMOTE_ADDR` devuelve `None`, que `ip_bucket` lleva al cubo fijo (`backend/apps/users/throttling.py:11-12`).
- **`APIView.dispatch` y el 405** (confirmado; explicación del plan corregida en `6250f43`): `rest_framework/views.py:514` llama a `initial()` antes de resolver el método (`views.py:517-521`), así que los límites, que se aplican en `super().initial()`, ganan al 405 y lo cuentan. Un método no admitido se salta el CSRF por la condición del mixin (`backend/apps/core/csrf.py:25-29`), no por `dispatch`.
- **`SimpleRateThrottle.wait`** (confirmado): `throttling.py:154` cuenta la espera desde `history[-1]`, la anotación más antigua; con más anotaciones que el límite, `throttling.py:158-160` devuelve `None`, que `backend/apps/core/api.py:78` (`max(1, exc.wait or 1)`) convierte en `retry_after` 1. Con exactamente 20 anotaciones coincide con `wait_seconds`; el `wait()` propio solo cambia algo con más.
- **`LocMemCache._cull`** (confirmado): `django/core/cache/backends/locmem.py:97` borra `len // cull_frequency` entradas (2 000 con 10, 6 666 con 3) y `locmem.py:93-95` vacía el almacén con 0.
- **`salted_hmac`** (confirmado): firma `(key_salt, value, secret=None, *, algorithm="sha1")` en `django/utils/crypto.py:19`, así que `algorithm="sha256"` va explícito; `crypto.py:27-28` lee `SECRET_KEY` en cada llamada; `crypto.py:45` aplica `force_bytes(value)`, que deja pasar los `bytes` (un `str` con un sustituto suelto fallaría en la codificación UTF-8 estricta, de ahí el `surrogatepass` previo).
- **`SessionBase._validate_session_key`** (confirmado): `django/contrib/sessions/backends/base.py:220` solo exige `key and len(key) >= 8`, sin comprobar el alfabeto: ocho nulos pasan la validación (premisa de la Desviación 2 del plan).
- **`SessionBase.is_empty`** (confirmado): `base.py:185-190` no carga la sesión.
- **`login()`** (confirmado): sin `SESSION_KEY` hace `cycle_key` (`django/contrib/auth/__init__.py:186-187`), después `rotate_token` (`__init__.py:196`) y emite `user_logged_in` (`__init__.py:197`). Con la misma cuenta y el mismo hash no hay `flush()` ni `cycle_key` (`__init__.py:175-185`), así que la clave de sesión no cambia, aunque `rotate_token` (`__init__.py:196`) sí rota el token CSRF; y una sesión anónima conserva sus datos (`__init__.py:156-157`). De ahí el `flush()` explícito antes de `login()`.
- **`authenticate` y `user_login_failed`** (confirmado): la señal solo se emite si todos los backends devuelven `None` (`__init__.py:125-128`), así que los rechazos por la forma no la emiten; `authenticate` declara `@sensitive_variables("credentials")` (`__init__.py:107`), y quedan sin tapar `username` y `password` de `ModelBackend.authenticate` (riesgo del plan corregido en `6250f43`).

### Lo que esta lectura no cubre
Se fija con tests en la tarea indicada; si un test muestra un comportamiento distinto del que supone el plan, se para y se avisa.

| Punto | Dónde se comprueba |
|---|---|
| `MD5PasswordHasher.verify` calcula el hash con `encode` (base del recuento) | T4, recuento de hashes |
| `_clean_credentials` tapa la contraseña en `user_login_failed` | T4 y T6 (receptor temporal) |
| `flush()` no emite `user_logged_out`; `update_last_login` es el único receptor de Django en `user_logged_in` | T4 (señal de salida, caracterización) y T5 |
| `sensitive_variables` en un método de una `APIView` y en la página técnica | T4 (`check_credentials`) y T6 (`LoginView.post`) |
| Una `property` `cache` sustituye al atributo de clase de `SimpleRateThrottle` | T2 (`override_settings` de `CACHES`) |
| `Throttled(wait)` redondea hacia arriba | No influye: `wait_seconds` ya devuelve segundos enteros; el `retry_after` de los dos límites se comprueba en T2, T3 y T6 |
| `LOCATION` separa los diccionarios de LocMemCache | T2 (`test_cache_settings.py`, aislamiento) |
| Expulsión por LRU de LocMemCache | Sin test: riesgo aceptado en la spec (D7 del plan) |
| Cookies que escriben o borran `SessionMiddleware` y `CsrfViewMiddleware` cuando llegan mal formadas | T5 (respuesta idéntica por estado de cookie) |
| Cookie `sessionid` con nulos por escape octal | T5 (Desviación 2) |
| drf-spectacular: `LoginRequest` y `LoginError` pasan `--fail-on-warn` | T5 (regeneración del contrato) |

## T2. Almacén `login` y límite por IP
Fecha: 2026-11-18 · Commits: `91503e9` (`Clock` a `helpers.py`) y `b9602d3` (`feat`, con el almacén, `wait_seconds`, `client_bucket`, `LoginIpThrottle`, las vistas de test y los dos ficheros de tests nuevos).

### Rojo, antes del código
- `config/tests/test_cache_settings.py`: `6 failed, 2 passed`. Los seis fallan con `InvalidCacheBackendError: The connection 'login' doesn't exist.`: `test_the_cache_aliases_are_exactly_default_and_login`, `test_login_has_its_own_location`, `test_login_declares_its_capacity_and_cull_options`, `test_login_cache_drops_a_tenth_of_its_entries_when_it_is_full`, `test_a_key_written_in_login_does_not_exist_in_default` y `test_a_key_written_in_default_does_not_exist_in_login`. Los dos que pasan, `test_default_is_local_memory_without_options` y `test_default_cache_keeps_its_capacity_of_300_entries`, caracterizan el almacén `default`, que ya existía.
- `apps/users/tests/test_login_throttling.py`: `1 error during collection`, `ImportError: cannot import name 'LOGIN_CACHE_ALIAS' from 'apps.users.throttling'` (no existían `LOGIN_CACHE_ALIAS`, `LoginIpThrottle`, `client_bucket` ni `wait_seconds`). Las vistas de test se escribieron con el código, porque importan `LoginIpThrottle`.

### Verde, después del código
- Los dos ficheros nuevos: `46 passed` (8 de la caché y 38 del límite). Capacidad medida con la API pública de la caché: 18 001 claves supervivientes tras escribir 20 001 en `login` y 201 tras escribir 301 en `default`, los números previstos (la caché expulsa antes de insertar).
- Suite entera, con `test_migrations.py`, `test_production.py` y `test_settings.py`: `2267 passed in 51.60s`.
- `ruff check .`: `All checks passed!`. `ruff format --check .`: `146 files already formatted`. El primer `ruff check` dio un `E501` en un comentario de un test, de 89 columnas; se acortó.
- Tras las mutaciones, con los ficheros restaurados: `519 passed` en los módulos nuevos y en `apps/users/tests`.

### Desfase de `openapi.json`
La orden de la CI (`python manage.py spectacular --format openapi-json --file /tmp/openapi.json --validate --fail-on-warn --lang en && diff /tmp/openapi.json openapi.json`), lanzada en un contenedor suelto con `--no-deps -e DB_HOST=db-inexistente.invalid`: salida `exit=0`, sin ninguna línea de `diff` y sin avisos de validación. La T2 no toca vistas, serializers ni URLs de producción.

### Pruebas de mecanismo
Cada mutación se hizo sobre el fichero con copia previa, sha256 antes y después y restauración desde la copia; los doce hashes coincidieron (`throttling.py` `a191a1167813…`, `base.py` `7b88eb531408…`). Se ejecutaron los dos ficheros de tests nuevos. Son las 7 de la tarea, con sus variantes (M2a y M2b, M5a y M5b, M7a y M7b), más M5c y M8.

| Mutación | Cambio | Tests que la matan |
|---|---|---|
| M1 | `wait_seconds` cuenta desde `history[-1]`, la anotación más antigua | `test_wait_seconds_counts_from_the_entry_that_leaves_the_count_below_the_limit`, `test_the_wait_comes_from_the_entry_that_leaves_the_count_below_the_limit` |
| M2a | Ventana fija: un `allow_request` propio vacía el historial cuando la anotación más antigua cumple la ventana | `test_the_window_slides_instead_of_resetting`, solo por su aserción final: la 11.ª petición, tras las 10 que pasan a los 60 s, da 200 en vez de 429; sin ella la mutación sobrevive |
| M2b | Sin podar la ventana | `test_throttled_requests_do_not_count_and_do_not_extend_the_wait`, `test_the_window_frees_up_as_the_clock_advances`, `test_the_window_slides_instead_of_resetting` |
| M3 | `throttle_failure` anota también los rechazos | `test_the_wait_comes_from_the_entry_that_leaves_the_count_below_the_limit`, `test_throttled_requests_do_not_count_and_do_not_extend_the_wait`, `test_the_window_slides_instead_of_resetting` |
| M4 | `cache` devuelve `caches["default"]` | `test_the_counters_live_in_the_login_cache_and_not_in_default`, `test_the_cache_is_resolved_at_each_use_and_follows_override_settings`, `test_the_wait_comes_from_the_entry_that_leaves_the_count_below_the_limit` |
| M5a | `MAX_ENTRIES` 300 | `test_login_declares_its_capacity_and_cull_options`, `test_login_cache_drops_a_tenth_of_its_entries_when_it_is_full` |
| M5b | `login` sin `LOCATION`, la misma que `default` | `test_login_has_its_own_location`, `test_a_key_written_in_login_does_not_exist_in_default`, `test_a_key_written_in_default_does_not_exist_in_login`, `test_the_counters_live_in_the_login_cache_and_not_in_default` |
| M5c | `CULL_FREQUENCY` 3, el valor por defecto de Django, en lugar del 10 elegido en el plan (D7) | los mismos dos que M5a |
| M6 | Sin el `wait()` propio: queda el de DRF | `test_the_wait_comes_from_the_entry_that_leaves_the_count_below_the_limit` |
| M7a | `client_bucket` toma la IP de `X-Forwarded-For` | `test_client_bucket_ignores_x_forwarded_for`, `test_x_forwarded_for_is_ignored` |
| M7b | `NUM_PROXIES = None` en los ajustes | los mismos dos que M7a |
| M8 | `cache` como atributo de clase, resuelto al importar | `test_the_cache_is_resolved_at_each_use_and_follows_override_settings` |

### Puntos de «Lo que esta lectura no cubre» resueltos en esta tarea
- Una `property` `cache` sustituye al atributo de clase de `SimpleRateThrottle`: confirmado (el test del `override_settings` y M8).
- `LOCATION` separa los diccionarios de `LocMemCache`: confirmado (aislamiento en los dos sentidos y M5b).
- `Throttled(wait)` redondea hacia arriba: no influye, porque `wait_seconds` ya devuelve segundos enteros.

### Desviaciones y añadidos respecto del plan
- **`client_bucket` y la clave del límite**: `LoginIpThrottle.get_cache_key` usa `client_bucket(request)` en vez de calcular `ip_bucket(self.get_ident(request))`. Es la misma identidad, con el mismo camino que `RegistrationThrottle` (`BaseThrottle.get_ident`, que respeta `NUM_PROXIES`) y sin leer `REMOTE_ADDR` a mano. Evita que `client_bucket` quede sin uso hasta la T3 y que haya dos definiciones de la IP del visitante. Sus tests directos (el cubo de `REMOTE_ADDR`, `X-Forwarded-For` ignorado, direcciones no válidas al cubo fijo y la clave del límite) pasan de la T3 a la T2; la T3 usa `client_bucket` para la clave del par.
- **Añadido**: `LoginIpLimitedSessionView` y su ruta, para probar que el límite también alcanza a quien tiene sesión; el test `test_the_cache_is_resolved_at_each_use_and_follows_override_settings`, que fija la `property`; y las mutaciones M5c y M8.
- **`conftest.py`**: `clear_default_cache` pasa a `clear_caches` y vacía todos los alias de `CACHES`.

## T3. Clave del par y límite de fallos
Fecha: 2026-11-18 · Commit: `881b895` (`feat`, con `LOGIN_PAIR_KEY_SALT`, `login_pair_key`, `LoginFailureLimit` y 19 tests nuevos en `test_login_throttling.py`).

### Rojo, antes del código
- `apps/users/tests/test_login_throttling.py`: `1 error during collection`, `ImportError: cannot import name 'LoginFailureLimit' from 'apps.users.throttling'` (no existían `LoginFailureLimit` ni `login_pair_key`). Ruff estaba limpio sobre los tests.

### Verde, después del código
- `test_login_throttling.py`: `57 passed` (38 de la T2 y 19 nuevos: 9 de la clave del par, 9 del límite y el de la `property`).
- Suite entera, con `test_migrations.py`, `test_production.py` y `test_settings.py`: `2286 passed in 47.68s`.
- `ruff check .`: `All checks passed!`. `ruff format --check .`: `146 files already formatted`.
- Ningún fichero de test tocado contiene U+00A8 literal: comprobado con un script que busca los bytes `c2 a8` sin escribir el carácter.
- Desfase de `openapi.json`: la orden de la CI de la T2, lanzada en un contenedor suelto con `--no-deps -e DB_HOST=db-inexistente.invalid`, termina con `exit=0`, sin ninguna línea de `diff` y sin avisos de validación. La T3 no toca vistas, serializers ni URLs de producción.
- Frontend, en el host: `npm run api:check` con `exit=0`; `npm test` (vitest) con `34 passed` ficheros y `1174 passed` tests; `npm run build` con `exit=0` y el aviso de Vite sobre chunks de más de 500 kB. La T2 no ejecutó vitest, build ni `api:check`. Ni la T2 ni la T3 tocan el frontend, y por eso no hay `eslint` de ficheros tocados.

### Pruebas de mecanismo
Una sola ejecución sobre el código del commit `881b895`, con las 18 mutaciones. Cada una se hizo sobre `throttling.py` con copia previa fuera del repo y fuera de `/tmp`, sha256 antes y después y restauración desde la copia; los dos hashes coincidieron (`9d34caf36036…`). Se ejecutó `test_login_throttling.py` entero. Mueren las 18. M1 a M8 son las del plan; M9 a M16 se añaden en la tarea.

| Mutación | Cambio | Tests que la matan |
|---|---|---|
| M1 | Clave sin secreto: `hashlib.sha256` en lugar de `salted_hmac` | `test_the_secret_key_changes_the_key`, `test_the_key_hashes_a_single_normalization_of_the_raw_email` |
| M2 | Email normalizado en claro en la clave | `test_the_pair_key_carries_neither_the_email_nor_a_marker`, `test_the_secret_key_changes_the_key`, `test_the_key_hashes_a_single_normalization_of_the_raw_email` |
| M3 | `encode("utf-8")` estricto | `test_a_lone_surrogate_and_a_null_character_give_distinct_keys_without_failing` |
| M4 | Normalizar dos veces | `test_the_key_hashes_a_single_normalization_of_the_raw_email` |
| M5 | Clave sin cubo (`login_pair:{digest}`) | `test_another_bucket_gives_another_key`, `test_the_key_hashes_a_single_normalization_of_the_raw_email` |
| M6 | Ventana fija: se vacía el historial cuando la anotación más antigua cumple la ventana | `test_the_window_slides_and_the_entry_on_the_boundary_leaves` |
| M7 | Espera desde la anotación más antigua | `test_wait_with_seven_entries_counts_from_the_fifth_most_recent` |
| M8 | `client_bucket` toma la IP de `X-Forwarded-For` | `test_client_bucket_ignores_x_forwarded_for`, `test_the_pair_key_ignores_x_forwarded_for`, `test_x_forwarded_for_is_ignored` |
| M9 | `wait` anota | `test_wait_does_not_record`, `test_wait_is_none_without_history_and_below_the_limit` |
| M10a | `record_failure` guarda sin `timeout` | `test_record_failure_stores_newest_first_in_the_login_cache_for_the_window` |
| M10b | `record_failure` guarda con la mitad de la ventana | el mismo que M10a |
| M11 | `cache` devuelve `caches["default"]` | `test_record_failure_stores_newest_first_in_the_login_cache_for_the_window`, `test_record_failure_drops_the_entries_that_left_the_window`, `test_the_failure_limit_cache_is_resolved_at_each_use_and_follows_override_settings` |
| M12a | `wait` sin podar la ventana | `test_the_window_slides_and_the_entry_on_the_boundary_leaves` |
| M12b | `record_failure` sin podar la ventana | `test_record_failure_drops_the_entries_that_left_the_window` |
| M13 | `len > limit` en lugar de `>=` | `test_wait_with_exactly_the_limit_returns_the_wait`, `test_each_key_has_its_own_counter`, `test_the_window_slides_and_the_entry_on_the_boundary_leaves` |
| M14 | Otra sal | `test_the_key_hashes_a_single_normalization_of_the_raw_email` |
| M15 | `record_failure` añade al final del historial | `test_record_failure_stores_newest_first_in_the_login_cache_for_the_window`, `test_wait_with_exactly_the_limit_returns_the_wait`, `test_wait_with_seven_entries_counts_from_the_fifth_most_recent`, `test_the_window_slides_and_the_entry_on_the_boundary_leaves` |
| M16 | `cache` como atributo de clase, resuelto al importar | `test_record_failure_stores_newest_first_in_the_login_cache_for_the_window`, `test_the_failure_limit_cache_is_resolved_at_each_use_and_follows_override_settings` |

### Desviaciones y añadidos respecto del plan
- **`chr(0xA8)` en lugar del escape**: `test_the_key_hashes_a_single_normalization_of_the_raw_email` construye el email con `chr(0xA8) + "ana@x.es"` y no con `"\u00a8ana@x.es"`. Al escribir el fichero, el escape se convirtió en el carácter literal y la comprobación de la tarea (ningún fichero de test con U+00A8) lo detectó. Construido con `chr`, ninguna herramienta puede convertirlo; el valor es el mismo y la mutación M4 sigue muriendo.
- **Test añadido de la `property`**: `test_the_failure_limit_cache_is_resolved_at_each_use_and_follows_override_settings`, como el de `LoginIpThrottle` en la T2: un `override_settings` de `CACHES` cambia el almacén que usa `LoginFailureLimit`. Fija la `property` de forma explícita, como en la T2.
- **Mutaciones añadidas**: M9 a M16 (la M13 y la M16, a petición de la revisión de la tarea).
- **Sal**: `LOGIN_PAIR_KEY_SALT = "rentradar.users.login_pair_key"`, con el valor literal en el test de la clave para que forme parte del contrato (M14).
- **Reloj**: `LoginFailureLimit.timer` es un atributo de clase como el de los throttles; los tests lo sustituyen con un fixture propio (`failure_clock`), porque el `clock` de la T2 solo parchea `LoginIpThrottle`.

## T4. Comprobación de credenciales
Fecha: 2026-11-18 · Commit: `46595c9` (`feat`, con `apps/users/login.py`, `test_login_credentials.py` y el test de la señal en `test_logout_api.py`). Antes, en la documentación: `ce33b47` (premisa de `DEBUG`), `93963dd` (`CREDENTIALS_INVALID` y los ayudantes de sesión a la T5) y `dd89a6e` (U+00A8 con `chr(0xA8)` en la T4).

### Rojo, antes del código
- `apps/users/tests/test_login_credentials.py`: `1 error during collection`, `ImportError: cannot import name 'login' from 'apps.users'` (no existía el módulo).
- `test_logging_out_does_not_send_user_logged_out` (`test_logout_api.py`): `1 passed` al escribirlo. Es de caracterización: la salida no cambia en esta tarea, y su valor lo demuestra la M6.

### Verde, después del código
- `test_login_credentials.py` y `test_logout_api.py`: `86 passed` (37 nuevos de credenciales, los 48 que ya tenía la salida y el de la señal).
- Suite entera, con `test_migrations.py`, `test_production.py` y `test_settings.py`: `2324 passed in 47.14s`.
- `ruff check .`: `All checks passed!`. `ruff format --check .`: `148 files already formatted`. El primer `ruff check` dio un `E501` en un comentario de `login.py`, de 89 columnas; se acortó.
- Ningún fichero tocado contiene U+00A8 literal ni un nulo literal: comprobado con un script que busca los bytes sin escribir los caracteres. El email con U+00A8 se construye con `chr(0xA8)`.
- Desfase de `openapi.json`: la orden de la CI de la T2, en un contenedor suelto con `--no-deps -e DB_HOST=db-inexistente.invalid`, termina con `exit=0`, sin ninguna línea de `diff` y sin avisos de validación. La T4 no toca vistas, serializers ni URLs.
- Frontend, en el host: `npm run api:check` con `exit=0`; `npm test` (vitest) con `34 passed` ficheros y `1174 passed` tests; `npm run build` con `exit=0`. La T4 no toca el frontend.
- Ningún test mostró que Django se comporte distinto de lo que supone el plan: `MD5PasswordHasher.verify` y `make_password` pasan por `encode`, y el recuento es de un hash en cada caso previsto.

### Pruebas de mecanismo
Una sola ejecución sobre el código del commit `46595c9`, con las 13 mutaciones. Cada una se hizo sobre `login.py` o `views.py` con copia previa fuera del repo y fuera de `/tmp`, sha256 antes y después y restauración desde la copia; los hashes coincidieron (`login.py` `fdd1e6206faa…`, `views.py` `6e03be3ddda9…`). Se ejecutaron `test_login_credentials.py` y `test_logout_api.py`. Mueren las 13. M1 a M7 son las de la tarea; M8 a M13 se añaden en ella.

| Mutación | Cambio | Tests que la matan |
|---|---|---|
| M1 | Sin el tope de 128 puntos de código | `test_uncheckable_passwords_are_rejected_without_queries_hashes_or_signal[129-code-points]` |
| M2 | La contraseña `""` llega a `authenticate` | `test_uncheckable_passwords_are_rejected_without_queries_hashes_or_signal[empty]` |
| M3 | Consulta la cuenta antes y no llama a `authenticate` sin ella | `test_each_kind_of_wrong_credentials_computes_exactly_one_hash[unknown_email]`, `test_an_email_without_at_sign_is_looked_up`, `test_the_pair_key_and_the_lookup_receive_the_same_raw_email` (los dos casos), `test_the_error_report_hides_the_email_and_the_password` |
| M4 | Pasa a `authenticate` el email ya normalizado | `test_the_pair_key_and_the_lookup_receive_the_same_raw_email` (los dos casos), `test_user_login_failed_is_sent_once_with_the_raw_email_and_the_password_hidden` |
| M5 | Sin el rechazo del sustituto en el email | `test_unqueryable_emails_are_rejected_without_queries_hashes_or_signal[lone-surrogate]`, `test_no_content_of_the_email_or_password_raises[email-lone-surrogate]` |
| M6 | `django.contrib.auth.logout()` en `LogoutView` | `test_logging_out_does_not_send_user_logged_out` |
| M7 | Sin `@sensitive_variables` | `test_the_error_report_hides_the_email_and_the_password` |
| M8 | Sin el rechazo del nulo en el email | `test_unqueryable_emails_are_rejected_without_queries_hashes_or_signal[null-character]`, `test_no_content_of_the_email_or_password_raises[email-null-inside]` |
| M9 | Rechaza el nulo en la contraseña | `test_a_correct_password_with_a_null_character_returns_the_account`, `test_any_other_password_is_checkable[only-null]` y `[null-inside]` |
| M10 | Tope con `<` en lugar de `<=` | `test_a_wrong_password_of_128_code_points_computes_one_hash`, `test_any_other_password_is_checkable[128-code-points]` |
| M11 | Sin `strip` al decidir si el email está vacío | `test_unqueryable_emails_are_rejected_without_queries_hashes_or_signal[blank]` |
| M12 | Acepta la contraseña con sustituto | `test_uncheckable_passwords_are_rejected_without_queries_hashes_or_signal[lone-surrogate]`, `test_no_content_of_the_email_or_password_raises[password-lone-surrogate]` |
| M13 | `@sensitive_variables("email")`, sin la contraseña | `test_the_error_report_hides_the_email_and_the_password` |

M3 no mata el test de `user_login_failed`: usa una cuenta que existe, así que el mutante también llama a `authenticate`. Mata el del informe de error porque, sin cuenta para el email con la marca, devuelve `None` antes de llegar al `authenticate` parcheado y no se lanza la excepción.

### Puntos de «Lo que esta lectura no cubre» resueltos en esta tarea
- `MD5PasswordHasher.verify` calcula el hash con `encode`: confirmado (recuento de hashes).
- `_clean_credentials` tapa la contraseña en `user_login_failed`: confirmado en la T4 (test de la señal); la T6 lo comprueba de nuevo sobre el endpoint.
- `flush()` no emite `user_logged_out`: confirmado (test de caracterización y M6). La parte de `user_logged_in` queda para la T5.
- `sensitive_variables`: tapa las variables solo con `DEBUG=False` (`ce33b47`); con `DEBUG=True`, la página técnica las muestra. Confirmado en `check_credentials`; la T6 lo comprueba en `LoginView.post`.

### Desviaciones y añadidos respecto del plan
- **Sin el test de declaración de `@sensitive_variables`**: en una función síncrona, Django pone el atributo `sensitive_variables` dentro del wrapper, al llamar a la función, no al decorarla (`django/views/decorators/debug.py`). Un test que lo leyera dependería del orden de los tests. El test del informe de error mata M7 y M13.
- **Premisa de `DEBUG` corregida (`ce33b47`)**: `SafeExceptionReporterFilter.is_active` devuelve `settings.DEBUG is False`, así que el filtro solo tapa las variables con `DEBUG=False`; con `DEBUG=True`, la página técnica las muestra. El test pone `DEBUG=False` y mira solo el marco de `check_credentials`; los marcos de dentro (el parche, el backend) pueden mostrar los valores, como recoge el plan en Riesgos.
- **`CREDENTIALS_INVALID` y los ayudantes de sesión a la T5 (`93963dd`)**: la constante la usa `LoginView`, y el tercer uso de `untouchable_session_store`, `stored_sessions` y `cross_origin_headers` llega con los tests del endpoint.
- **Añadido**: las mutaciones M8 a M13 y los casos de `is_queryable_email` e `is_checkable_password` que las matan (texto sin arroba, de 4000 caracteres o con U+00A8; contraseña con nulo o de 128 puntos de código).

### Nota para la T10
`user_login_failed` lleva el email crudo en `credentials` (Django solo tapa la contraseña). Hoy ningún receptor del proyecto se conecta a esa señal; ninguno debe registrar `credentials` en el log.

## T5. Endpoint de entrada (sin límites)
Fecha: 2026-11-18 · Commits: `924390b` (`untouchable_session_store`, `stored_sessions` y `cross_origin_headers` a `helpers.py`, sin cambiar casos), `969377c` (`feat`, con `CREDENTIALS_INVALID`, `LoginRequestSerializer`, `LoginErrorSerializer`, `LoginView`, `_open_session`, la ruta, los tests, `openapi.json` y `schema.gen.ts`) y `73ce3cf` (riesgo aceptado de la cookie de sesión con nulos).

### Traslado de los ayudantes de sesión (`924390b`)
- `test_register_api.py` y `test_logout_api.py` recogen los mismos 135 tests antes y después, con los mismos identificadores.
- Suite entera: `2324 passed`, como tras la T4. Ruff, desfase de `openapi.json` (`exit=0`, sin `diff`), `api:check`, vitest y build en verde.

### Rojo, antes del código
- `apps/users/tests/test_login_api.py`: `99 failed, 28 errors`. Los fallos son el 404 de `/api/v1/auth/login/` (`assert 404 == 400`, `assert 404 == 200`, `KeyError: 'sessionid'`…); los errores, del fixture que parchea `check_credentials` en `apps.users.views`, que aún no lo importaba.
- `test_auth_contract.py`: `1 error during collection`, `ImportError: cannot import name 'LoginErrorSerializer'`.
- `apps/core/tests/test_csrf_guard.py`: `1 error during collection`, `ImportError: cannot import name 'LoginView'`.

### Verde, después del código
- Los tres ficheros: `163 passed` (127 de `test_login_api.py`, los del contrato con 6 nuevos y dos casos ampliados, y la guarda con uno nuevo).
- Suite entera, con `test_migrations.py`, `test_production.py` y `test_settings.py`: `2460 passed` (136 nuevos).
- `ruff check .`: `All checks passed!`. `ruff format --check .`: `149 files already formatted`.
- Ningún fichero de test tocado contiene U+00A8 literal ni un nulo literal: el sustituto y la barra del escape octal se construyen con `chr()`, y los nulos van como escape.

### Contrato y frontend
- `openapi.json` regenerado con `spectacular --validate --fail-on-warn` (`exit=0`) y `schema.gen.ts` con `npm run api:gen`, en el mismo commit que la vista.
- Desfase de `openapi.json` tras regenerar: la orden de la CI, en un contenedor suelto con `--no-deps -e DB_HOST=db-inexistente.invalid`, termina con `exit=0` y sin ninguna línea de `diff`.
- Frontend, en el host: `npm run api:check` con `exit=0`; `npm test` (vitest) con `34 passed` ficheros y `1174 passed` tests; `npm run build` con `exit=0`. La T5 no toca código del frontend; solo regenera `schema.gen.ts`.

### Pruebas de mecanismo
Una sola ejecución sobre el código del commit `969377c`, con las 14 mutaciones. Cada una se hizo sobre `views.py`, `serializers.py` o `login.py` con copia previa fuera del repo y fuera de `/tmp`, sha256 antes y después y restauración desde la copia; los hashes coincidieron y son los de los ficheros del commit (`views.py` `8440673785d1…`, `serializers.py` `3d89df027969…`, `login.py` `e37e563c077c…`). Se ejecutaron `test_login_api.py`, `test_auth_contract.py` y `test_csrf_guard.py`. Mueren las 14. M1 a M6 son las de la tarea; M7 a M14 se añaden en ella.

| Mutación | Cambio | Tests que la matan |
|---|---|---|
| M1 | Otro código (`account_inactive`) para la cuenta desactivada | `test_every_wrong_credential_gets_the_same_answer[*-inactive-account]`, en los cuatro estados de cookie (además, los casos con nulo o sustituto en el email, porque el mutante consulta la BD con ellos) |
| M2 | Sin `flush()` en `_open_session` | `test_a_previous_session_is_replaced[anonymous]` y `[same-account]` |
| M3 | Lee `request.session` en la rama de fallo | `test_a_failed_login_touches_neither_the_session_nor_the_cookies[anonymous]` y `[another-account]` (sin sesión, Django no carga nada) |
| M4 | `LoginView` sin `CsrfEnforcedMixin` | los 12 casos de `test_without_a_valid_token_the_credentials_are_not_checked`, `test_a_foreign_origin_is_rejected_even_with_a_valid_token`, `test_the_body_is_not_read_before_the_csrf_check`, `test_errors_carry_only_their_planned_keys[csrf-failed]`, `test_no_answer_can_be_stored_by_a_cache[403]`, `test_no_answer_grants_cross_origin_access[403]` y `test_every_project_view_that_changes_state_has_the_explicit_csrf_check` |
| M5 | Sin `no-store` en el 200 | `test_a_valid_login_answers_200_with_only_the_stored_email`, `test_no_answer_can_be_stored_by_a_cache[200]` |
| M6 | `SessionUserSerializer` como `ModelSerializer` con todos los campos | `test_the_success_carries_only_the_email_even_for_a_staff_account`, `test_serializers_are_explicit_white_lists[SessionUserSerializer-fields0]`, `test_the_session_component_has_a_nullable_user_with_only_the_email` y cinco más de la entrada que comparan el cuerpo exacto |
| M7 | Devuelve el email recibido en lugar del guardado | `test_a_valid_login_answers_200_with_only_the_stored_email` |
| M8 | `login()` antes que `flush()` | los cuatro casos de `test_a_previous_session_is_replaced`, `test_the_new_session_belongs_to_the_account`, `test_who_am_i_returns_the_email_after_logging_in` y tres más |
| M9 | `max_bytes=LOGIN_MAX_BYTES + 1` | `test_a_body_of_4096_bytes_is_read_and_one_of_4097_is_too_large` |
| M10 | Sin `http_method_names` | los seis casos de `test_every_other_method_gets_405_with_allow_post`, `test_a_preflight_from_another_origin_gets_405_without_cross_origin_headers` |
| M11 | Otro `operation_id` | `test_the_login_is_a_post_with_its_operation_and_tag` |
| M12 | Sin `LOGIN_COOKIES` en los parámetros del esquema | `test_the_login_success_documents_the_cookies_it_sets` |
| M13 | Otro valor de `CREDENTIALS_INVALID` | los 60 casos de `test_every_wrong_credential_gets_the_same_answer` y `test_a_body_of_4096_bytes_is_read_and_one_of_4097_is_too_large` |
| M14 | `rotate_token(http_request)` en la rama de fallo | los tres casos de `test_a_failed_login_touches_neither_the_session_nor_the_cookies` |

### Cookie de sesión con nulos (Desviación 2 del plan)
- Con una cookie `sessionid` de 8 nulos escritos con escape octal y las credenciales correctas, la entrada responde 500: `_open_session` llama a `flush()`, que borra por esa clave (`django/contrib/sessions/backends/db.py`, `delete`), y PostgreSQL lo rechaza (`DataError: PostgreSQL text fields cannot contain NUL (0x00) bytes`). El test `test_a_session_cookie_with_null_characters_gives_a_server_error_on_success` fija el 500 y que no queda ninguna sesión.
- La salida (`POST /api/v1/auth/logout/`) y «quién soy» (`GET /api/v1/auth/session/`) de la 009 también dan 500 con esa cookie, sin credenciales: comprobado con un test temporal sobre la BD de test, creado y borrado en la misma orden.
- Riesgo aceptado en la spec (`73ce3cf`), con su corrección prevista: validar también el alfabeto de la clave de sesión.

### Puntos de «Lo que esta lectura no cubre» resueltos en esta tarea
- Cookies que escriben o borran `SessionMiddleware` y `CsrfViewMiddleware`: con las cookies bien formadas, un fallo no envía ningún `Set-Cookie`; con un `sessionid` de menos de 8 caracteres o una clave desconocida, la respuesta es idéntica para todas las causas de RF-2.
- Cookie `sessionid` con nulos por escape octal: confirmada la hipótesis (500 en `flush()`).
- drf-spectacular: `LoginRequest` y `LoginError` pasan `--fail-on-warn`.
- `update_last_login` es el único receptor de `user_logged_in` (`django/contrib/auth/apps.py:28`, sin otros en `apps/` ni `config/`); la entrada escribe `last_login`.

### Desviaciones y añadidos respecto del plan
- **`minLength: 1` en el contrato**: `LoginRequest` publica `email` y `password` obligatorios y nulables, y drf-spectacular añade `minLength: 1` porque `CharField` no admite cadena vacía, igual que en `RegistrationRequest`. El servidor acepta `""` y responde `credentials_invalid` (RF-2), lo que fijan los tests.
- **`@sensitive_variables("fields")` pasa a la T6**: entra en `LoginView.post` con su test (informe de error con `DEBUG=False`) y su mutación. En la T5, el cuerpo leído va directamente a `read_text_fields`, sin una variable propia.
- **M10 cambiada**: añadir `"get"` a `http_method_names` sin un manejador seguiría dando 405 con `Allow: POST`, y la mutación sobreviviría por construcción; se quita `http_method_names`, lo que deja pasar OPTIONS y el resto.
- **`test_a_failed_login_touches_neither_the_session_nor_the_cookies` reforzado**: con las cookies bien formadas, un fallo no envía ningún `Set-Cookie`, tampoco el de `csrftoken`; lo mata M14.
- **Añadido**: las mutaciones M7 a M14 y los casos de 4096 y 4097 bytes, sesión caducada, `last_login` e `is_active`/`next` ignorados.

### Nota para la T10
La /sdd-change de la 009 (validar también el alfabeto de la clave de sesión: 32 caracteres de [a-z0-9]) va a «Próximos pasos» de MEMORY.md, para hacerla al cerrar la 015.

## T6. Límites conectados al endpoint, orden y fugas
Fecha: 2026-11-18 · Commits: `f925eb6` (`assert_throttled` a `helpers.py`, sin cambiar casos) y `5b81f3b` (`feat`: `throttle_classes = [LoginIpThrottle]`, límite del par en `post` tras leer el cuerpo, `@sensitive_variables("fields")` y los tests).

### Traslado de `assert_throttled` (`f925eb6`)
- `test_throttling.py` y `test_login_throttling.py` importan la común; `test_register_api.py` la llama desde `assert_register_throttled`, que añade sus claves exactas (`{"code", "retry_after"}`) y `no-store`.
- `pytest --collect-only` de los tres ficheros: los mismos 220 identificadores antes y después (`diff` vacío).
- Suite entera: `2460 passed`, como tras la T5. Ruff, migraciones, desfase de `openapi.json` (`exit=0`, sin `diff`), `api:check`, vitest y build en verde.

### Rojo, antes del código
`apps/users/tests/test_login_api.py` sobre la vista de la T5: `48 failed, 143 passed`. Todos los fallos se deben a que falta el límite o `@sensitive_variables`:
- RF-3 (10): 200, 403 o 405 donde se espera 429 (`assert response.status_code == 429`); en la 21.ª entrada, la petición llega a `check_credentials`, que está prohibido, y da 500.
- RF-4 (13): 200 o 400 donde se espera 429; en los 5 fallos con la contraseña correcta, la petición llega a `check_credentials`, que está prohibido.
- RF-5 (6): la entrada con el límite superado llega a la sesión (`AssertionError: session.flush`).
- RF-6 (11): la condición previa de que los dos pares estén bloqueados falla (`assert None == 900`).
- Casos 429 añadidos a los tests de la T5 (6): `assert 200 == 429` y cuerpo `{'user'}` en lugar de `{'code', 'retry_after'}`.
- Fugas (2): sin ningún 429 en la secuencia (`At index 6 diff: 200 != 429`); `fields` visible en el informe de error (`{'email': 'zq7x.ana@correo.es', …} == '********************'`).

Pasan ya en rojo, porque sin límite también dan 200 o no anotan nada; son de caracterización respecto de la T5 y los valida su mutación:
- `test_a_success_is_not_counted_as_a_failure` (dos aciertos tras cuatro fallos): lo valida M1.
- `test_the_same_email_from_another_network_can_log_in` (`ipv4`, `ipv6-other-64`): lo valida M13.
- `test_no_rejection_before_the_credentials_records_a_failure` (13 casos): lo valida M7.

### Verde, después del código
- `test_login_api.py`: `191 passed` (los 127 de la T5, sin cambios, y 64 nuevos).
- Suite entera: `2524 passed` (64 nuevos). `test_migrations.py`: `1 passed`.
- `ruff check .`: `All checks passed!`. `ruff format --check .`: `149 files already formatted`.
- Ningún fichero tocado contiene U+00A8 literal ni un nulo literal: el nulo y el sustituto se construyen con `chr()`.

### Contrato y frontend
- `openapi.json` no cambia: la orden de la CI, en un contenedor suelto con `--no-deps -e DB_HOST=db-inexistente.invalid`, termina con `exit=0` y sin ninguna línea de `diff`. `@sensitive_variables` va debajo de `@extend_schema`, y la anotación del esquema se conserva.
- Frontend, en el host: `npm run api:check` con `exit=0`; `npm test` (vitest) con `34 passed` ficheros y `1174 passed` tests; `npm run build` con `exit=0`. La T6 no toca el frontend.

### Pruebas de mecanismo
Una sola ejecución sobre el código del commit `5b81f3b`, con las 13 mutaciones. Cada una se hizo sobre `views.py`, `api.py` o `throttling.py` con copia previa fuera del repo y fuera de `/tmp`, sha256 antes y después y restauración desde la copia. Los hashes coincidieron y son los de los ficheros del commit, comprobados con `git show 5b81f3b:<ruta> | sha256sum`: `views.py` `4be86758dde5…`, `api.py` `8102e9b69355…`, `throttling.py` `9d34caf3605e…`. Se ejecutaron `test_login_api.py`, `test_register_api.py`, `test_throttling.py` y `test_login_throttling.py`. Mueren las 13. M1 a M9 son las del plan (plan.md, línea 227) y M10 la añade tasks.md; M11 llega con @sensitive_variables, movido de la T5 a esta tarea; M13 repite la de la T3, cuyo plan ya citaba un test de la T6; M12 se añade en esta tarea.

| Mutación | Cambio | Tests que la matan |
|---|---|---|
| M1 | Anota el acierto como fallo | `test_a_success_is_not_counted_as_a_failure`, `test_a_success_does_not_reset_the_failures`, `test_the_twenty_first_login_from_one_ip_is_throttled_before_the_credentials`, `test_a_different_x_forwarded_for_on_each_request_does_not_avoid_the_ip_limit` y `test_no_answer_log_or_limit_store_contains_the_email_or_the_password` |
| M2 | Borra los fallos del par al acertar | `test_a_success_does_not_reset_the_failures` |
| M3 | Anota un fallo en cada rechazo del par | `test_pair_rejections_are_not_counted_as_failures` y `test_fifteen_minutes_after_the_first_failure_the_account_can_log_in` |
| M4 | Comprueba el par después de `check_credentials` | `test_five_failures_throttle_the_correct_password_without_checking_it` |
| M5 | `check_credentials(http_request, email=None, password=None)` en la primera línea de `post` | `test_five_failures_throttle_the_correct_password_without_checking_it`, los 8 casos de cuerpo mal formado de `test_with_the_pair_blocked_each_earlier_rejection_gets_its_own_error`, los 8 de `test_a_malformed_or_too_large_body_is_rejected_with_its_general_code`, `test_a_body_that_is_not_json_is_an_invalid_request` y `test_the_error_report_hides_the_body_fields_in_the_login_view` |
| M6 | El cuerpo se lee una vez en `initial` y el par se comprueba allí, antes de los límites y del CSRF; `post` usa esos campos sin comprobar el par | `test_a_pair_rejection_counts_towards_the_ip_limit`, `test_the_body_is_not_read_before_the_csrf_check`, `test_with_the_pair_blocked_each_earlier_rejection_gets_its_own_error[no-csrf-header]` y `[foreign-origin]` y `test_no_answer_log_or_limit_store_contains_the_email_or_the_password` |
| M7 | `handle_exception` propio que, salvo en un 429, anota un fallo con la clave del email ausente | los 13 casos de `test_no_rejection_before_the_credentials_records_a_failure`, los 11 de `test_with_the_pair_blocked_each_earlier_rejection_gets_its_own_error` y `test_failures_with_an_email_that_cannot_be_queried_count[absent]`, `[null]`, `[empty]` y `[blank]` |
| M8 | `throttle_classes = []` | `test_the_twenty_first_login_from_one_ip_is_throttled_before_the_credentials`, `test_a_pair_rejection_counts_towards_the_ip_limit`, los 7 casos de `test_once_the_ip_limit_is_reached_every_method_gets_429`, `test_a_different_x_forwarded_for_on_each_request_does_not_avoid_the_ip_limit`, los 3 casos `ip-*` de `test_a_throttled_login_touches_neither_the_session_nor_the_cookies`, `[429-ip-limit]` de los tests de caché y origen cruzado, `test_errors_carry_only_their_planned_keys[ip-throttled]` y `test_no_answer_log_or_limit_store_contains_the_email_or_the_password` |
| M9 | Sin `no-store` en los 429 (`api_exception_handler`, `api.py`) | `test_no_answer_can_be_stored_by_a_cache[429-ip-limit]` y `[429-pair-limit]` de la entrada; en el registro, `test_no_answer_can_be_stored_by_a_cache[429]`, los 7 casos de `test_ten_rejected_requests_use_up_the_quota_of_the_real_endpoint` y `test_ten_registrations_use_up_the_quota_and_the_eleventh_creates_nothing` |
| M10 | `client_bucket` toma la IP de `X-Forwarded-For` (`throttling.py`) | `test_a_different_x_forwarded_for_on_each_request_does_not_avoid_the_ip_limit` y `…_the_pair_limit`; en `test_login_throttling.py`, `test_x_forwarded_for_is_ignored`, `test_client_bucket_ignores_x_forwarded_for` y `test_the_pair_key_ignores_x_forwarded_for` |
| M11 | Sin `@sensitive_variables("fields")` | `test_the_error_report_hides_the_body_fields_in_the_login_view` |
| M12 | `logger.warning` con el email en la rama de fallo | `test_no_answer_log_or_limit_store_contains_the_email_or_the_password` |
| M13 | Clave del par sin la red (`throttling.py`) | `test_the_same_email_from_another_network_can_log_in[ipv4]` y `[ipv6-other-64]`; en `test_login_throttling.py`, `test_another_bucket_gives_another_key` y `test_the_key_hashes_a_single_normalization_of_the_raw_email`. `test_two_addresses_of_the_same_ipv6_64_share_the_pair_limit` no la mata, como se espera |

Con esta sección, `validation.md` reúne las mutaciones de T2 a T6: cada tarea tiene la suya en su apartado «Pruebas de mecanismo».

### Puntos de «Lo que esta lectura no cubre» resueltos en esta tarea
- `_clean_credentials` tapa la contraseña en `user_login_failed`: el receptor temporal recibe 5 señales, todas con `password` igual a `********************`.
- `sensitive_variables` en un método de una `APIView`: con `DEBUG=False`, el informe de error muestra `fields` tapado en el marco de `LoginView.post`, filtrado por función y por fichero (el `post` del cliente de pruebas lleva el cuerpo en claro).
- `retry_after` de los dos límites sobre el endpoint: 60 en el de IP y 900, 850 o 1 en el del par, según el historial.

### Desviaciones y añadidos respecto del plan
- **«Anotar el rechazo del par» (M3)**: no la mata «la espera no crece», porque con `history[4]` insertar el rechazo delante deja la misma espera. La matan `test_pair_rejections_are_not_counted_as_failures`, que sustituye a ese test, y `test_fifteen_minutes_after_the_first_failure_the_account_can_log_in`.
- **«`check_credentials` antes del cuerpo» (M5)**: los tests de RF-3 no pueden matarla, porque el 429 por IP se decide en `initial()`, antes de `post`. La matan los de RF-4 y RF-6.
- **«4 fallos, acierto y fallo»**: el 429 llega en la 7.ª petición, la siguiente al quinto fallo, no en el 6.º intento.
- **`no-store` de los 429**: lo pone `api_exception_handler` para todos los errores, no la vista; M9 muta `api.py`, y también la matan los tests del registro.
- **M4**: solo la mata `test_five_failures_throttle_the_correct_password_without_checking_it`. Con 7 fallos sembrados, la espera calculada tras `check_credentials` sigue siendo la de `history[4]` y el 429 se produce igual, antes de abrir la sesión.
- **M6 reescrita**: en una primera versión, `initial` consumía el cuerpo y `post` lo releía vacío, y además seguía comprobando el par; todas las peticiones anotaban con la clave del email ausente y `test_a_pair_rejection_counts_towards_the_ip_limit` pasaba por casualidad. La versión registrada lee el cuerpo una sola vez y quita la comprobación de `post`.
- **Fugas**: el cuerpo del 200 lleva el email de la cuenta por contrato, así que el test comprueba el cuerpo en los 20 rechazos, y las cabeceras y las cookies en todas las respuestas. El SQL con valores no llega al log porque la configuración real deja `django.db.backends` en INFO; el test lo fija como condición previa, igual que el del registro, en lugar de copiar `log_every_sql`.
- **Rechazos previos con el par bloqueado**: el test cubre los 8 cuerpos mal formados, además de sin cabecera CSRF, origen ajeno (403 `csrf_failed`) y PUT (405 con `Allow: POST`), con `check_credentials` prohibido. Comprueba primero que los pares del email y del email ausente están bloqueados, y por eso falla en rojo.
- **Caracterización**: `test_a_success_is_not_counted_as_a_failure`, `test_the_same_email_from_another_network_can_log_in` y `test_no_rejection_before_the_credentials_records_a_failure` pasan sobre la vista de la T5; los validan M1, M13 y M7.
- **Reloj y ayudantes**: un solo `Clock`, autouse en `test_login_api.py`, sustituye el `timer` de `LoginIpThrottle` y de `LoginFailureLimit`, así que los 429 añadidos a los tests de la T5 no dependen de la hora real. `forbid_credential_checks` sale del fixture `credentials_never_checked` (tercer uso), sin cambiar su comportamiento.
- **Registro de comprobaciones**: va en un commit de documentación aparte del `feat`, no dentro de él.
- **Añadido**: la mutación M12 (email en un log).

## T7. Entrada en el cliente de sesión
Fecha: 2026-11-19 · Commits: `b630cf6` (`refactor`: `postWithin` y `retryOnceOnCsrf`, que pasan a usar el registro y la salida) y `23cd020` (`feat`: `LOGIN_URL`, `LoginOutcome`, `login()`, `interpretLogin`, `isCredentialsInvalid` y sus tests).

### Refactor (`b630cf6`)
- Solo cambia `frontend/src/api/session.ts`: `git diff` de `session.test.ts` vacío, así que los tests del registro y de la salida no cambian ni una línea.
- `session.test.ts`: `239 passed`, los mismos que antes. vitest entero: `34 passed` ficheros y `1174 passed` tests.
- `npm run build` con `exit=0`; la comprobación de tipos va dentro (`tsc -b && vite build`). `eslint` de `session.ts` y `npm run api:check` con `exit=0`.
- Backend, aunque no cambia: `2524 passed`, ruff en verde, migraciones (`makemigrations --check --dry-run` en un contenedor suelto: `No changes detected`) y desfase de `openapi.json` (`exit=0`, sin `diff`).

### Rojo, antes del código
- `session.test.ts` con los tests nuevos: `74 failed | 239 passed (313)`. Todos los fallos están en los bloques `login:` y su único error es `TypeError: client.login is not a function`.
- Test añadido después (429 con otro `code`, dos casos), ejecutado con su filtro: `2 failed` con el mismo error; los dos casos del registro con ese nombre, `2 passed`.
- En total, 76 tests nuevos fallan solo porque `login` no existe; los 239 anteriores siguen en verde.

### Verde, después del código (`23cd020`)
- `session.test.ts`: `315 passed` (239 y 76 nuevos), con la misma sha256 antes y después de escribir `login()`. vitest entero: `34 passed` ficheros y `1250 passed` tests.
- `npm run build` con `exit=0`; `eslint` de `session.ts` y `session.test.ts` y `npm run api:check` con `exit=0`.
- Backend, aunque no cambia: `2524 passed`. `ruff check .`: `All checks passed!`; `ruff format --check .`: `149 files already formatted`. Migraciones: `No changes detected`. Desfase de `openapi.json`: `exit=0`, sin ninguna línea de `diff`.

### Pruebas de mecanismo
No aplica (plan).

### Desviaciones y añadidos respecto del plan
- **Firma de `postWithin`**: `postWithin(url, interpret, body?)` en lugar de `postWithin(url, body?)`, porque el intérprete lee el cuerpo dentro de los 10 s, como ya hacían el registro y la salida. Corregido en el plan y en las tareas en `d454cc5`.
- **Refactor en un commit propio**: la extracción va en `b630cf6`, separada del `feat`, para que los tests del registro y de la salida la vigilen sola (`d454cc5`).
- **«Otra forma o código»** (`tasks.md:113` en `d454cc5`): se lee como el código dentro de `params`. Un 400 `invalid_fields` cuyo `params` no es exactamente `{"non_field": ["credentials_invalid"]}` da `failed("invalid")`; un 400 con otro `code` de primer nivel da `failed("request")`, como fija `plan.md:121` en `d454cc5` y como hace el registro.
- **Variantes de `credentials_invalid`**: nueve casos de `invalid_fields` que dan `failed("invalid")`: una clave de más junto a `non_field`, dos códigos en `non_field`, `non_field` con una lista vacía, otro código en `non_field`, el código en otro campo, `params` vacío, sin `params`, `non_field` como texto y el código en mayúsculas.
- **429 con otro `code`**: es `throttled` si `retry_after` es válido, como en el registro, porque la rama del 429 no mira el `code` (en `23cd020`, `session.ts:295-299` en el registro y `session.ts:341-345` en la entrada).
- **La salida tras entrar**: el test comprueba que la cookie leída tras entrar (`TOKEN_B`) es distinta de la de antes (`TOKEN_A`) y que la salida envía la nueva.
- **`retry_after` en dos sitios**: la comprobación del 429 es igual en el registro y en la entrada; son dos usos y se extrae en el tercero.
- **Registro de comprobaciones**: va en un commit de documentación aparte del `feat`.

## T8. Página `/login` y enlaces cruzados
Fecha: 2026-11-19 · Commits: `b9bc37a` (`feat`: lógica del formulario, funciones comunes de sesión y `loginForm.ts`) y `145de07` (`feat`: ruta `/login`, `LoginForm`, `LoginPage` y enlaces cruzados).

### Rojo del primer commit (`b9bc37a`)
- `sessionState.test.ts`, `loginForm.test.ts` y `registerForm.test.ts`: `19 failed | 120 passed (139)`.
- Los 19 fallos están en los bloques nuevos: 4 en `authenticatedResult`, 1 en `shouldLeaveAuthForm` y 14 en `settleUnexpected`, con `TypeError: … is not a function`. `loginForm.test.ts` no llega a cargar: `Cannot find module './loginForm' imported from src/login/loginForm.test.ts`.
- Los tests de las cuatro funciones que se sustituyen siguen en verde: `settleLogout` (8), `registrationResult` (2), `settleRegistration` (4) y `shouldLeaveRegister` (1).

### Verde del primer commit (`b9bc37a`)
- vitest entero: `35 passed` ficheros y `1285 passed` tests (1250 de la T7 − 15 borrados de las funciones sustituidas + 50 nuevos = 1285; los casos de los 15 están dentro de los 50). `loginForm.test.ts`: `31 passed`.
- `npm run build` con `exit=0`; eslint de los 9 ficheros tocados y `npm run api:check` con `exit=0`.
- Backend, aunque no cambia: `2524 passed`, ruff en verde, migraciones (`No changes detected`) y desfase de `openapi.json` (`exit=0`, sin `diff`).
- Un `grep` de `registrationResult`, `settleLogout`, `settleRegistration`, `shouldLeaveRegister` y `markRegistered` en `frontend/src` no da resultados.

### Rojo del segundo commit (`145de07`)
- `route.test.ts`, `LoginForm.test.ts` y `RegistrationForm.test.ts` (el filtro recoge también `loginForm.test.ts`, que pasa): `3 failed | 94 passed (97)`.
- `resolveRoute`: `expected 'notFound' to be 'login'` y `expected 'notFound' to be 'redirectToLogin'`. Enlace del registro: `expected '' to be undefined` (no existen ni el enlace ni su texto). `LoginForm.test.ts` no llega a cargar: `Cannot find module './LoginForm'`.
- `/login//`, `/LOGIN`, `/login/x`, `/logins`, `//login` y `/login.html` ya dan la página no encontrada: pasan en rojo y son de caracterización.

### Verde del segundo commit (`145de07`)
- vitest entero: `36 passed` ficheros y `1322 passed` tests: 1285 + 28 (`LoginForm.test.ts`) + 2 (rutas `/login` y `/login/`) + 6 (casos nuevos de página no encontrada) + 1 (enlace del registro) = 1322. `loginFormState.test.ts`: `31 passed`, los mismos de `b9bc37a`.
- `npm run build` con `exit=0`; eslint de los 12 ficheros tocados y `npm run api:check` con `exit=0`.
- Backend, aunque no cambia: `2524 passed`, ruff en verde, migraciones (`No changes detected`) y desfase de `openapi.json` (`exit=0`, sin `diff`).

### Pruebas de mecanismo
Una sola ejecución sobre el código del commit `145de07`, con la mutación del plan: la contraseña de `LoginForm` pasa a ser un campo controlado (`useState` en el componente, y `value` y `onChange` en el campo de `LoginForm.tsx:76` en `145de07`). Se hizo con copia previa fuera del repo y fuera de `/tmp`, sin `sed -i`, con sha256 antes y después y restauración desde la copia.

| Fichero | sha256 |
|---|---|
| `LoginForm.tsx` en `145de07` (`git show`), antes y después | `dc093c8c3d23c3f101bd24ce2feaa0b47c3fefa516eca6583447b90182434367` |
| `LoginForm.tsx` mutado | `d4cd58508c1e787d3dfc2c2a8e2c79ef014940c263ca9d40f04cc128e49db886` |

`LoginForm.test.ts`: `6 failed | 22 passed (28)`. Mueren con ella los 6 casos de «la contraseña nunca llega al HTML» (`LoginForm.test.ts:116` en `145de07`); no falla ningún otro test. Tras restaurar, `git status --short` sale vacío.

### Desviaciones y añadidos respecto del plan
- **Corrección de lint de un test ya aprobado**: en «lo que se registra no incluye el email ni la contraseña que lleva la llamada», el doble se tipa con `vi.fn<(sent: typeof credentials) => Promise<LoginOutcome>>(…)` en lugar de con un parámetro sin uso que eslint rechazaba (`sessionState.test.ts:264` en `b9bc37a`). El test comprueba lo mismo; es el único cambio en los tests después del rojo, aparte de la importación del renombrado.
- **Textos de `es.ts` en el commit que los usa**: `session.loggedIn` y `login.credentialsInvalid` en `b9bc37a`; `login.title`, `login.submit`, `login.submitting`, `login.toRegister` y `register.toLogin` en `145de07`, en lugar de todos en el primero.
- **Caso de `settleRegistration` sin sustituto exacto**: el test que comprobaba que `register` recibía las credenciales (borrado en `b9bc37a`) solo comprobaba que `settleRegistration` reenviaba sus argumentos. Cómo monta `RegisterPage` las credenciales nunca tuvo test unitario, y el envío real del registro y de la entrada se comprueba en el navegador en la T10. Sus demás casos pasan a `settleUnexpected`.
- **TS1149**: `loginForm.test.ts` y `LoginForm.test.ts` solo difieren en mayúsculas y `tsc` los rechaza, aunque vitest no lo detecta (riesgo ya recogido en MEMORY.md). El módulo de lógica se renombra dentro de `145de07` a `loginFormState.ts` y `loginFormState.test.ts`; en el test solo cambia la línea de importación. `plan.md` y `tasks.md` conservan los nombres anteriores.

### Decisión
- **Enlaces cruzados**: «¿No tienes cuenta? Regístrate» (`LoginForm.tsx:115` en `145de07`) y «¿Ya tienes cuenta? Entra» (`RegistrationForm.tsx:135` en `145de07`) son enlaces normales que recargan la página; el plan solo fija la navegación interna para la barra superior. Pasa a «Próximos pasos» en la T10.

### Nota para la T10
- Comprobar en Chrome que el gestor de contraseñas ofrece guardar las credenciales al entrar y las rellena en `/login`, con el email marcado como `autocomplete="email"` y no como `"username"`.

## T9. Barra superior con «Entrar» y foco tras salir
Fecha: 2026-11-19 · Commit: `e4bc905` (`feat`: `topBarAction` con `"anonymous"`, «Entrar» y «Registrarse» en la barra sin sesión, y el foco tras salir a «Entrar»).

### Rojo, antes del código
- `sessionState.test.ts` y `TopBar.test.ts`: `5 failed | 62 passed (67)`, todos por el comportamiento anterior:
  - `topBarAction("anonymous")`: `expected 'register' to be 'anonymous'`.
  - `logoutResult` tras salir: el foco sigue en `"register"` (`expected { status: 'anonymous', …(3) } to deeply equal { status: 'anonymous', …(3) }`).
  - Barra sin sesión (3): no pinta «Entrar» (`expected '' to match /href="\/login"/`), ni el grupo con los dos enlaces (`expected -1 to be greater than -1`), ni sus clases `btn` (`expected [ '' ] to include 'btn'`).

### Verde, después del código (`e4bc905`)
- `sessionState.test.ts` y `TopBar.test.ts`: `67 passed`. vitest entero: `36 passed` ficheros y `1324 passed` tests: 1322 de la T8 + 2, porque el test de «Registrarse» sin sesión se sustituye por tres (enlaces y clases; orden y grupo; 44 px).
- El test comprueba la clase `btn` en «Entrar» y «Registrarse»; los 44 px los fija la regla `.btn` de `buttons.css:6-7` en `e4bc905` (`min-width` y `min-height` en `2.75rem`) y se miden en el navegador en la T10.
- `npm run build` con `exit=0`; eslint de los 7 ficheros tocados y `npm run api:check` con `exit=0`.
- Backend, aunque no cambia: `2524 passed`, ruff en verde, migraciones (`No changes detected`) y desfase de `openapi.json` (`exit=0`, sin `diff`).
- Barra sin sesión: grupo `flex items-center gap-2` con «Entrar» (secundario) y «Registrarse» (principal), en `TopBar.tsx:36-43` en `e4bc905`. Foco tras salir: `focus: "login"` en `sessionState.ts:67` y `loginRef` en `AppShell.tsx:40`, en `e4bc905`. Ya no queda `registerRef`.

### Pruebas de mecanismo
No aplica (interfaz; plan).

### Desviaciones y añadidos respecto del plan
- Ninguna.
