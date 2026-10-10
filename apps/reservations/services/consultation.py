from apps.core.exceptions import RessourceIntrouvable
from apps.reservations.models import Reservation
from apps.reservations.repository import reservation_repository
from apps.trajets.services import get_trajet_du_conducteur


def mes_reservations(passager, statut: str | None = None):
    reservations = reservation_repository.de_passager(passager)
    return reservations.filter(statut=statut) if statut else reservations


def get_reservation(utilisateur, reservation_id) -> Reservation:
    """Visible uniquement par le passager ou le conducteur du trajet."""
    reservation = reservation_repository.get_by_id(reservation_id)
    if utilisateur.id not in (reservation.passager_id, reservation.trajet.conducteur_id):
        raise RessourceIntrouvable("Réservation introuvable.")
    return reservation


def reservations_du_trajet(conducteur, trajet_id, statut: str | None = None):
    trajet = get_trajet_du_conducteur(conducteur, trajet_id)
    return reservation_repository.du_trajet(trajet, [statut] if statut else None)


def reservations_du_trajet_admin(trajet):
    """Back-office : toutes les réservations du trajet, quel que soit leur statut."""
    return reservation_repository.du_trajet(trajet)


def lister_reservations(statut: str | None = None, recherche: str | None = None, trajet_id=None):
    return reservation_repository.lister(statut, recherche, trajet_id)


def get_reservation_admin(reservation_id) -> Reservation:
    return reservation_repository.get_by_id(reservation_id)
