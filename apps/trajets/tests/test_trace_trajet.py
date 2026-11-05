from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone

from apps.routage.providers import FakeRoutingProvider
from apps.trajets import services
from apps.trajets.models import Trajet
from conftest import ADIDOGOME, GRAND_MARCHE

pytestmark = pytest.mark.django_db

DEPART = (ADIDOGOME["lat"], ADIDOGOME["lng"])
ARRIVEE = (GRAND_MARCHE["lat"], GRAND_MARCHE["lng"])
CARREFOURS = [
    {"lat": 6.1750, "lng": 1.1700, "libelle": "Carrefour Adidogomé"},
    {"lat": 6.1600, "lng": 1.1900, "libelle": "Carrefour Bè"},
    {"lat": 6.1400, "lng": 1.2100, "libelle": "Carrefour Déckon"},
]
TRACE_DIRECT = [list(DEPART), *[[c["lat"], c["lng"]] for c in CARREFOURS], list(ARRIVEE)]


def publier(client_de, conducteur):
    charge = {
        "vehicule_id": str(conducteur.vehicules.first().id),
        "depart_lat": DEPART[0],
        "depart_lng": DEPART[1],
        "depart_libelle": "Adidogomé",
        "arrivee_lat": ARRIVEE[0],
        "arrivee_lng": ARRIVEE[1],
        "arrivee_libelle": "Grand Marché",
        "depart_le": (timezone.now() + timedelta(hours=2)).isoformat(),
        "places": 2,
        "points": CARREFOURS,
    }
    return client_de(conducteur).post("/api/v1/trajets/", charge, format="json")


def assert_prix_depart_arrivee(conducteur, trajet_id):
    """Le prix reste calculé départ → arrivée, sans les carrefours (D-21 reporté)."""
    devis = services.estimer(
        conducteur,
        vehicule_id=conducteur.vehicules.first().id,
        depart=DEPART,
        arrivee=ARRIVEE,
        places=2,
    )
    trajet = Trajet.objects.get(pk=trajet_id)
    assert trajet.distance_km == devis.distance_km
    assert trajet.duree_min == devis.duree_min
    assert trajet.prix_place == devis.prix_place
    assert trajet.tarification == devis.instantane()


def test_le_prix_ne_suit_pas_le_trace(client_de, conducteur):
    original = FakeRoutingProvider.itineraire
    with mock.patch.object(
        FakeRoutingProvider, "itineraire", autospec=True, side_effect=original
    ) as itineraire:
        reponse = publier(client_de, conducteur)

    assert reponse.status_code == 201
    assert itineraire.call_count == 1
    assert itineraire.call_args.args[1:] == (DEPART, ARRIVEE)
    assert_prix_depart_arrivee(conducteur, reponse.json()["reponse"]["id"])


def test_trace_par_les_carrefours_dans_l_ordre_en_lat_lng(client_de, conducteur):
    reponse = publier(client_de, conducteur)

    trace = reponse.json()["reponse"]["trace"]
    assert trace == {"source": "routage", "points": TRACE_DIRECT}
    assert trace["points"][0] == [6.1745, 1.169]  # [lat, lng] : lat ≈ 6,1 à Lomé
    assert Trajet.objects.get(pk=reponse.json()["reponse"]["id"]).trace == trace


def test_trace_indisponible_ne_bloque_pas_la_publication(client_de, conducteur):
    with mock.patch.object(FakeRoutingProvider, "trace", side_effect=TimeoutError("OSRM")):
        reponse = publier(client_de, conducteur)

    assert reponse.status_code == 201
    corps = reponse.json()["reponse"]
    assert corps["trace"] == {"source": "estimation", "points": TRACE_DIRECT}
    assert_prix_depart_arrivee(conducteur, corps["id"])


def test_itineraire_en_panne_le_trace_n_est_pas_demande(client_de, conducteur):
    with (
        mock.patch.object(FakeRoutingProvider, "itineraire", side_effect=TimeoutError("OSRM")),
        mock.patch.object(FakeRoutingProvider, "trace") as trace,
    ):
        reponse = publier(client_de, conducteur)

    assert reponse.status_code == 201
    trace.assert_not_called()
    assert reponse.json()["reponse"]["trace"] == {"source": "estimation", "points": TRACE_DIRECT}


def test_detail_du_trajet_contient_le_trace(client_de, passager, conducteur):
    trajet_id = publier(client_de, conducteur).json()["reponse"]["id"]

    detail = client_de(passager).get(f"/api/v1/trajets/{trajet_id}/").json()["reponse"]

    assert detail["trace"] == {"source": "routage", "points": TRACE_DIRECT}


def test_trajet_publie_avant_le_trace(client_de, passager, trajet):
    Trajet.objects.filter(pk=trajet.pk).update(trace=None)

    detail = client_de(passager).get(f"/api/v1/trajets/{trajet.id}/").json()["reponse"]

    assert "trace" in detail and detail["trace"] is None


def test_trace_absent_de_la_recherche_et_de_mes_trajets(client_de, passager, conducteur):
    trajet_id = publier(client_de, conducteur).json()["reponse"]["id"]

    resultats = (
        client_de(passager)
        .get(
            "/api/v1/trajets/recherche/",
            {
                "depart_lat": DEPART[0],
                "depart_lng": DEPART[1],
                "arrivee_lat": ARRIVEE[0],
                "arrivee_lng": ARRIVEE[1],
                "date_heure": (timezone.now() + timedelta(hours=2)).isoformat(),
            },
        )
        .json()["reponse"]
    )
    mes_trajets = client_de(conducteur).get("/api/v1/trajets/mes-trajets/").json()["reponse"]

    assert [r["trajet"]["id"] for r in resultats] == [trajet_id]
    assert "trace" not in resultats[0]["trajet"]
    assert [t["id"] for t in mes_trajets["results"]] == [trajet_id]
    assert "trace" not in mes_trajets["results"][0]
