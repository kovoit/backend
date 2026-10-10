"""Connexion au back-office : email + mot de passe, réservée aux administrateurs (is_staff).

Le flux OTP (services/otp.py) reste celui de l'application mobile.
"""

from contextlib import suppress

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import update_last_login
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.exceptions import ActionInterdite, ErreurMetier


class IdentifiantsInvalides(ErreurMetier):
    code = "IDENTIFIANTS_INVALIDES"
    message = "Email ou mot de passe incorrect."
    http_status = 401


class CompteNonAdmin(ActionInterdite):
    code = "COMPTE_NON_ADMIN"
    message = "Accès réservé aux administrateurs Kovoit."


class SessionExpiree(ErreurMetier):
    code = "SESSION_EXPIREE"
    message = "Session invalide ou expirée. Reconnectez-vous."
    http_status = 401


def connecter_admin(email: str, mot_de_passe: str) -> dict:
    """Vérifie les identifiants et le rôle admin, puis émet les jetons JWT.

    `authenticate` hache le mot de passe même si le compte n'existe pas (temps constant)
    et refuse les comptes désactivés : même message dans tous ces cas, pas d'énumération.
    """
    utilisateur = authenticate(username=email.strip().lower(), password=mot_de_passe)
    if utilisateur is None:
        raise IdentifiantsInvalides()
    if not utilisateur.is_staff:
        raise CompteNonAdmin()
    update_last_login(None, utilisateur)
    jetons = RefreshToken.for_user(utilisateur)
    return {"utilisateur": utilisateur, "access": str(jetons.access_token), "refresh": str(jetons)}


def rafraichir_admin(refresh: str | None) -> dict:
    """Nouveau couple de jetons (rotation : l'ancien refresh est mis en liste noire)."""
    if not refresh:
        raise SessionExpiree()
    entree = TokenRefreshSerializer(data={"refresh": refresh})
    # Jeton expiré / révoqué (TokenError), compte désactivé (AuthenticationFailed) ou supprimé
    try:
        entree.is_valid(raise_exception=True)
    except (TokenError, AuthenticationFailed, get_user_model().DoesNotExist) as exc:
        raise SessionExpiree() from exc
    return entree.validated_data


def deconnecter_admin(refresh: str | None) -> None:
    """Révoque le refresh s'il est encore valide ; sans effet sinon (déconnexion idempotente)."""
    if not refresh:
        return
    with suppress(TokenError):
        RefreshToken(refresh).blacklist()
