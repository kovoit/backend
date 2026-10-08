"""Correspondance passager / trajets (PRD §5) : rayons et fenêtre horaire paramétrables."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import cos, radians

from django.utils import timezone

from apps.accounts.services import est_suspendu
from apps.core.geo import distance_haversine_km
from apps.parametres.services import get_param
from apps.trajets.models import PointPriseEnCharge, Trajet
from apps.trajets.repository import trajet_repository

KM_PAR_DEGRE = 111.32


@dataclass
class ResultatRecherche:
    trajet: Trajet
    point_propose: PointPriseEnCharge
    distance_marche_km: float
    ecart_minutes: int


def _boite(lat: float, lng: float, rayon_km: float) -> tuple[float, float, float, float]:
    delta_lat = rayon_km / KM_PAR_DEGRE
    delta_lng = rayon_km / (KM_PAR_DEGRE * max(cos(radians(lat)), 0.01))
    return lat - delta_lat, lat + delta_lat, lng - delta_lng, lng + delta_lng


def rechercher(
    utilisateur,
    depart_lat: float,
    depart_lng: float,
    arrivee_lat: float,
    arrivee_lng: float,
    date_heure: datetime,
) -> list[ResultatRecherche]:
    fenetre = timedelta(minutes=get_param("fenetre_horaire_min"))
    rayon_depart = float(get_param("rayon_depart_km"))
    rayon_arrivee = float(get_param("rayon_arrivee_km"))

    candidats = trajet_repository.candidats_recherche(
        max(date_heure - fenetre, timezone.now()),
        date_heure + fenetre,
        utilisateur,
        *_boite(arrivee_lat, arrivee_lng, rayon_arrivee),
    )

    resultats = []
    for trajet in candidats:
        if est_suspendu(trajet.conducteur):
            continue
        distance_arrivee = distance_haversine_km(
            arrivee_lat, arrivee_lng, trajet.arrivee_lat, trajet.arrivee_lng
        )
        if distance_arrivee > rayon_arrivee:
            continue
        point, marche = min(
            (
                (point, distance_haversine_km(depart_lat, depart_lng, point.lat, point.lng))
                for point in trajet.points.all()
            ),
            key=lambda couple: couple[1],
        )
        if marche > rayon_depart:
            continue
        ecart = abs((trajet.depart_le - date_heure).total_seconds()) // 60
        resultats.append(ResultatRecherche(trajet, point, round(marche, 2), int(ecart)))

    # Heure de départ la plus proche d'abord, puis distance de marche la plus courte
    resultats.sort(key=lambda r: (r.ecart_minutes, r.distance_marche_km))
    return resultats
