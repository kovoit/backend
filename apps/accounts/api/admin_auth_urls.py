from django.urls import path

from apps.accounts.api import admin_auth_views as views
from apps.accounts.api import admin_mot_de_passe

urlpatterns = [
    path("connexion/", views.ConnexionAdminVue.as_view(), name="admin-connexion"),
    path("jeton/rafraichir/", views.RafraichirAdminVue.as_view(), name="admin-jeton-rafraichir"),
    path("deconnexion/", views.DeconnexionAdminVue.as_view(), name="admin-deconnexion"),
    path("moi/", views.MoiAdminVue.as_view(), name="admin-moi"),
    path(
        "mot-de-passe/oublie/",
        admin_mot_de_passe.MotDePasseOublieVue.as_view(),
        name="admin-mot-de-passe-oublie",
    ),
    path(
        "mot-de-passe/reinitialiser/",
        admin_mot_de_passe.ReinitialiserMotDePasseVue.as_view(),
        name="admin-mot-de-passe-reinitialiser",
    ),
]
