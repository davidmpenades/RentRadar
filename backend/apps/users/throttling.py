import time
from ipaddress import IPv4Address, IPv6Address, ip_address, ip_network
from math import ceil

from django.core.cache import caches
from django.utils.crypto import salted_hmac
from rest_framework.throttling import BaseThrottle, SimpleRateThrottle

from apps.users.models import User

UNKNOWN_BUCKET = "unknown"
IPV6_PREFIX = 64
LOGIN_CACHE_ALIAS = "login"
LOGIN_PAIR_KEY_SALT = "rentradar.users.login_pair_key"


def ip_bucket(address):
    # El texto recibido nunca es la clave: solo una dirección válida, normalizada
    if not isinstance(address, str):
        return UNKNOWN_BUCKET
    try:
        parsed = ip_address(address)
    except ValueError:
        return UNKNOWN_BUCKET
    if isinstance(parsed, IPv4Address):
        return str(parsed)
    if parsed.ipv4_mapped is not None:
        return str(parsed.ipv4_mapped)
    # Sin bits de host la red conserva la zona: se quita antes de truncar
    without_zone = IPv6Address(int(parsed))
    return str(ip_network((without_zone, IPV6_PREFIX), strict=False))


def client_bucket(request):
    # get_ident respeta NUM_PROXIES: sin proxy de confianza es REMOTE_ADDR
    return ip_bucket(BaseThrottle().get_ident(request))


def wait_seconds(history, now, limit, window):
    # history va de la más reciente a la más antigua y ya está podada
    # Desde la anotación que deja el recuento bajo el límite, no desde la más antigua
    return max(1, ceil(window - (now - history[limit - 1])))


class RegistrationThrottle(SimpleRateThrottle):
    # No hereda de AnonRateThrottle: quien ya tiene sesión también queda limitado
    rate = "10/hour"
    scope = "register"

    def get_cache_key(self, request, view):
        # Sin proxy de confianza, el identificador es REMOTE_ADDR
        return self.cache_format % {
            "scope": self.scope,
            "ident": ip_bucket(self.get_ident(request)),
        }


class LoginIpThrottle(SimpleRateThrottle):
    # Como el del registro, limita también a quien ya tiene sesión
    rate = "20/min"
    scope = "login_ip"

    @property
    def cache(self):
        # Se resuelve en cada uso: un atributo de clase se fijaría al importar
        return caches[LOGIN_CACHE_ALIAS]

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": client_bucket(request),
        }

    def wait(self):
        # El de DRF devuelve None con más anotaciones que el límite
        return wait_seconds(self.history, self.now, self.num_requests, self.duration)


def login_pair_key(bucket, email):
    # Una sola normalización del email crudo: normalize_email no es idempotente
    normalized = User.objects.normalize_email(email or "")
    # Un sustituto suelto no se codifica con el modo estricto
    value = normalized.encode("utf-8", errors="surrogatepass")
    digest = salted_hmac(LOGIN_PAIR_KEY_SALT, value, algorithm="sha256").hexdigest()
    return f"login_pair:{bucket}:{digest}"


class LoginFailureLimit:
    limit = 5
    window = 15 * 60
    timer = staticmethod(time.time)

    @property
    def cache(self):
        # Se resuelve en cada uso: un atributo de clase se fijaría al importar
        return caches[LOGIN_CACHE_ALIAS]

    def wait(self, key):
        now = self.timer()
        history = self._recent(key, now)
        if len(history) < self.limit:
            return None
        return wait_seconds(history, now, self.limit, self.window)

    def record_failure(self, key):
        now = self.timer()
        history = self._recent(key, now)
        history.insert(0, now)
        self.cache.set(key, history, self.window)

    def _recent(self, key, now):
        history = self.cache.get(key, [])
        return [mark for mark in history if mark > now - self.window]
