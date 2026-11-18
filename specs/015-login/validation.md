# Validación — 015-login
Rama: `feature/015-login` · Entorno: backend en Docker Compose (contenedor suelto, sin BD), frontend en el host

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
