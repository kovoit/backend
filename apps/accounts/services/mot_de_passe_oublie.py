"""« Mot de passe oublié » de l'application, par code e-mail (F-073, D-69, D-71, D-77).

Aucun code pour une adresse inconnue, un compte désactivé ou un administrateur (`is_staff`,
qui passe par le lien du back-office) : la réponse est la même. Un compte créé sans mot de
passe (ancienne connexion par code) fixe ainsi son premier mot de passe (D-69).
"""

from django.db import transaction

from apps.accounts.models import ObjetCode, User
from apps.accounts.repository import user_repository
from apps.accounts.services.codes_email import (
    CodeOtpInvalide,
    code_envoye,
    consommer_code,
    envoyer_code,
    normaliser_email,
    verifier_limites,
)
from apps.accounts.services.mot_de_passe import valider_mot_de_passe
from apps.audit.services import journaliser

OBJET = ObjetCode.REINITIALISATION


def _compte_eligible(email: str) -> User | None:
    utilisateur = user_repository.get_par_email(email)
    if utilisateur is None or not utilisateur.is_active or utilisateur.is_staff:
        return None
    return utilisateur


def demander_code_reinitialisation(email: str) -> dict:
    email = normaliser_email(email)
    utilisateur = _compte_eligible(email)
    if utilisateur is not None:
        verifier_limites(email, OBJET)
        envoyer_code(
            email, OBJET, action="session.demander_reinitialisation", utilisateur=utilisateur
        )
    return code_envoye(email)


def reinitialiser_par_code(email: str, code: str, mot_de_passe: str) -> None:
    """Le mot de passe est contrôlé avant le code : un refus MOT_DE_PASSE_FAIBLE laisse le code
    et l'ancien mot de passe valables. Succès : adresse vérifiée (le code le prouve, D-77) et
    toutes les sessions révoquées ; aucun jeton émis."""
    email = normaliser_email(email)
    utilisateur = _compte_eligible(email)
    valider_mot_de_passe(mot_de_passe, utilisateur or User(email=email))
    if utilisateur is None:
        raise CodeOtpInvalide()
    consommer_code(email, OBJET, code)
    with transaction.atomic():
        utilisateur = user_repository.get_for_update(utilisateur.pk)
        user_repository.changer_mot_de_passe(utilisateur, mot_de_passe, email_verifie=True)
        user_repository.revoquer_sessions(utilisateur)
        journaliser("session.reinitialiser_mot_de_passe", ressource=utilisateur, acteur=utilisateur)
