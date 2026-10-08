"""Connexion par code OTP envoyé par email, puis émission des jetons JWT."""

import secrets
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.repository import otp_repository, user_repository
from apps.core.exceptions import ActionInterdite, DonneesInvalides, TropDeRequetes
from apps.notifications.services import envoyer_email
from apps.parametres.services import get_param


class CodeOtpInvalide(DonneesInvalides):
    code = "CODE_OTP_INVALIDE"
    message = "Code invalide ou expiré."


class CompteDesactive(ActionInterdite):
    code = "COMPTE_DESACTIVE"
    message = "Ce compte est désactivé."


def _normaliser(email: str) -> str:
    return email.strip().lower()


def demander_otp(email: str) -> None:
    """Envoie un code. Même réponse que le compte existe ou non (pas d'énumération)."""
    email = _normaliser(email)
    maintenant = timezone.now()

    dernier = otp_repository.dernier_envoye(email)
    delai = get_param("otp_delai_renvoi_s")
    if dernier and (maintenant - dernier.cree_le).total_seconds() < delai:
        raise TropDeRequetes(f"Patientez {delai} secondes avant de demander un nouveau code.")
    depuis = maintenant - timedelta(hours=1)
    if otp_repository.nombre_envoyes_depuis(email, depuis) >= get_param("otp_max_par_heure"):
        raise TropDeRequetes("Trop de codes demandés. Réessayez dans une heure.")

    code = f"{secrets.randbelow(1_000_000):06d}"
    validite = get_param("otp_validite_min")
    with transaction.atomic():
        otp_repository.invalider_actifs(email)
        otp_repository.create(
            email=email,
            code_hash=make_password(code),
            expire_le=maintenant + timedelta(minutes=validite),
        )
    envoyer_email(
        email,
        "Votre code de connexion Kovoit",
        f"Votre code Kovoit : {code}\n\n"
        f"Il est valable {validite} minutes. Ne le communiquez à personne.",
    )


def verifier_otp(email: str, code: str) -> dict:
    """Vérifie le code, crée le compte au premier passage et renvoie les jetons JWT."""
    email = _normaliser(email)
    with transaction.atomic():
        otp = otp_repository.dernier_actif_verrouille(email, timezone.now())
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

    utilisateur, nouveau = user_repository.get_ou_creer(email)
    if not utilisateur.is_active:
        raise CompteDesactive()
    if not utilisateur.email_verifie:
        utilisateur = user_repository.update(utilisateur, email_verifie=True)

    jetons = RefreshToken.for_user(utilisateur)
    return {
        "utilisateur": utilisateur,
        "nouveau_compte": nouveau,
        "access": str(jetons.access_token),
        "refresh": str(jetons),
    }


def deconnecter(refresh: str) -> None:
    try:
        RefreshToken(refresh).blacklist()
    except TokenError as exc:
        raise DonneesInvalides(
            "Jeton de rafraîchissement invalide ou déjà utilisé.", code="JETON_INVALIDE"
        ) from exc
