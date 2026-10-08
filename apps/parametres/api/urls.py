from django.urls import path

from apps.parametres.api.views import ParametreDetailVue, ParametreListeVue

urlpatterns = [
    path("", ParametreListeVue.as_view(), name="parametres-liste"),
    path("<str:cle>/", ParametreDetailVue.as_view(), name="parametres-detail"),
]
