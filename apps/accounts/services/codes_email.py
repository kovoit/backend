"""Codes à 6 chiffres envoyés par e-mail, rattachés à un objet (D-77).

- Délai de renvoi (`otp_delai_renvoi_s`) compté **par objet** ; plafond horaire
  (`otp_max_par_heure`) commun à tous les envois vers l'adresse.
- Un nouveau code n'annule que les codes du même objet.
- Seul le hash est stocké ; le code clair ne part que dans l'e-mail, après la transaction.
"""

import secrets
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import ObjetCode
from apps.accounts.repository import otp_repository
from apps.audit.services import journaliser
from apps.core.exceptions import DonneesInvalides, TropDeRequetes
from apps.notifications.services import envoyer_email
from apps.parametres.services import get_param

SUJETS = {
    ObjetCode.VERIFICATION_EMAIL: "Kovoit — code de vérification de votre adresse e-mail",
    ObjetCode.REINITIALISATION: "Kovoit — code de réinitialisation du mot de passe",
}
INTRODUCTIONS = {
    ObjetCode.VERIFICATION_EMAIL: "Voici le code qui confirme votre adresse e-mail.",
    ObjetCode.REINITIALISATION: (
        "Voici le code qui permet de choisir un nouveau mot de passe. Si vous n'avez rien "
        "demandé, ignorez ce message : votre mot de passe actuel reste valable."
    ),
}


class CodeOtpInvalide(DonneesInvalides):
    code = "CODE_OTP_INVALIDE"
    message = "Code invalide ou expiré."


def normaliser_email(email: str) -> str:
    return email.strip().lower()


def code_envoye(email: str) -> dict:
    """Réponse commune des envois de code (`CODE_ENVOYE`)."""
    return {"email": email, "delai_renvoi_s": get_param("otp_delai_renvoi_s")}


def _blocage(email: str, objet: str) -> str | None:
    """Message du refus si un envoi est impossible maintenant, sinon None."""
    maintenant = timezone.now()
    dernier = otp_repository.dernier_envoye(email, objet)
    delai = get_param("otp_delai_renvoi_s")
    if dernier and (maintenant - dernier.cree_le).total_seconds() < delai:
        return f"Patientez {delai} secondes avant de demander un nouveau code."
    depuis = maintenant - timedelta(hours=1)
    if otp_repository.nombre_envoyes_depuis(email, depuis) >= get_param("otp_max_par_heure"):
        return "Trop de codes demandés. Réessayez dans une heure."
    return None


def verifier_limites(email: str, objet: str) -> None:
    """429 TROP_DE_REQUETES dans le délai de renvoi ou au plafond horaire."""
    message = _blocage(email, objet)
    if message:
        raise TropDeRequetes(message)


def peut_envoyer(email: str, objet: str) -> bool:
    return _blocage(email, objet) is None


def envoyer_code(
    email: str,
    objet: str,
    *,
    sujet: str | None = None,
    introduction: str | None = None,
    action: str = "",
    utilisateur=None,
) -> None:
    """Crée un code (le précédent du même objet est annulé) puis l'envoie par e-mail.

    `sujet`, `introduction` : textes propres à l'objet, sauf mention contraire.
    `action` : action d'audit journalisée dans la même transaction que le code.
    """
    code = f"{secrets.randbelow(1_000_000):06d}"
    validite = get_param("otp_validite_min")
    with transaction.atomic():
        otp_repository.invalider_actifs(email, objet)
        otp_repository.create(
            email=email,
            objet=objet,
            code_hash=make_password(code),
            expire_le=timezone.now() + timedelta(minutes=validite),
        )
        if action:
            journaliser(action, ressource=utilisateur, acteur=utilisateur)
    introduction = INTRODUCTIONS[objet] if introduction is None else introduction
    corps = (
        f"Votre code Kovoit : {code}\n\n"
        f"Il est valable {validite} minutes. Ne le communiquez à personne."
    )
    envoyer_email(email, sujet or SUJETS[objet], f"{introduction}\n\n{corps}".lstrip())


def consommer_code(email: str, objet: str, code: str) -> None:
    """Valide et consomme le dernier code actif de cet objet, sinon 400 CODE_OTP_INVALIDE.

    Un mauvais code compte un essai ; au dernier essai, le code est annulé.
    """
    with transaction.atomic():
        otp = otp_repository.dernier_actif_verrouille(email, objet, timezone.now())
        if otp is None:
            raise CodeOtpInvalide()
        valide = check_password(code, otp.code_hash)
        if valide:
            otp_repository.update(otp, utilise=True)
        else:
            essais = otp.essais + 1
            epuise = essais >= get_param("otp_max_essais")
            otp_repository.update(otp, essais=essais, utilise=epuise)
    # L'erreur est levée hors de la transaction pour que le compteur d'essais soit enregistré.
    if not valide:
        raise CodeOtpInvalide()
