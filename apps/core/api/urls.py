from django.urls import path

from apps.core.api.views import SanteVue

urlpatterns = [
    path("sante/", SanteVue.as_view(), name="sante"),
]
