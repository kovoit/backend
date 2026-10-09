from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import ActionInterdite, Conflit
from apps.portefeuille import services as portefeuille
from apps.reservations.models import Reservation
from apps.reservations.repository import reservation_repository
from apps.reservations.services.commun import libelle_trajet, notifier_conducteur
from apps.routage.services import distance_route_km
from apps.tarification.services import frais_service
from apps.trajets.models import StatutTrajet
from apps.trajets.repository import point_repository, trajet_repository


def demander_place(
    passager,
    *,
    trajet_id,
    point_id,
    arrivee_lat: float,
    arrivee_lng: float,
    arrivee_libelle: str = "",
    moyen_paiement: str | None = None,
) -> Reservation:
    """Demande une place : le montant est bloqué sur le portefeuille (complément éventuel payé
    par Flooz ou Mixx). La place n'est retenue qu'à l'acceptation du conducteur."""
    with transaction.atomic():
        trajet = trajet_repository.get_verrouille(trajet_id)
        if trajet.conducteur_id == passager.id:
            raise ActionInterdite("Vous ne pouvez pas réserver votre propre trajet.")
        if trajet.statut != StatutTrajet.PUBLIE or trajet.places_restantes < 1:
            raise Conflit("Ce trajet n'accepte plus de réservation.", code="TRAJET_INDISPONIBLE")
        if trajet.depart_le <= timezone.now():
            raise Conflit("Ce trajet est déjà parti.", code="TRAJET_INDISPONIBLE")
        if reservation_repository.active_existe(trajet, passager):
            raise Conflit("Vous avez déjà une réservation sur ce trajet.", code="DEJA_RESERVE")
        point = point_repository.get_du_trajet(trajet, point_id)

        reservation = reservation_repository.create(
            trajet=trajet,
            passager=passager,
            point=point,
            arrivee_lat=arrivee_lat,
            arrivee_lng=arrivee_lng,
            arrivee_libelle=arrivee_libelle,
            distance_km=distance_route_km((point.lat, point.lng), (arrivee_lat, arrivee_lng)),
            prix=trajet.prix_place,
            frais_service=frais_service(),
        )
        complement = portefeuille.bloquer(reservation, moyen_paiement)
        if complement:
            reservation_repository.update(
                reservation, moyen_paiement=moyen_paiement, complement_paye=complement
            )

    notifier_conducteur(
        reservation,
        "Nouvelle demande de place",
        f"{passager.prenom} demande une place pour {libelle_trajet(reservation)}.",
    )
    return reservation_repository.get_by_id(reservation.id)
