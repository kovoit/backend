from rest_framework.permissions import BasePermission

from apps.kyc.models import TypeDossier
from apps.kyc.services import est_verifie, peut_publier


class KycPassagerVerifie(BasePermission):
    message = "Votre identité doit être vérifiée (KYC passager) pour réserver."
    code = "kyc_passager_requis"

    def has_permission(self, request, view) -> bool:
        return est_verifie(request.user, TypeDossier.PASSAGER)


class PeutPublier(BasePermission):
    message = "Un KYC conducteur vérifié et un véhicule déclaré sont nécessaires pour publier."
    code = "conducteur_non_habilite"

    def has_permission(self, request, view) -> bool:
        return peut_publier(request.user)
