from django.urls import path

from apps.kyc.api import views

urlpatterns = [
    path("kyc/", views.MesDossiersVue.as_view(), name="kyc"),
    path("kyc/<str:type_dossier>/pieces/", views.PieceVue.as_view(), name="kyc-pieces"),
    path("kyc/<str:type_dossier>/soumettre/", views.SoumettreVue.as_view(), name="kyc-soumettre"),
]
