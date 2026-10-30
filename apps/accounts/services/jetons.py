"""Émission et révocation des jetons JWT (application mobile et back-office)."""

from django.db import transaction
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.utils import get_md5_hash_password

from apps.accounts.models import User
from apps.audit.contexte import CLAIM_CANAL
from apps.audit.services import journaliser
from apps.core.exceptions import ActionInterdite, DonneesInvalides


class JetonAutreCompte(ActionInterdite):
    code = "JETON_AUTRE_COMPTE"
    message = "Ce jeton de session n'appartient pas à votre compte."


def emettre_jetons(utilisateur: User, canal: str) -> dict:
    """Couple access + refresh portant le claim signé `canal` (D-71).

    Le claim est posé **avant** l'enregistrement du refresh (`outstand`) : la copie gardée en
    base (OutstandingToken) le porte aussi. `RefreshToken.for_user` l'enregistrerait sans.
    """
    jeton = RefreshToken()
    jeton[api_settings.USER_ID_CLAIM] = str(getattr(utilisateur, api_settings.USER_ID_FIELD))
    if api_settings.CHECK_REVOKE_TOKEN:
        jeton[api_settings.REVOKE_TOKEN_CLAIM] = get_md5_hash_password(utilisateur.password)
    jeton[CLAIM_CANAL] = canal
    jeton.outstand()
    return {"access": str(jeton.access_token), "refresh": str(jeton)}


def deconnecter(utilisateur: User, refresh: str) -> None:
    """Révoque le refresh de cet appareil, seulement s'il appartient à l'utilisateur (D-76)."""
    try:
        jeton = RefreshToken(refresh)
    except TokenError as exc:
        raise DonneesInvalides(
            "Jeton de rafraîchissement invalide ou déjà utilisé.", code="JETON_INVALIDE"
        ) from exc
    if str(jeton.get(api_settings.USER_ID_CLAIM)) != str(utilisateur.pk):
        raise JetonAutreCompte()
    with transaction.atomic():
        jeton.blacklist()
        journaliser("session.deconnecter", ressource=utilisateur, acteur=utilisateur)
