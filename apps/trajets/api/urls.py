from django.urls import path

from apps.trajets.api import views

urlpatterns = [
    path("trajets/", views.PublierVue.as_view(), name="trajets"),
    path("trajets/recherche/", views.RechercheVue.as_view(), name="trajets-recherche"),
    path("trajets/mes-trajets/", views.MesTrajetsVue.as_view(), name="mes-trajets"),
    path("trajets/<uuid:pk>/", views.TrajetDetailVue.as_view(), name="trajet-detail"),
    path("trajets/<uuid:pk>/position/", views.PositionVue.as_view(), name="trajet-position"),
    path("trajets/<uuid:pk>/terminer/", views.TerminerVue.as_view(), name="trajet-terminer"),
    path("trajets/<uuid:pk>/annuler/", views.AnnulerVue.as_view(), name="trajet-annuler"),
]
