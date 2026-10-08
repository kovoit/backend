"""Calculs géographiques simples (vol d'oiseau). La distance de facturation passe par `routage`."""

from math import asin, cos, radians, sin, sqrt

RAYON_TERRE_KM = 6371.0


def distance_haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance à vol d'oiseau entre deux points GPS, en kilomètres."""
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return 2 * RAYON_TERRE_KM * asin(sqrt(a))
