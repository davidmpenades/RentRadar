from django.core.asgi import get_asgi_application

from config.env import configure_settings_module

configure_settings_module()
application = get_asgi_application()
