from django.urls import path

from apps.trajets.api.admin_views import TrajetAdminDetailVue, TrajetAdminListeVue

urlpatterns = [
    path("trajets/", TrajetAdminListeVue.as_view(), name="admin-trajets"),
    path("trajets/<uuid:pk>/", TrajetAdminDetailVue.as_view(), name="admin-trajet-detail"),
]
