"""Suspension et réactivation des comptes (manuelle par l'admin ou automatique)."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import StatutCompte, User
from apps.accounts.repository import user_repository
from apps.accounts.services.profil import est_suspendu
from apps.core.exceptions import Conflit
from apps.notifications.services import notifier


class DejaSuspendu(Conflit):
    code = "DEJA_SUSPENDU"
    message = "Ce compte est déjà suspendu."


class DejaActif(Conflit):
    code = "DEJA_ACTIF"
    message = "Ce compte est déjà actif."


def suspendre(utilisateur: User, jours: int | None = None, motif: str = "") -> User:
    """Suspend le compte et annule ses engagements à venir (réservations et trajets)."""
    from apps.reservations.services import annuler_engagements_a_venir

    jusqu_au = timezone.now() + timedelta(days=jours) if jours else None
    with transaction.atomic():
        utilisateur = user_repository.update(
            utilisateur,
            statut_compte=StatutCompte.SUSPENDU,
            suspendu_jusqu_au=jusqu_au,
            motif_suspension=motif,
        )
        annuler_engagements_a_venir(utilisateur)

    duree = f"jusqu'au {timezone.localtime(jusqu_au):%d/%m/%Y %H:%M}" if jusqu_au else ""
    notifier(
        utilisateur,
        "Compte suspendu",
        f"Votre compte est suspendu {duree}. Vos réservations et trajets à venir sont annulés.",
    )
    return utilisateur


def suspendre_par_admin(utilisateur: User, motif: str, jours: int | None = None) -> dict:
    """Suspension manuelle : motif obligatoire ; renvoie le nombre de réservations annulées."""
    from apps.reservations.repository import reservation_repository

    if est_suspendu(utilisateur):
        raise DejaSuspendu()
    with transaction.atomic():
        annulees = reservation_repository.compter_engagements_a_venir(utilisateur, timezone.now())
        utilisateur = suspendre(utilisateur, jours, motif)
    return {"utilisateur": utilisateur, "reservations_annulees": annulees}


def reactiver(utilisateur: User) -> User:
    if utilisateur.statut_compte == StatutCompte.ACTIF:
        raise DejaActif()
    utilisateur = user_repository.update(
        utilisateur,
        statut_compte=StatutCompte.ACTIF,
        suspendu_jusqu_au=None,
        motif_suspension="",
    )
    notifier(utilisateur, "Compte réactivé", "Votre compte Kovoit est de nouveau actif.")
    return utilisateur


def reactiver_suspensions_expirees() -> int:
    expires = list(user_repository.suspensions_expirees(timezone.now()))
    for utilisateur in expires:
        reactiver(utilisateur)
    return len(expires)
