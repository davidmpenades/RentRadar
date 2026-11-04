from django.urls import path

from apps.users.tests import throttle_views

urlpatterns = [
    path("register-like/", throttle_views.ThrottledPostView.as_view()),
    path("register-like-session/", throttle_views.ThrottledSessionView.as_view()),
]
