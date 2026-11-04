from ipaddress import IPv4Address, IPv6Address, ip_address, ip_network

from rest_framework.throttling import SimpleRateThrottle

UNKNOWN_BUCKET = "unknown"
IPV6_PREFIX = 64


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
