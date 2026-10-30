import logging
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.utils.module_loading import import_string

from apps.core.geo import distance_haversine_km
from apps.routage.providers import Point

logger = logging.getLogger(__name__)
CENTIEME = Decimal("0.01")


@dataclass(frozen=True)
class Trace:
    """Tracé affiché sur la carte ; n'entre jamais dans le calcul du prix."""

    source: str  # « routage » ou « estimation » (segments droits entre les étapes)
    points: list[list[float]]  # [[lat, lng], …], 5 décimales


@dataclass(frozen=True)
class Itineraire:
    distance_km: Decimal
    duree_min: int
    source: str  # « routage » (service d'itinéraire) ou « estimation » (service indisponible)


def _fournisseur():
    return import_string(settings.ROUTAGE_PROVIDER)()


def distance_route_km(depart: Point, arrivee: Point) -> Decimal | None:
    """Distance par la route en km (2 décimales). None si le service de routage est indisponible."""
    try:
        distance = _fournisseur().distance_km(depart, arrivee)
    except Exception:  # noqa: BLE001 — service externe : on n'empêche pas la réservation
        logger.warning(
            "Calcul de distance impossible (%s)", settings.ROUTAGE_PROVIDER, exc_info=True
        )
        return None
    return Decimal(str(round(distance, 2)))


def itineraire(depart: Point, arrivee: Point) -> Itineraire:
    """Distance et durée du trajet. Service indisponible : estimation explicite et signalée
    (vol d'oiseau × coefficient de détour, vitesse moyenne), jamais une valeur inventée."""
    from apps.parametres.services import get_param

    try:
        distance, duree = _fournisseur().itineraire(depart, arrivee)
        source = "routage"
    except Exception:  # noqa: BLE001 — service externe
        logger.warning("Itinéraire indisponible (%s)", settings.ROUTAGE_PROVIDER, exc_info=True)
        distance = distance_haversine_km(*depart, *arrivee) * float(
            get_param("coef_detour_estimation")
        )
        duree = distance / float(get_param("vitesse_moyenne_kmh")) * 60
        source = "estimation"
    duree_min = int(Decimal(str(duree)).to_integral_value(rounding=ROUND_HALF_UP))
    return Itineraire(Decimal(str(distance)).quantize(CENTIEME), duree_min, source)


def _arrondir(points) -> list[list[float]]:
    return [[round(float(lat), 5), round(float(lng), 5)] for lat, lng in points]


def trace(etapes: list[Point], *, essayer_routage: bool = True) -> Trace:
    """Tracé passant par les étapes dans l'ordre. Service indisponible (ou non tenté) :
    segments droits entre les étapes. Ne lève jamais pour une réponse du fournisseur."""
    if essayer_routage:
        try:
            return Trace("routage", _arrondir(_fournisseur().trace(list(etapes))))
        except Exception:  # noqa: BLE001 — service externe : la publication n'échoue pas
            logger.warning("Tracé indisponible (%s)", settings.ROUTAGE_PROVIDER, exc_info=True)
    return Trace("estimation", _arrondir(etapes))
