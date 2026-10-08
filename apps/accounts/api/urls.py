from django.urls import path

from apps.accounts.api import views

urlpatterns = [
    path("auth/otp/demander/", views.OtpDemandeVue.as_view(), name="otp-demander"),
    path("auth/otp/verifier/", views.OtpVerificationVue.as_view(), name="otp-verifier"),
    path("auth/jeton/rafraichir/", views.JetonRafraichirVue.as_view(), name="jeton-rafraichir"),
    path("auth/deconnexion/", views.DeconnexionVue.as_view(), name="deconnexion"),
    path("moi/", views.MoiVue.as_view(), name="moi"),
    path("moi/mode/", views.MoiModeVue.as_view(), name="moi-mode"),
]
