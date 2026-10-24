"""Mot de passe oublié du back-office (comptes administrateurs uniquement).

1. L'admin saisit son email : s'il s'agit d'un compte admin actif, un lien lui est envoyé.
   Même réponse dans tous les cas (aucune énumération des comptes).
2. Le lien (uid + jeton Django, valable PASSWORD_RESET_TIMEOUT) permet de choisir un nouveau
   mot de passe, soumis aux validateurs de Django. Le jeton devient invalide dès que le mot de
   passe change ; toutes les sessions ouvertes sont révoquées.
Le jeton n'est jamais journalisé ni renvoyé dans une réponse.
"""

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from apps.accounts.repository import user_repository
from apps.audit.services import journaliser
from apps.core.exceptions import DonneesInvalides
from apps.notifications.services import envoyer_email


class LienReinitialisationInvalide(DonneesInvalides):
    code = "LIEN_INVALIDE"
    message = "Ce lien n'est plus valable. Demandez un nouveau lien de réinitialisation."


def _admin_actif(email: str):
    utilisateur = user_repository.get_or_none(email=email.strip().lower())
    if utilisateur is None or not (utilisateur.is_active and utilisateur.is_staff):
        return None
    return utilisateur


def demander_reinitialisation(email: str) -> None:
    utilisateur = _admin_actif(email)
    if utilisateur is None:
        return  # même réponse : rien n'indique si le compte existe
    uid = urlsafe_base64_encode(force_bytes(utilisateur.pk))
    jeton = default_token_generator.make_token(utilisateur)
    lien = f"{settings.BACKOFFICE_URL.rstrip('/')}/reinitialiser?uid={uid}&jeton={jeton}"
    minutes = settings.PASSWORD_RESET_TIMEOUT // 60
    envoyer_email(
        utilisateur.email,
        "Kovoit — réinitialiser votre mot de passe",
        f"Bonjour {utilisateur.prenom},\n\n"
        f"Pour choisir un nouveau mot de passe du back-office Kovoit, ouvrez ce lien "
        f"(valable {minutes} minutes, une seule fois) :\n{lien}\n\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message : votre mot de "
        "passe actuel reste valable.",
    )
    journaliser("session.demander_reinitialisation", ressource=utilisateur, acteur=utilisateur)


def reinitialiser(uid: str, jeton: str, mot_de_passe: str) -> None:
    try:
        pk = force_str(urlsafe_base64_decode(uid))
    except (TypeError, ValueError) as exc:
        raise LienReinitialisationInvalide() from exc
    utilisateur = user_repository.get_or_none(pk=pk)
    if (
        utilisateur is None
        or not (utilisateur.is_active and utilisateur.is_staff)
        or not default_token_generator.check_token(utilisateur, jeton)
    ):
        raise LienReinitialisationInvalide()
    try:
        validate_password(mot_de_passe, utilisateur)
    except ValidationError as exc:
        raise DonneesInvalides(
            "Mot de passe trop faible.",
            code="MOT_DE_PASSE_FAIBLE",
            erreurs={"mot_de_passe": list(exc.messages)},
        ) from exc
    with transaction.atomic():
        user_repository.changer_mot_de_passe(utilisateur, mot_de_passe)
        user_repository.revoquer_sessions(utilisateur)
        journaliser("session.reinitialiser_mot_de_passe", ressource=utilisateur, acteur=utilisateur)
