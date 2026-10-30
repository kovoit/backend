"""Connexion à l'application par e-mail + mot de passe (F-072, D-73, D-74).

`authenticate` hache le mot de passe même pour une adresse inconnue (temps constant) et refuse
les comptes désactivés ou sans mot de passe utilisable : même 401 dans tous ces cas. Un compte
suspendu se connecte (alerte COMPTE_SUSPENDU du bloc `etat`) ; un admin aussi, en `canal` =
mobile (il n'ouvre pas le back-office avec ces jetons, D-71).
"""

from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.db import transaction

from apps.accounts.models import ObjetCode
from apps.accounts.services.codes_email import envoyer_code, normaliser_email, peut_envoyer
from apps.accounts.services.connexion_admin import IdentifiantsInvalides
from apps.accounts.services.jetons import emettre_jetons
from apps.audit.models import Canal
from apps.audit.services import journaliser
from apps.core.exceptions import ActionInterdite


class EmailNonVerifie(ActionInterdite):
    code = "EMAIL_NON_VERIFIE"
    message = "Adresse e-mail pas encore vérifiée : saisissez le code reçu par e-mail."


def connecter(email: str, mot_de_passe: str) -> dict:
    email = normaliser_email(email)
    utilisateur = authenticate(username=email, password=mot_de_passe)
    if utilisateur is None:
        raise IdentifiantsInvalides()
    if not utilisateur.email_verifie:
        # Nouveau code hors délai de renvoi et sous le plafond ; sinon même 403 sans envoi
        if peut_envoyer(email, ObjetCode.VERIFICATION_EMAIL):
            envoyer_code(email, ObjetCode.VERIFICATION_EMAIL)
        raise EmailNonVerifie()
    with transaction.atomic():
        update_last_login(None, utilisateur)
        journaliser("session.connecter", ressource=utilisateur, acteur=utilisateur)
    return {"utilisateur": utilisateur, "nouveau_compte": False} | emettre_jetons(
        utilisateur, Canal.MOBILE
    )
