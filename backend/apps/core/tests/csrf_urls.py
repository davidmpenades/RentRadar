from django.urls import path

from apps.core.tests import csrf_views

urlpatterns = [
    path("post-only/", csrf_views.PostOnlyView.as_view()),
    path("post-handler/", csrf_views.PostHandlerView.as_view()),
    path("get-and-post/", csrf_views.GetAndPostView.as_view()),
    path("throttled/", csrf_views.ThrottledView.as_view()),
]
