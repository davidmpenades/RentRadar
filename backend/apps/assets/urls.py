from django.urls import path

from apps.assets.views import PublicAssetListView

urlpatterns = [
    path("public/assets/", PublicAssetListView.as_view(), name="public-asset-list"),
]
