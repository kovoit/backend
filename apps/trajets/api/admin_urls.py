from django.urls import path

from apps.trajets.api.views import TrajetAdminListeVue

urlpatterns = [
    path("trajets/", TrajetAdminListeVue.as_view(), name="admin-trajets"),
]
