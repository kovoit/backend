"""Suspension et réactivation des comptes (manuelle par l'admin ou automatique)."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import StatutCompte, User
from apps.accounts.repository import user_repository
from apps.notifications.services import notifier


def suspendre(utilisateur: User, jours: int | None = None) -> User:
    """Suspend le compte et annule ses engagements à venir (réservations et trajets)."""
    from apps.reservations.services import annuler_engagements_a_venir

    jusqu_au = timezone.now() + timedelta(days=jours) if jours else None
    with transaction.atomic():
        utilisateur = user_repository.update(
            utilisateur, statut_compte=StatutCompte.SUSPENDU, suspendu_jusqu_au=jusqu_au
        )
        annuler_engagements_a_venir(utilisateur)

    duree = f"jusqu'au {timezone.localtime(jusqu_au):%d/%m/%Y %H:%M}" if jusqu_au else ""
    notifier(
        utilisateur,
        "Compte suspendu",
        f"Votre compte est suspendu {duree}. Vos réservations et trajets à venir sont annulés.",
    )
    return utilisateur


def reactiver(utilisateur: User) -> User:
    utilisateur = user_repository.update(
        utilisateur, statut_compte=StatutCompte.ACTIF, suspendu_jusqu_au=None
    )
    notifier(utilisateur, "Compte réactivé", "Votre compte Kovoit est de nouveau actif.")
    return utilisateur


def reactiver_suspensions_expirees() -> int:
    expires = list(user_repository.suspensions_expirees(timezone.now()))
    for utilisateur in expires:
        reactiver(utilisateur)
    return len(expires)
