import logging
from decimal import Decimal

from django.conf import settings
from django.utils.module_loading import import_string

from apps.routage.providers import Point

logger = logging.getLogger(__name__)


def distance_route_km(depart: Point, arrivee: Point) -> Decimal | None:
    """Distance par la route en km (2 décimales). None si le service de routage est indisponible."""
    fournisseur = import_string(settings.ROUTAGE_PROVIDER)()
    try:
        distance = fournisseur.distance_km(depart, arrivee)
    except Exception:  # noqa: BLE001 — service externe : on n'empêche pas la publication
        logger.warning(
            "Calcul de distance impossible (%s)", settings.ROUTAGE_PROVIDER, exc_info=True
        )
        return None
    return Decimal(str(round(distance, 2)))
