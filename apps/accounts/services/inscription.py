"""Inscription dans l'application (F-070) et vérification de l'adresse e-mail (F-071).

Le compte est créé non vérifié, avec son mot de passe et les CGU acceptées (version et date,
D-78) ; un code `verification_email` part à l'adresse. Le bon code vérifie l'adresse et ouvre
la session (jetons `canal` = mobile).
"""

from django.contrib.auth.models import update_last_login
from django.db import IntegrityError, transaction
from django.utils import timezone

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
from apps.accounts.services.jetons import emettre_jetons
from apps.accounts.services.mot_de_passe import valider_mot_de_passe
from apps.audit.models import Canal
from apps.audit.services import journaliser
from apps.core.exceptions import Conflit
from apps.core.telephone import normaliser_telephone

OBJET = ObjetCode.VERIFICATION_EMAIL
MESSAGE_EMAIL_DEJA_UTILISE = "Un compte existe déjà avec cette adresse e-mail."


class EmailDejaUtilise(Conflit):
    code = "EMAIL_DEJA_UTILISE"
    message = f"{MESSAGE_EMAIL_DEJA_UTILISE} Connectez-vous."

    def __init__(self):
        super().__init__(erreurs={"email": [MESSAGE_EMAIL_DEJA_UTILISE]})


def inscrire(*, prenom: str, nom: str, email: str, telephone: str, mot_de_passe: str) -> dict:
    """Contrôles dans l'ordre du contrat : téléphone, mot de passe, adresse libre."""
    from apps.accounts.cgu import CGU_VERSION

    email = normaliser_email(email)
    telephone = normaliser_telephone(telephone)
    valider_mot_de_passe(mot_de_passe, User(email=email, prenom=prenom, nom=nom))
    if user_repository.email_existe(email):
        raise EmailDejaUtilise()
    try:
        with transaction.atomic():
            utilisateur = user_repository.creer(
                email,
                password=mot_de_passe,
                prenom=prenom,
                nom=nom,
                telephone=telephone,
                cgu_version=CGU_VERSION,
                cgu_acceptees_le=timezone.now(),
            )
            journaliser("compte.creer", ressource=utilisateur, acteur=utilisateur)
    except IntegrityError as exc:  # inscription simultanée de la même adresse
        raise EmailDejaUtilise() from exc
    envoyer_code(email, OBJET)
    return code_envoye(email)


def _compte_a_verifier(email: str) -> User | None:
    utilisateur = user_repository.get_par_email(email)
    if utilisateur is None or not utilisateur.is_active or utilisateur.email_verifie:
        return None
    return utilisateur


def verifier_email(email: str, code: str) -> dict:
    """Bon code → adresse vérifiée et session ouverte, sinon 400 CODE_OTP_INVALIDE."""
    email = normaliser_email(email)
    utilisateur = _compte_a_verifier(email)
    if utilisateur is None:
        raise CodeOtpInvalide()
    consommer_code(email, OBJET, code)
    with transaction.atomic():
        utilisateur = user_repository.get_for_update(utilisateur.pk)
        utilisateur = user_repository.update(utilisateur, email_verifie=True)
        update_last_login(None, utilisateur)
        journaliser("compte.verifier_email", ressource=utilisateur, acteur=utilisateur)
        journaliser("session.connecter", ressource=utilisateur, acteur=utilisateur)
    return {"utilisateur": utilisateur, "nouveau_compte": True} | emettre_jetons(
        utilisateur, Canal.MOBILE
    )


def renvoyer_code(email: str) -> dict:
    """Même réponse pour une adresse inconnue, vérifiée ou désactivée : rien n'est envoyé."""
    email = normaliser_email(email)
    if _compte_a_verifier(email) is not None:
        verifier_limites(email, OBJET)
        envoyer_code(email, OBJET)
    return code_envoye(email)
