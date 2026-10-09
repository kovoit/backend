from rest_framework.permissions import BasePermission

from apps.kyc.models import TypeDossier
from apps.kyc.services import est_verifie, peut_publier


class KycPassagerVerifie(BasePermission):
    message = "Vérifiez votre identité (KYC) depuis votre profil pour pouvoir réserver."
    code = "kyc_passager_requis"

    def has_permission(self, request, view) -> bool:
        return est_verifie(request.user, TypeDossier.PASSAGER)


class PeutPublier(BasePermission):
    message = (
        "Pour proposer un trajet, faites vérifier votre KYC conducteur et déclarez votre "
        "véhicule depuis votre profil."
    )
    code = "conducteur_non_habilite"

    def has_permission(self, request, view) -> bool:
        return peut_publier(request.user)
