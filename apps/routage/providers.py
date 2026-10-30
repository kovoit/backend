"""Fournisseurs d'itinéraire par la route. Choisi par le réglage `ROUTAGE_PROVIDER`."""

import json
import urllib.request

from django.conf import settings

from apps.core.geo import distance_haversine_km

Point = tuple[float, float]  # (latitude, longitude)


class RoutingProvider:
    def itineraire(self, depart: Point, arrivee: Point) -> tuple[float, float]:
        """(distance en km, durée en minutes) par la route."""
        raise NotImplementedError

    def distance_km(self, depart: Point, arrivee: Point) -> float:
        return self.itineraire(depart, arrivee)[0]

    def trace(self, etapes: list[Point]) -> list[Point]:
        """Points (lat, lng) de la route passant par les étapes dans l'ordre (affichage)."""
        raise NotImplementedError


class OsrmProvider(RoutingProvider):
    """OSRM (OpenStreetMap) : serveur public par défaut, auto-hébergeable via `OSRM_URL`."""

    def itineraire(self, depart: Point, arrivee: Point) -> tuple[float, float]:
        coordonnees = f"{depart[1]},{depart[0]};{arrivee[1]},{arrivee[0]}"
        url = f"{settings.OSRM_URL.rstrip('/')}/route/v1/driving/{coordonnees}?overview=false"
        with urllib.request.urlopen(url, timeout=5) as reponse:  # noqa: S310 — URL de config
            donnees = json.load(reponse)
        if donnees.get("code") != "Ok" or not donnees.get("routes"):
            raise ValueError(f"Réponse OSRM inattendue : {donnees.get('code')}")
        route = donnees["routes"][0]
        return route["distance"] / 1000, route["duration"] / 60

    def trace(self, etapes: list[Point]) -> list[Point]:
        coordonnees = ";".join(f"{lng},{lat}" for lat, lng in etapes)
        url = (
            f"{settings.OSRM_URL.rstrip('/')}/route/v1/driving/{coordonnees}"
            "?overview=simplified&geometries=geojson"
        )
        with urllib.request.urlopen(url, timeout=5) as reponse:  # noqa: S310 — URL de config
            donnees = json.load(reponse)
        if donnees.get("code") != "Ok" or not donnees.get("routes"):
            raise ValueError(f"Réponse OSRM inattendue : {donnees.get('code')}")
        points = donnees["routes"][0]["geometry"]["coordinates"]
        if len(points) < 2:
            raise ValueError("Tracé OSRM trop court")
        return [(lat, lng) for lng, lat in points]  # GeoJSON : [lng, lat]


class FakeRoutingProvider(RoutingProvider):
    """Tests et développement hors ligne : vol d'oiseau majoré de 30 %, à 25 km/h."""

    def itineraire(self, depart: Point, arrivee: Point) -> tuple[float, float]:
        distance = distance_haversine_km(*depart, *arrivee) * 1.3
        return distance, distance / 25 * 60

    def trace(self, etapes: list[Point]) -> list[Point]:
        return list(etapes)
