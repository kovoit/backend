"""Connexion par code OTP envoyé par email, puis émission des jetons JWT.

Flux historique de l'application (`auth/otp/*`), inchangé pour le client jusqu'à son retrait
(D-70). Il n'utilise que les codes `verification_email` : un code de réinitialisation du mot
de passe n'ouvre pas de session par ce chemin.
"""

from django.db import transaction

from apps.accounts.models import ObjetCode
from apps.accounts.repository import user_repository
from apps.accounts.services.codes_email import (
    consommer_code,
    envoyer_code,
    normaliser_email,
    verifier_limites,
)
from apps.accounts.services.jetons import emettre_jetons
from apps.audit.models import Canal
from apps.audit.services import journaliser
from apps.core.exceptions import ActionInterdite

OBJET = ObjetCode.VERIFICATION_EMAIL


class CompteDesactive(ActionInterdite):
    code = "COMPTE_DESACTIVE"
    message = "Ce compte est désactivé."


def demander_otp(email: str) -> None:
    """Envoie un code. Même réponse que le compte existe ou non (pas d'énumération)."""
    email = normaliser_email(email)
    verifier_limites(email, OBJET)
    envoyer_code(email, OBJET, sujet="Votre code de connexion Kovoit", introduction="")


def verifier_otp(email: str, code: str) -> dict:
    """Vérifie le code, crée le compte au premier passage et renvoie les jetons JWT."""
    email = normaliser_email(email)
    consommer_code(email, OBJET, code)

    with transaction.atomic():
        utilisateur, nouveau = user_repository.get_ou_creer(email)
        if nouveau:
            journaliser("compte.creer", ressource=utilisateur, acteur=utilisateur)
    if not utilisateur.is_active:
        raise CompteDesactive()
    with transaction.atomic():
        if not utilisateur.email_verifie:
            utilisateur = user_repository.update(utilisateur, email_verifie=True)
        journaliser("session.connecter", ressource=utilisateur, acteur=utilisateur)

    # Claim signé : le serveur sait que ce jeton vient de l'app mobile (journal d'audit)
    return {"utilisateur": utilisateur, "nouveau_compte": nouveau} | emettre_jetons(
        utilisateur, Canal.MOBILE
    )
