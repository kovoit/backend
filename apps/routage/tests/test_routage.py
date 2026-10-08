import io
import json
from decimal import Decimal
from unittest import mock

from apps.routage.providers import OsrmProvider
from apps.routage.services import distance_route_km

DEPART, ARRIVEE = (6.1745, 1.1690), (6.1300, 1.2220)


def reponse_osrm(donnees: dict):
    return mock.MagicMock(
        __enter__=lambda s: io.StringIO(json.dumps(donnees)), __exit__=lambda *a: None
    )


def test_osrm_renvoie_la_distance_en_km(settings):
    settings.OSRM_URL = "https://osrm.exemple"
    with mock.patch(
        "urllib.request.urlopen",
        return_value=reponse_osrm({"code": "Ok", "routes": [{"distance": 8423.7}]}),
    ) as appel:
        assert OsrmProvider().distance_km(DEPART, ARRIVEE) == 8.4237

    url = appel.call_args.args[0]
    assert url.startswith("https://osrm.exemple/route/v1/driving/1.169,6.1745;1.222,6.13")


def test_service_indisponible_renvoie_none(settings):
    settings.ROUTAGE_PROVIDER = "apps.routage.providers.OsrmProvider"
    with mock.patch("urllib.request.urlopen", return_value=reponse_osrm({"code": "NoRoute"})):
        assert distance_route_km(DEPART, ARRIVEE) is None


def test_fournisseur_simule():
    distance = distance_route_km(DEPART, ARRIVEE)

    assert isinstance(distance, Decimal) and distance > 0
