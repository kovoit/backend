from django.urls import path

from apps.lieux.api.views import LieuxVue

urlpatterns = [path("lieux/", LieuxVue.as_view(), name="lieux")]
