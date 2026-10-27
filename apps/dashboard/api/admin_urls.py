from django.urls import path

from apps.dashboard.api.views import TableauDeBordVue

urlpatterns = [
    path("tableau-de-bord/", TableauDeBordVue.as_view(), name="admin-tableau-de-bord"),
]
