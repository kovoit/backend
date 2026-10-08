"""Fournisseurs de distance par la route. Choisi par le réglage `ROUTAGE_PROVIDER`."""

import json
import urllib.request

from django.conf import settings

from apps.core.geo import distance_haversine_km

Point = tuple[float, float]  # (latitude, longitude)


class RoutingProvider:
    def distance_km(self, depart: Point, arrivee: Point) -> float:
        raise NotImplementedError


class OsrmProvider(RoutingProvider):
    """OSRM (OpenStreetMap) : serveur public par défaut, auto-hébergeable via `OSRM_URL`."""

    def distance_km(self, depart: Point, arrivee: Point) -> float:
        coordonnees = f"{depart[1]},{depart[0]};{arrivee[1]},{arrivee[0]}"
        url = f"{settings.OSRM_URL.rstrip('/')}/route/v1/driving/{coordonnees}?overview=false"
        with urllib.request.urlopen(url, timeout=5) as reponse:  # noqa: S310 — URL de config
            donnees = json.load(reponse)
        if donnees.get("code") != "Ok" or not donnees.get("routes"):
            raise ValueError(f"Réponse OSRM inattendue : {donnees.get('code')}")
        return donnees["routes"][0]["distance"] / 1000


class FakeRoutingProvider(RoutingProvider):
    """Pour les tests et le développement hors ligne : vol d'oiseau majoré de 30 %."""

    def distance_km(self, depart: Point, arrivee: Point) -> float:
        return distance_haversine_km(*depart, *arrivee) * 1.3
