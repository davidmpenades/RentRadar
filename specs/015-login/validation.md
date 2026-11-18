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
