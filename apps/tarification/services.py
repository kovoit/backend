"""Tarification (PRD §7) : seul point d'entrée des autres apps pour le prix d'un trajet.

La formule est dans calcul.py (pure, testée seule) ; ce module y injecte les paramètres
administrables et l'itinéraire. Le prix est toujours calculé ici, jamais reçu du client.
"""

from decimal import Decimal

from apps.core.geo import distance_haversine_km
from apps.parametres.services import get_param
from apps.routage.providers import Point
from apps.routage.services import itineraire
from apps.tarification.calcul import (
    Devis,
    Parametres,
    calculer,
    part_du_trajet,
    prix_passager,
    repartir_paiement,
)
from apps.vehicules.models import TypeVehicule

__all__ = [
    "Devis",
    "devis_trajet",
    "parametres_pour",
    "prix_pour",
    "repartition",
    "repartir_paiement",
]


def _decimal(cle: str) -> Decimal:
    return Decimal(str(get_param(cle)))


def parametres_pour(vehicule) -> Parametres:
    """Paramètres courants pour ce véhicule : sa consommation si elle est connue, sinon la
    consommation de référence de son type (voiture ou moto)."""
    moto = vehicule.type_vehicule == TypeVehicule.MOTO
    propre = getattr(vehicule, "consommation_l_100km", None)
    if propre:
        consommation, source = Decimal(str(propre)), "vehicule"
    else:
        cle = "consommation_moto_l_100km" if moto else "consommation_voiture_l_100km"
        consommation, source = _decimal(cle), f"reference_{vehicule.type_vehicule}"
    return Parametres(
        prix_carburant_litre=_decimal("prix_carburant_litre"),
        consommation_l_100km=consommation,
        source_consommation=source,
        majoration_charge_par_passager_pct=_decimal("majoration_charge_par_passager_pct"),
        cout_horaire_conducteur=_decimal("cout_horaire_conducteur"),
        entretien_par_km=_decimal("entretien_moto_par_km" if moto else "entretien_voiture_par_km"),
        taux_commission_pct=_decimal("taux_commission_pct"),
        arrondi_prix_fcfa=int(get_param("arrondi_prix_fcfa")),
        prix_minimum_place=int(get_param("prix_minimum_place")),
    )


def devis_trajet(vehicule, depart: Point, arrivee: Point, places: int) -> Devis:
    """Prix d'un trajet partagé entre le conducteur et `places` passagers prévus."""
    route = itineraire(depart, arrivee)
    return calculer(
        distance_km=route.distance_km,
        duree_min=route.duree_min,
        type_vehicule=vehicule.type_vehicule,
        passagers_prevus=places,
        parametres=parametres_pour(vehicule),
        source_itineraire=route.source,
    )


def prix_pour(trajet, point, arrivee_lat: float, arrivee_lng: float) -> dict:
    """Prix d'un passager selon sa propre distance : du point de prise en charge choisi à son
    arrivée, rapportée au trajet du conducteur. Règles d'arrondi figées à la publication."""
    parametres = (trajet.tarification or {}).get("parametres") or {}
    if not parametres:  # trajet publié avant la tarification automatique : prix fixe
        return {"prix": trajet.prix_place, "part_trajet": Decimal(1)}
    part = part_du_trajet(
        distance_haversine_km(point.lat, point.lng, arrivee_lat, arrivee_lng),
        distance_haversine_km(
            trajet.depart_lat, trajet.depart_lng, trajet.arrivee_lat, trajet.arrivee_lng
        ),
    )
    prix = prix_passager(
        trajet.prix_place,
        part,
        int(parametres.get("arrondi_prix_fcfa", 5)),
        int(parametres.get("prix_minimum_place", 0)),
    )
    return {"prix": prix, "part_trajet": part}


def repartition(prix: int, taux_commission_pct) -> dict:
    """Commission et net conducteur d'un paiement, au taux figé lors de la publication."""
    commission, net = repartir_paiement(prix, Decimal(str(taux_commission_pct)))
    return {"commission": commission, "net_conducteur": net}
