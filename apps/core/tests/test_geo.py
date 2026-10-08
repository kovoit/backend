import pytest

from apps.core.geo import distance_haversine_km


def test_distance_nulle_pour_un_meme_point():
    assert distance_haversine_km(6.1319, 1.2228, 6.1319, 1.2228) == 0


def test_un_degre_de_latitude_fait_environ_111_km():
    assert distance_haversine_km(6.0, 1.2, 7.0, 1.2) == pytest.approx(111.19, abs=0.1)


def test_distance_symetrique():
    aller = distance_haversine_km(6.1319, 1.2228, 6.1725, 1.2133)
    retour = distance_haversine_km(6.1725, 1.2133, 6.1319, 1.2228)
    assert aller == pytest.approx(retour)
