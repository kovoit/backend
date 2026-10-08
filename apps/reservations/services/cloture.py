"""Fin de trajet, clôture (confirmation ou automatique) et litiges."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import Conflit, DonneesInvalides
from apps.parametres.services import get_param
from apps.portefeuille import services as portefeuille
from apps.reservations.models import Reservation, StatutReservation
from apps.reservations.repository import reservation_repository
from apps.reservations.services.commun import (
    libelle_trajet,
    notifier_conducteur,
    notifier_passager,
    transitionner,
    verrouiller_pour_passager,
)

CREDITER_CONDUCTEUR = "crediter_conducteur"
REMBOURSER_PASSAGER = "rembourser_passager"


def terminer_reservations_du_trajet(trajet) -> None:
    """Trajet verrouillé. Les passagers montés passent « terminée » ; les demandes sont refusées."""
    if reservation_repository.du_trajet(trajet, [StatutReservation.ACCEPTEE]).exists():
        raise Conflit(
            "Saisissez le code de départ ou déclarez absents les passagers non montés.",
            code="PASSAGERS_EN_ATTENTE",
        )
    for reservation in reservation_repository.du_trajet(trajet, [StatutReservation.DEMANDEE]):
        reservation = reservation_repository.get_verrouillee(reservation.id)
        transitionner(reservation, StatutReservation.REFUSEE)
        portefeuille.debloquer(reservation)
    for reservation in reservation_repository.du_trajet(trajet, [StatutReservation.EN_COURS]):
        reservation = reservation_repository.get_verrouillee(reservation.id)
        transitionner(reservation, StatutReservation.TERMINEE)
        notifier_passager(
            reservation,
            "Trajet terminé",
            "Confirmez votre arrivée et notez votre conducteur dans l'application.",
        )


def _cloturer(reservation: Reservation) -> None:
    transitionner(reservation, StatutReservation.CLOTUREE)
    portefeuille.crediter_conducteur(reservation)


def confirmer_arrivee(passager, reservation_id) -> Reservation:
    with transaction.atomic():
        reservation = verrouiller_pour_passager(passager, reservation_id)
        if reservation.statut != StatutReservation.TERMINEE:
            raise Conflit(
                "Seul un trajet terminé peut être confirmé.", code="CONFIRMATION_IMPOSSIBLE"
            )
        _cloturer(reservation)
    notifier_conducteur(
        reservation,
        "Trajet clôturé",
        f"{passager.prenom} a confirmé son arrivée ({libelle_trajet(reservation)}).",
    )
    return reservation_repository.get_by_id(reservation.id)


def cloturer_automatiquement() -> int:
    """Tâche planifiée : clôture les réservations terminées depuis `delai_confirmation_auto_h`."""
    limite = timezone.now() - timedelta(hours=get_param("delai_confirmation_auto_h"))
    nombre = 0
    for reservation in reservation_repository.a_cloturer(limite):
        with transaction.atomic():
            reservation = reservation_repository.get_verrouillee(reservation.id)
            if reservation.statut == StatutReservation.TERMINEE:
                _cloturer(reservation)
                nombre += 1
    return nombre


def passer_en_litige(reservation: Reservation) -> None:
    """Réservation verrouillée et « terminée » : le montant reste gelé jusqu'à la décision."""
    transitionner(reservation, StatutReservation.LITIGE)


def trancher_litige(reservation_id, decision: str) -> Reservation:
    if decision not in (CREDITER_CONDUCTEUR, REMBOURSER_PASSAGER):
        raise DonneesInvalides("Décision de litige inconnue.", code="DECISION_INVALIDE")
    reservation = reservation_repository.get_verrouillee(reservation_id)
    transitionner(reservation, StatutReservation.CLOTUREE)
    if decision == CREDITER_CONDUCTEUR:
        portefeuille.crediter_conducteur(reservation)
    else:
        portefeuille.rembourser(reservation)
    return reservation
