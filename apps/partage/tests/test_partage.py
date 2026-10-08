import pytest

from apps.reservations import services as reservations

pytestmark = pytest.mark.django_db


def test_partage_impossible_avant_acceptation(client_de, passager, reservation):
    reponse = client_de(passager).post(f"/api/v1/reservations/{reservation.id}/partage/")

    assert reponse.status_code == 409


def test_lien_public_puis_expire_a_l_annulation(
    client_de, api_client, passager, conducteur, reservation_acceptee
):
    reponse = client_de(passager).post(f"/api/v1/reservations/{reservation_acceptee.id}/partage/")
    assert reponse.status_code == 201
    chemin = reponse.json()["reponse"]["chemin"]
    # Le même lien est renvoyé si on le redemande
    assert (
        client_de(passager)
        .post(f"/api/v1/reservations/{reservation_acceptee.id}/partage/")
        .json()["reponse"]["chemin"]
        == chemin
    )

    public = api_client.get(chemin).json()["reponse"]
    assert public["conducteur_prenom"] == "Kodjo"
    assert "TG" in public["vehicule"]
    assert "email" not in str(public)

    reservations.annuler(passager, reservation_acceptee.id)
    assert api_client.get(chemin).status_code == 404


def test_le_conducteur_ne_cree_pas_de_lien(client_de, conducteur, reservation_acceptee):
    reponse = client_de(conducteur).post(f"/api/v1/reservations/{reservation_acceptee.id}/partage/")

    assert reponse.status_code == 404


def test_jeton_inconnu(api_client):
    assert api_client.get("/api/v1/partage/inexistant/").status_code == 404
