from django.db import transaction
from django.utils import timezone

from apps.audit.services import journaliser
from apps.core.exceptions import DonneesInvalides
from apps.tarification.services import Devis, devis_trajet
from apps.trajets.models import Trajet
from apps.trajets.repository import point_repository, trajet_repository
from apps.vehicules.repository import vehicule_repository

POINTS_MIN, POINTS_MAX = 1, 3


def estimer(conducteur, *, vehicule_id, depart, arrivee, places: int) -> Devis:
    """Prix et détail du calcul AVANT publication (écran de publication du conducteur)."""
    vehicule = vehicule_repository.get_de(conducteur, vehicule_id)
    if not 1 <= places <= vehicule.nb_places - 1:
        raise DonneesInvalides(
            f"Ce véhicule permet au plus {vehicule.nb_places - 1} place(s) passager.",
            code="PLACES_INVALIDES",
        )
    return devis_trajet(vehicule, depart, arrivee, places)


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
    """Publie un trajet. Le prix par place est calculé par le backend (tarification), jamais
    reçu du conducteur, et figé avec l'instantané du calcul."""
    if depart_le <= timezone.now():
        raise DonneesInvalides("L'heure de départ doit être dans le futur.", code="DEPART_PASSE")
    if not POINTS_MIN <= len(points) <= POINTS_MAX:
        raise DonneesInvalides("Indiquez de 1 à 3 points de prise en charge.")
    # Itinéraire et prix calculés avant toute écriture (appel externe hors transaction)
    devis = estimer(
        conducteur,
        vehicule_id=vehicule_id,
        depart=(depart_lat, depart_lng),
        arrivee=(arrivee_lat, arrivee_lng),
        places=places,
    )
    vehicule = vehicule_repository.get_de(conducteur, vehicule_id)
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
            distance_km=devis.distance_km,
            duree_min=devis.duree_min,
            prix_place=devis.prix_place,
            tarification=devis.instantane(),
        )
        point_repository.creer_pour(trajet, points)
        journaliser(
            "trajet.publier",
            ressource=trajet,
            role="conducteur",
            details={
                "depart_le": depart_le,
                "places": places,
                "prix_place": trajet.prix_place,
                "distance_km": devis.distance_km,
                "duree_min": devis.duree_min,
                "cout_total": str(devis.cout_total),  # montant exact, pas de flottant
                "commission_place": devis.commission_place,
                "net_conducteur_place": devis.net_conducteur_place,
                "formule_version": devis.formule_version,
                "source_itineraire": devis.source_itineraire,
            },
        )
    return trajet_repository.get_by_id(trajet.id)
