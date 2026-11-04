from rest_framework.authentication import SessionAuthentication

from apps.core.tests.csrf_views import PostOnlyView
from apps.users.throttling import RegistrationThrottle


class ThrottledPostView(PostOnlyView):
    throttle_classes = [RegistrationThrottle]


class ThrottledSessionView(ThrottledPostView):
    # Con autenticación por sesión, el usuario de la petición sí puede estar autenticado
    authentication_classes = [SessionAuthentication]
