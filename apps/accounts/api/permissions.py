from rest_framework.permissions import BasePermission, IsAdminUser, IsAuthenticated

from apps.accounts import roles
from apps.accounts.roles import roles_de
from apps.accounts.services import est_suspendu
from apps.audit.contexte import CLAIM_CANAL
from apps.audit.models import Canal


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


class CanalWeb(BasePermission):
    """Jeton émis par la connexion au back-office (claim signé `canal` = web, D-71) : un admin
    connecté depuis l'application (canal mobile) n'ouvre pas les routes d'administration."""

    message = "Connectez-vous au back-office pour accéder à cette partie de Kovoit."
    code = "canal_web_requis"

    def has_permission(self, request, view) -> bool:
        jeton = request.auth
        return hasattr(jeton, "get") and jeton.get(CLAIM_CANAL) == Canal.WEB


class _Role(BasePermission):
    role = ""
    message = "Votre rôle d'administrateur ne donne pas accès à cette partie du back-office."
    code = "role_admin_insuffisant"

    def has_permission(self, request, view) -> bool:
        return self.role in roles_de(request.user)


def _role(nom: str) -> type[BasePermission]:
    return type(f"Role{nom.capitalize()}", (_Role,), {"role": nom})


CONNECTE = [IsAuthenticated, EmailVerifie]
# Tout administrateur (tableau de bord, consultation des paramètres, son profil), connecté
# par le back-office ; un non-admin reçoit ACCES_REFUSE avant CANAL_WEB_REQUIS
ADMIN = [IsAuthenticated, IsAdminUser, CanalWeb]
# Par domaine (voir apps/accounts/roles.py) : un admin sans rôle n'a que ADMIN
# (tableau de bord, lecture des paramètres)
ADMIN_MODERATION = [*ADMIN, _role(roles.MODERATION)]
ADMIN_FINANCE = [*ADMIN, _role(roles.FINANCE)]
ADMIN_AUDIT = [*ADMIN, _role(roles.AUDIT)]
ADMIN_PARAMETRES = [*ADMIN, _role(roles.PARAMETRES)]
