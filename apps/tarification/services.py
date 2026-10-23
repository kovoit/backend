"""Tarification (PRD §7) : seul point d'entrée des autres apps pour le prix d'un trajet.

La formule est dans calcul.py (pure, testée seule) ; ce module y injecte les paramètres
administrables et l'itinéraire. Le prix est toujours calculé ici, jamais reçu du client.
"""

from decimal import Decimal

from apps.parametres.services import get_param
from apps.routage.providers import Point
from apps.routage.services import itineraire
from apps.tarification.calcul import Devis, Parametres, calculer, repartir_paiement
from apps.vehicules.models import TypeVehicule

__all__ = ["Devis", "devis_trajet", "parametres_pour", "repartition", "repartir_paiement"]


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


def repartition(prix: int, taux_commission_pct) -> dict:
    """Commission et net conducteur d'un paiement, au taux figé lors de la publication."""
    commission, net = repartir_paiement(prix, Decimal(str(taux_commission_pct)))
    return {"commission": commission, "net_conducteur": net}
