from django.urls import path

from apps.dashboard.api.views import EconomiesVue

urlpatterns = [
    path("moi/economies/", EconomiesVue.as_view(), name="moi-economies"),
]
