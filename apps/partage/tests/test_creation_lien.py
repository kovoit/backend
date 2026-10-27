"""Création du lien « Partager mon trajet » : seulement en `acceptee` ou `en_cours` (D-05)."""

import pytest

from apps.partage.tests.parcours import (
    POSITION,
    POSITION_DANS_LA_PAGE,
    STATUTS_INVALIDES,
    amener_au_statut,
    creer_lien_par_api,
)
from apps.reservations import services as reservations
from apps.reservations.models import StatutReservation as S

pytestmark = pytest.mark.django_db


def _post_partage(client, reservation_id):
    return client.post(f"/api/v1/reservations/{reservation_id}/partage/")


def _verifier_409_partage_impossible(reponse):
    corps = reponse.json()
    assert reponse.status_code == 409
    assert set(corps) == {"statut", "message", "reponse"}
    assert corps["statut"] == "failed" and corps["message"].strip()
    assert corps["reponse"]["code"] == "PARTAGE_IMPOSSIBLE"


def test_creation_en_acceptee_renvoie_le_meme_lien(client_de, passager, reservation_acceptee):
    client = client_de(passager)

    premier = _post_partage(client, reservation_acceptee.id)
    second = _post_partage(client, reservation_acceptee.id)

    assert premier.status_code == second.status_code == 201
    assert premier.json()["statut"] == "success"
    assert premier.json()["reponse"] == second.json()["reponse"]


def test_creation_en_cours(client_de, passager, conducteur, reservation_acceptee):
    amener_au_statut(reservation_acceptee, S.EN_COURS, passager, conducteur)

    reponse = _post_partage(client_de(passager), reservation_acceptee.id)

    assert reponse.status_code == 201
    assert reponse.json()["reponse"]["chemin"].startswith("/suivi/")


@pytest.mark.parametrize("statut", STATUTS_INVALIDES)
def test_creation_409_hors_acceptee_et_en_cours_lien_deja_cree(
    client_de, passager, conducteur, reservation_acceptee, statut
):
    client = client_de(passager)
    creer_lien_par_api(client, reservation_acceptee.id)
    amener_au_statut(reservation_acceptee, statut, passager, conducteur)

    _verifier_409_partage_impossible(_post_partage(client, reservation_acceptee.id))


@pytest.mark.parametrize("statut", STATUTS_INVALIDES)
def test_creation_409_hors_acceptee_et_en_cours_sans_lien(
    client_de, passager, conducteur, reservation_acceptee, statut
):
    amener_au_statut(reservation_acceptee, statut, passager, conducteur)

    _verifier_409_partage_impossible(_post_partage(client_de(passager), reservation_acceptee.id))


@pytest.mark.parametrize("statut", [S.DEMANDEE, S.REFUSEE])
def test_creation_409_avant_acceptation(client_de, passager, conducteur, reservation, statut):
    if statut == S.REFUSEE:
        reservations.refuser(conducteur, reservation.id)

    _verifier_409_partage_impossible(_post_partage(client_de(passager), reservation.id))


def test_ca001_1_ca032_1_position_envoyee_en_cours_visible_par_le_proche(
    client_de, api_client, passager, conducteur, reservation_acceptee
):
    """Non-régression : le correctif D-05 ne masque pas la position pendant le trajet."""
    jeton = creer_lien_par_api(client_de(passager), reservation_acceptee.id)
    amener_au_statut(reservation_acceptee, S.EN_COURS, passager, conducteur)

    envoi = client_de(conducteur).post(
        f"/api/v1/trajets/{reservation_acceptee.trajet_id}/position/", POSITION
    )

    assert envoi.status_code == 200
    page = api_client.get(f"/suivi/{jeton}/")
    assert page.status_code == 200
    assert "En route" in page.content.decode()
    assert POSITION_DANS_LA_PAGE in page.content.decode()
    public = api_client.get(f"/api/v1/partage/{jeton}/").json()["reponse"]
    assert (public["position_lat"], public["position_lng"]) == (POSITION["lat"], POSITION["lng"])
