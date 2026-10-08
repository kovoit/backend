from django.urls import path

from apps.vehicules.api.views import VehiculeDetailVue, VehiculeListeVue

urlpatterns = [
    path("vehicules/", VehiculeListeVue.as_view(), name="vehicules"),
    path("vehicules/<uuid:pk>/", VehiculeDetailVue.as_view(), name="vehicule-detail"),
]
