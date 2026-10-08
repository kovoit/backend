from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import DonneesInvalides
from apps.routage.services import distance_route_km
from apps.tarification.services import prix_par_place
from apps.trajets.models import Trajet
from apps.trajets.repository import point_repository, trajet_repository
from apps.vehicules.repository import vehicule_repository

POINTS_MIN, POINTS_MAX = 1, 3


def publier(
    conducteur,
    *,
    vehicule_id,
    depart_lat: float,
    depart_lng: float,
    depart_libelle: str,
    arrivee_lat: float,
    arrivee_lng: float,
    arrivee_libelle: str,
    depart_le,
    places: int,
    points: list[dict],
) -> Trajet:
    """Publie un trajet. Le prix par place est fixé par le backend, jamais par le conducteur."""
    vehicule = vehicule_repository.get_de(conducteur, vehicule_id)
    if depart_le <= timezone.now():
        raise DonneesInvalides("L'heure de départ doit être dans le futur.", code="DEPART_PASSE")
    if not 1 <= places <= vehicule.nb_places - 1:
        raise DonneesInvalides(
            f"Ce véhicule permet au plus {vehicule.nb_places - 1} place(s) passager.",
            code="PLACES_INVALIDES",
        )
    if not POINTS_MIN <= len(points) <= POINTS_MAX:
        raise DonneesInvalides("Indiquez de 1 à 3 points de prise en charge.")

    distance = distance_route_km((depart_lat, depart_lng), (arrivee_lat, arrivee_lng))
    with transaction.atomic():
        trajet = trajet_repository.create(
            conducteur=conducteur,
            vehicule=vehicule,
            depart_lat=depart_lat,
            depart_lng=depart_lng,
            depart_libelle=depart_libelle,
            arrivee_lat=arrivee_lat,
            arrivee_lng=arrivee_lng,
            arrivee_libelle=arrivee_libelle,
            depart_le=depart_le,
            places_total=places,
            places_restantes=places,
            distance_km=distance,
            prix_place=prix_par_place(distance),
        )
        point_repository.creer_pour(trajet, points)
    return trajet_repository.get_by_id(trajet.id)
