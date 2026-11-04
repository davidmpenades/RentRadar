from django.urls import path

from apps.users.views import CurrentSessionView, LogoutView, RegisterView

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/session/", CurrentSessionView.as_view(), name="auth-session"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
]
