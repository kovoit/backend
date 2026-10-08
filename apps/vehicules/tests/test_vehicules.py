import pytest

from apps.vehicules.tests.factories import VehiculeFactory

pytestmark = pytest.mark.django_db
URL = "/api/v1/vehicules/"
VOITURE = {
    "type_vehicule": "voiture",
    "marque": "Toyota",
    "modele": "Yaris",
    "couleur": "Blanche",
    "immatriculation": "tg 1234 ab",
    "nb_places": 5,
}


def test_declarer_un_vehicule_normalise_l_immatriculation(client_utilisateur):
    reponse = client_utilisateur.post(URL, VOITURE, format="json")

    assert reponse.status_code == 201
    assert reponse.json()["reponse"]["immatriculation"] == "TG1234AB"


def test_immatriculation_deja_enregistree(client_utilisateur):
    VehiculeFactory(immatriculation="TG1234AB")

    reponse = client_utilisateur.post(URL, VOITURE, format="json")

    assert reponse.status_code == 409
    assert reponse.json()["reponse"]["code"] == "IMMATRICULATION_EXISTANTE"


def test_une_moto_a_deux_places(client_utilisateur):
    reponse = client_utilisateur.post(
        URL, {**VOITURE, "type_vehicule": "moto", "nb_places": 3}, format="json"
    )

    assert reponse.status_code == 400


def test_lister_modifier_supprimer(client_utilisateur, utilisateur):
    vehicule = VehiculeFactory(proprietaire=utilisateur)

    assert len(client_utilisateur.get(URL).json()["reponse"]) == 1
    reponse = client_utilisateur.patch(f"{URL}{vehicule.id}/", {"couleur": "Rouge"}, format="json")
    assert reponse.json()["reponse"]["couleur"] == "Rouge"
    assert client_utilisateur.delete(f"{URL}{vehicule.id}/").status_code == 200
    assert client_utilisateur.get(URL).json()["reponse"] == []


def test_vehicule_d_un_autre_introuvable(client_utilisateur):
    autre = VehiculeFactory()

    assert client_utilisateur.get(f"{URL}{autre.id}/").status_code == 404
    assert client_utilisateur.delete(f"{URL}{autre.id}/").status_code == 404


def test_vehicule_lie_a_un_trajet_non_supprimable(client_de, conducteur, trajet):
    reponse = client_de(conducteur).delete(f"{URL}{trajet.vehicule_id}/")

    assert reponse.status_code == 409
    assert reponse.json()["reponse"]["code"] == "VEHICULE_UTILISE"
