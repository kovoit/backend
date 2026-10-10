from django.urls import path

from apps.dashboard.api.views import IndicateursVue, TableauDeBordVue

urlpatterns = [
    path("indicateurs/", IndicateursVue.as_view(), name="admin-indicateurs"),
    path("tableau-de-bord/", TableauDeBordVue.as_view(), name="admin-tableau-de-bord"),
]
