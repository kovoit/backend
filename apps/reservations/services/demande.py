from django.db import transaction
from django.utils import timezone

from apps.audit.services import journaliser
from apps.core.exceptions import ActionInterdite, Conflit
from apps.portefeuille import services as portefeuille
from apps.reservations.models import Reservation
from apps.reservations.repository import reservation_repository
from apps.reservations.services.commun import libelle_trajet, notifier_conducteur
from apps.routage.services import distance_route_km
from apps.tarification.services import repartition
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
    # Appel externe (OSRM, jusqu'à 5 s) AVANT le verrou du trajet : les autres demandes sur ce
    # trajet n'attendent pas le service de routage.
    point = point_repository.get_du_trajet(trajet_repository.get_by_id(trajet_id), point_id)
    distance = distance_route_km((point.lat, point.lng), (arrivee_lat, arrivee_lng))
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
        taux = (trajet.tarification.get("parametres") or {}).get("taux_commission_pct", "0")

        reservation = reservation_repository.create(
            trajet=trajet,
            passager=passager,
            point=point,
            arrivee_lat=arrivee_lat,
            arrivee_lng=arrivee_lng,
            arrivee_libelle=arrivee_libelle,
            distance_km=distance,
            prix=trajet.prix_place,
            # Taux figé à la publication (absent des trajets publiés avant la tarification : 0)
            taux_commission_pct=taux,
            **repartition(trajet.prix_place, taux),
        )
        complement = portefeuille.bloquer(reservation, moyen_paiement)
        if complement:
            reservation_repository.update(
                reservation, moyen_paiement=moyen_paiement, complement_paye=complement
            )
        journaliser(
            "reservation.demander",
            ressource=reservation,
            role="passager",
            details={
                "trajet_id": trajet.id,
                "montant_total": reservation.montant_total,
                "complement_paye": complement,
                "moyen_paiement": moyen_paiement if complement else None,
            },
        )

    notifier_conducteur(
        reservation,
        "Nouvelle demande de place",
        f"{passager.prenom} demande une place pour {libelle_trajet(reservation)}.",
    )
    return reservation_repository.get_by_id(reservation.id)
