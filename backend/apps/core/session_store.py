import re

from django.contrib.sessions.backends import db


class SessionStore(db.SessionStore):
    def _validate_session_key(self, key):
        # La forma exacta de las claves que genera Django: 32 caracteres de a-z y 0-9
        return isinstance(key, str) and re.fullmatch(r"[a-z0-9]{32}", key) is not None
