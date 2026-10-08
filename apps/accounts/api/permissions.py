from rest_framework.permissions import BasePermission, IsAdminUser, IsAuthenticated

from apps.accounts.services import est_suspendu


class EmailVerifie(BasePermission):
    message = "Vérifiez votre adresse email pour accéder à ce service."
    code = "email_non_verifie"

    def has_permission(self, request, view) -> bool:
        return bool(request.user.is_authenticated and request.user.email_verifie)


class CompteActif(BasePermission):
    message = "Votre compte est suspendu : action impossible."
    code = "compte_suspendu"

    def has_permission(self, request, view) -> bool:
        return not est_suspendu(request.user)


CONNECTE = [IsAuthenticated, EmailVerifie]
ADMIN = [IsAuthenticated, IsAdminUser]
