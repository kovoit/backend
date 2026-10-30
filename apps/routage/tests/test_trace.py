from unittest import mock

import pytest

from apps.routage.providers import FakeRoutingProvider, OsrmProvider
from apps.routage.services import trace
from apps.routage.tests.test_routage import reponse_osrm

DEPART, CARREFOUR, ARRIVEE = (6.1745, 1.1690), (6.1750, 1.1700), (6.1300, 1.2220)
ETAPES = [DEPART, CARREFOUR, ARRIVEE]
OSRM = "apps.routage.providers.OsrmProvider"


def route_osrm(coordonnees: list) -> dict:
    return {"code": "Ok", "routes": [{"geometry": {"coordinates": coordonnees}}]}


def test_osrm_demande_le_trace_par_toutes_les_etapes_dans_l_ordre(settings):
    settings.OSRM_URL = "https://osrm.exemple/"
    with mock.patch(
        "urllib.request.urlopen", return_value=reponse_osrm(route_osrm([[1.169, 6.1745]] * 2))
    ) as appel:
        OsrmProvider().trace(ETAPES)

    assert appel.call_args.args[0] == (
        "https://osrm.exemple/route/v1/driving/1.169,6.1745;1.17,6.175;1.222,6.13"
        "?overview=simplified&geometries=geojson"
    )
    assert appel.call_args.kwargs["timeout"] == 5


def test_osrm_convertit_lng_lat_en_lat_lng(settings):
    settings.ROUTAGE_PROVIDER = OSRM
    geojson = [[1.169, 6.1745], [1.1712345678, 6.1601234567], [1.222, 6.13]]
    with mock.patch("urllib.request.urlopen", return_value=reponse_osrm(route_osrm(geojson))):
        resultat = trace(ETAPES)

    assert resultat.source == "routage"
    assert resultat.points == [[6.1745, 1.169], [6.16012, 1.17123], [6.13, 1.222]]


@pytest.mark.parametrize(
    "reponse",
    [
        {"code": "NoRoute"},
        {"code": "Ok", "routes": []},
        route_osrm([[1.169, 6.1745]]),
    ],
)
def test_reponse_osrm_inutilisable_donne_des_segments_droits(settings, reponse):
    settings.ROUTAGE_PROVIDER = OSRM
    with mock.patch("urllib.request.urlopen", return_value=reponse_osrm(reponse)):
        resultat = trace(ETAPES)

    assert resultat.source == "estimation"
    assert resultat.points == [list(etape) for etape in ETAPES]


def test_panne_reseau_donne_des_segments_droits(settings):
    settings.ROUTAGE_PROVIDER = OSRM
    with mock.patch("urllib.request.urlopen", side_effect=TimeoutError("délai dépassé")):
        resultat = trace(ETAPES)

    assert resultat.source == "estimation"
    assert resultat.points == [list(etape) for etape in ETAPES]


def test_sans_routage_le_fournisseur_n_est_pas_appele():
    with mock.patch.object(FakeRoutingProvider, "trace") as fournisseur:
        resultat = trace(ETAPES, essayer_routage=False)

    fournisseur.assert_not_called()
    assert resultat.source == "estimation"
    assert resultat.points == [list(etape) for etape in ETAPES]


def test_fournisseur_simule():
    resultat = trace(ETAPES)

    assert resultat.source == "routage"
    assert resultat.points == [list(etape) for etape in ETAPES]
