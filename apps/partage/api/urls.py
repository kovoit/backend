from django.urls import path

from apps.partage.api.views import ConsulterLienVue, CreerLienVue

urlpatterns = [
    path("reservations/<uuid:pk>/partage/", CreerLienVue.as_view(), name="partage-creer"),
    path("partage/<str:jeton>/", ConsulterLienVue.as_view(), name="partage-consulter"),
]
