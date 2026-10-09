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


def test_la_photo_du_vehicule_est_accessible(client_utilisateur, client, settings):
    settings.DEBUG = True  # en production, /media/ est servi par le serveur web
    from io import BytesIO

    from PIL import Image

    from apps.kyc.tests.factories import fichier_png

    tampon = BytesIO()
    Image.new("RGB", (4, 4), "orange").save(tampon, "PNG")
    photo = fichier_png("voiture.png")
    photo.file = BytesIO(tampon.getvalue())
    photo.size = len(tampon.getvalue())

    reponse = client_utilisateur.post(URL, {**VOITURE, "photo": photo}, format="multipart")

    url_photo = reponse.json()["reponse"]["photo"]
    assert "/media/vehicules/" in url_photo
    assert client.get(url_photo.split("testserver")[-1]).status_code == 200


def test_media_non_servi_hors_developpement(client, settings):
    settings.DEBUG = False

    assert client.get("/media/vehicules/voiture.png").status_code == 404
