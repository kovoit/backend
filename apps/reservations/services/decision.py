"""Le conducteur accepte ou refuse une demande."""

from django.db import transaction
from django.utils import timezone

from apps.audit.services import journaliser
from apps.core.exceptions import Conflit
from apps.portefeuille import services as portefeuille
from apps.reservations.code_depart import nouveau_sel
from apps.reservations.models import Reservation, StatutReservation
from apps.reservations.repository import reservation_repository
from apps.reservations.services.commun import (
    libelle_trajet,
    notifier_passager,
    transitionner,
    verrouiller_pour_conducteur,
)
from apps.trajets.models import StatutTrajet
from apps.trajets.repository import trajet_repository
from apps.trajets.services import retirer_place


def _verifier_trajet_ouvert(trajet) -> None:
    """Acceptation sur un trajet encore ouvert et pas encore parti (complet : PLUS_DE_PLACE)."""
    if trajet.statut not in (StatutTrajet.PUBLIE, StatutTrajet.COMPLET):
        raise Conflit("Ce trajet n'accepte plus de passagers.", code="TRAJET_NON_OUVERT")
    if trajet.depart_le <= timezone.now():
        raise Conflit("L'heure de départ de ce trajet est passée.", code="DEPART_PASSE")


def accepter(conducteur, reservation_id) -> Reservation:
    with transaction.atomic():
        reservation = verrouiller_pour_conducteur(conducteur, reservation_id)
        # Verrou du trajet : deux acceptations simultanées ne peuvent pas prendre la même place
        trajet = trajet_repository.get_verrouille(reservation.trajet_id)
        _verifier_trajet_ouvert(trajet)
        transitionner(reservation, StatutReservation.ACCEPTEE, code_depart_sel=nouveau_sel())
        retirer_place(trajet)
        journaliser("reservation.accepter", ressource=reservation, role="conducteur")

    notifier_passager(
        reservation,
        "Réservation acceptée",
        f"Votre place est confirmée pour {libelle_trajet(reservation)}. "
        "Ouvrez l'application pour voir votre code de départ.",
    )
    return reservation_repository.get_by_id(reservation.id)


def refuser(conducteur, reservation_id) -> Reservation:
    with transaction.atomic():
        reservation = verrouiller_pour_conducteur(conducteur, reservation_id)
        transitionner(reservation, StatutReservation.REFUSEE)
        portefeuille.debloquer(reservation)
        journaliser("reservation.refuser", ressource=reservation, role="conducteur")

    notifier_passager(
        reservation,
        "Réservation refusée",
        f"Le conducteur n'a pas pu accepter votre demande pour {libelle_trajet(reservation)}.",
    )
    return reservation_repository.get_by_id(reservation.id)
