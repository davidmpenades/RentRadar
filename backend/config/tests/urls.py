from django.urls import path

from config.tests import views

urlpatterns = [
    path("only-get/", views.only_get),
    path("explode/", views.explode),
    path("start-session/", views.start_session),
]
