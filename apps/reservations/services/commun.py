"""Outils partagés par les services de réservation : accès par rôle et transitions."""

from django.utils import timezone

from apps.core.exceptions import RessourceIntrouvable
from apps.notifications.services import notifier
from apps.reservations.models import Reservation
from apps.reservations.repository import reservation_repository
from apps.reservations.transitions import verifier_transition

INTROUVABLE = "Réservation introuvable."


def verrouiller_pour_conducteur(conducteur, reservation_id) -> Reservation:
    """Réservation verrouillée d'un trajet de `conducteur`, sinon 404."""
    reservation = reservation_repository.get_verrouillee(reservation_id)
    if reservation.trajet.conducteur_id != conducteur.id:
        raise RessourceIntrouvable(INTROUVABLE)
    return reservation


def verrouiller_pour_passager(passager, reservation_id) -> Reservation:
    reservation = reservation_repository.get_verrouillee(reservation_id)
    if reservation.passager_id != passager.id:
        raise RessourceIntrouvable(INTROUVABLE)
    return reservation


def verrouiller_pour_participant(utilisateur, reservation_id) -> Reservation:
    reservation = reservation_repository.get_verrouillee(reservation_id)
    if utilisateur.id not in (reservation.passager_id, reservation.trajet.conducteur_id):
        raise RessourceIntrouvable(INTROUVABLE)
    return reservation


def transitionner(reservation: Reservation, statut: str, **champs) -> Reservation:
    verifier_transition(reservation.statut, statut)
    return reservation_repository.changer_statut(reservation, statut, timezone.now(), **champs)


def libelle_trajet(reservation: Reservation) -> str:
    trajet = reservation.trajet
    heure = timezone.localtime(trajet.depart_le)
    return f"{trajet.depart_libelle} → {trajet.arrivee_libelle} ({heure:%d/%m à %H:%M})"


def notifier_passager(reservation: Reservation, titre: str, message: str) -> None:
    notifier(reservation.passager, titre, message, {"reservation_id": str(reservation.id)})


def notifier_conducteur(reservation: Reservation, titre: str, message: str) -> None:
    notifier(reservation.trajet.conducteur, titre, message, {"reservation_id": str(reservation.id)})
