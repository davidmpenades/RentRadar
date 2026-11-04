from django.urls import path

from apps.users.views import RegisterView

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
]
