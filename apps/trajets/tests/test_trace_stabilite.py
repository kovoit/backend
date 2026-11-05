"""F-056 / F-057 (contrat C1) : le tracé enregistré est la géométrie du routeur, il ne change
plus après la publication et il reste absent des réponses conducteur position / terminer /
annuler."""

from unittest import mock

import pytest

from apps.routage.providers import FakeRoutingProvider
from apps.trajets.models import Trajet
from apps.trajets.tests.test_trace_trajet import ARRIVEE, CARREFOURS, DEPART, TRACE_DIRECT, publier

pytestmark = pytest.mark.django_db

# Géométrie « OSRM » plus fine que les étapes, en (lat, lng), avec plus de 5 décimales
GEOMETRIE_ROUTEUR = [
    (6.174501, 1.169004),
    (6.1748349, 1.1695561),
    (6.1750, 1.1700),
    (6.1676123, 1.1801789),
    (6.1523456, 1.2004321),
    (6.1309871, 1.2201234),
]
# Même géométrie arrondie à 5 décimales (écrite à la main, pas recalculée)
GEOMETRIE_ARRONDIE = [
    [6.1745, 1.169],
    [6.17483, 1.16956],
    [6.175, 1.17],
    [6.16761, 1.18018],
    [6.15235, 1.20043],
    [6.13099, 1.22012],
]
ETAPES = [DEPART, *[(c["lat"], c["lng"]) for c in CARREFOURS], ARRIVEE]


def publier_avec_geometrie(client_de, conducteur):
    with mock.patch.object(FakeRoutingProvider, "trace", return_value=GEOMETRIE_ROUTEUR) as trace:
        reponse = publier(client_de, conducteur)
    trace.assert_called_once()
    assert trace.call_args.args[0] == ETAPES  # départ → carrefours dans l'ordre → arrivée
    return reponse


def test_la_geometrie_du_routeur_est_enregistree_pas_les_etapes(client_de, passager, conducteur):
    reponse = publier_avec_geometrie(client_de, conducteur)

    assert reponse.status_code == 201
    corps = reponse.json()
    assert corps["statut"] == "success" and corps["message"]
    trace = corps["reponse"]["trace"]
    assert trace == {"source": "routage", "points": GEOMETRIE_ARRONDIE}
    assert trace["points"] != TRACE_DIRECT
    trajet_id = corps["reponse"]["id"]
    assert Trajet.objects.get(pk=trajet_id).trace == trace
    detail = client_de(passager).get(f"/api/v1/trajets/{trajet_id}/").json()["reponse"]
    assert detail["trace"] == trace


@pytest.mark.parametrize(
    "routeur_apres",
    [
        pytest.param(
            {
                "trace": {"return_value": [(6.2, 1.1), (6.3, 1.3)]},
                "itineraire": {"return_value": (42.0, 99.0)},
            },
            id="autre_route",
        ),
        pytest.param(
            {
                "trace": {"side_effect": TimeoutError("OSRM")},
                "itineraire": {"side_effect": TimeoutError("OSRM")},
            },
            id="routeur_en_panne",
        ),
    ],
)
def test_le_trace_ne_change_plus_apres_la_publication(
    client_de, passager, conducteur, routeur_apres
):
    corps = publier_avec_geometrie(client_de, conducteur).json()["reponse"]
    trace_publie = corps["trace"]
    point_id = corps["points"][1]["id"]  # Carrefour Bè
    url = f"/api/v1/trajets/{corps['id']}/"
    avec_arret = {"point_id": point_id, "arrivee_lat": 6.1400, "arrivee_lng": 1.2100}

    with (
        mock.patch.object(FakeRoutingProvider, "trace", **routeur_apres["trace"]) as trace,
        mock.patch.object(FakeRoutingProvider, "itineraire", **routeur_apres["itineraire"]),
    ):
        sans_arret = client_de(passager).get(url)
        avec = client_de(passager).get(url, avec_arret)

    assert sans_arret.status_code == 200 and avec.status_code == 200
    assert sans_arret.json()["reponse"]["trace"] == trace_publie
    assert avec.json()["reponse"]["trace"] == trace_publie
    assert trace_publie == {"source": "routage", "points": GEOMETRIE_ARRONDIE}
    trace.assert_not_called()


@pytest.mark.parametrize(
    ("action", "charge"),
    [
        ("position", {"lat": 6.17, "lng": 1.18}),
        ("terminer", None),
        ("annuler", None),
    ],
    ids=["position", "terminer", "annuler"],
)
def test_trace_absent_des_reponses_conducteur(client_de, conducteur, action, charge):
    trajet_id = publier(client_de, conducteur).json()["reponse"]["id"]
    assert Trajet.objects.get(pk=trajet_id).trace is not None  # le trajet a bien un tracé

    reponse = client_de(conducteur).post(
        f"/api/v1/trajets/{trajet_id}/{action}/", charge, format="json"
    )

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["statut"] == "success" and corps["message"]
    assert corps["reponse"]["id"] == trajet_id
    assert "trace" not in corps["reponse"]
