from django.urls import path

from apps.accounts.api import auth_views, suppression, views

urlpatterns = [
    path("auth/inscription/", auth_views.InscriptionVue.as_view(), name="inscription"),
    path(
        "auth/inscription/verifier/",
        auth_views.InscriptionVerificationVue.as_view(),
        name="inscription-verifier",
    ),
    path(
        "auth/inscription/renvoyer-code/",
        auth_views.RenvoyerCodeVue.as_view(),
        name="inscription-renvoyer-code",
    ),
    path("auth/connexion/", auth_views.ConnexionVue.as_view(), name="connexion"),
    path(
        "auth/mot-de-passe/oublie/",
        auth_views.MotDePasseOublieVue.as_view(),
        name="mot-de-passe-oublie",
    ),
    path(
        "auth/mot-de-passe/reinitialiser/",
        auth_views.ReinitialiserParCodeVue.as_view(),
        name="mot-de-passe-reinitialiser",
    ),
    path("auth/otp/demander/", views.OtpDemandeVue.as_view(), name="otp-demander"),
    path("auth/otp/verifier/", views.OtpVerificationVue.as_view(), name="otp-verifier"),
    path("auth/jeton/rafraichir/", views.JetonRafraichirVue.as_view(), name="jeton-rafraichir"),
    path("auth/deconnexion/", views.DeconnexionVue.as_view(), name="deconnexion"),
    path("moi/", views.MoiVue.as_view(), name="moi"),
    path("moi/mode/", views.MoiModeVue.as_view(), name="moi-mode"),
    path("moi/supprimer/", suppression.SupprimerCompteVue.as_view(), name="moi-supprimer"),
]
