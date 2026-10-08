from django.urls import path

from apps.dashboard.api.views import IndicateursVue

urlpatterns = [
    path("indicateurs/", IndicateursVue.as_view(), name="admin-indicateurs"),
]
