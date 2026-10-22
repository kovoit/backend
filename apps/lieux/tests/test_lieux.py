import pytest

from apps.lieux.models import Lieu

pytestmark = pytest.mark.django_db

URL = "/api/v1/lieux/"


def _libelles(client, **params):
    reponse = client.get(URL, params)
    assert reponse.status_code == 200
    return [lieu["libelle"] for lieu in reponse.json()["reponse"]]


def test_lieux_de_depart_presents(client_utilisateur):
    lieux = client_utilisateur.get(URL).json()["reponse"]
    assert len(lieux) == 15
    assert set(lieux[0]) == {"id", "libelle", "quartier", "type", "lat", "lng"}


def test_recherche_sans_accents_ni_majuscules(client_utilisateur):
    assert _libelles(client_utilisateur, q="hedzra") == ["Hédzranawoé"]
    assert _libelles(client_utilisateur, q="TOKOIN") == [
        "CHU Sylvanus Olympio",
        "Tokoin Hôpital",
        "Université de Lomé · Entrée sud",
    ]
    # Moins de 2 caractères : pas de filtre
    assert len(_libelles(client_utilisateur, q="t")) == 15


def test_lieu_desactive_non_propose(client_utilisateur):
    Lieu.objects.filter(libelle="Grand Marché").update(actif=False)
    assert "Grand Marché" not in _libelles(client_utilisateur)


def test_reserve_aux_comptes_connectes(api_client):
    assert api_client.get(URL).status_code == 401
