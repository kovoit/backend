import pytest

from apps.reservations.code_depart import calculer_code
from conftest import GRAND_MARCHE

pytestmark = pytest.mark.django_db


def test_demande_via_api(client_de, passager, trajet):
    reponse = client_de(passager).post(
        "/api/v1/reservations/",
        {
            "trajet_id": str(trajet.id),
            "point_id": str(trajet.points.first().id),
            "arrivee_lat": GRAND_MARCHE["lat"],
            "arrivee_lng": GRAND_MARCHE["lng"],
        },
        format="json",
    )

    assert reponse.status_code == 201
    corps = reponse.json()["reponse"]
    assert corps["statut"] == "demandee" and corps["code_depart"] is None
    assert corps["montant_total"] == 300


def test_kyc_passager_obligatoire_pour_reserver(client_utilisateur, trajet):
    reponse = client_utilisateur.post("/api/v1/reservations/", {}, format="json")

    assert reponse.status_code == 403
    assert reponse.json()["reponse"]["code"] == "KYC_PASSAGER_REQUIS"


def test_le_code_de_depart_n_est_visible_que_du_passager(
    client_de, passager, conducteur, reservation
):
    reponse = client_de(conducteur).post(f"/api/v1/reservations/{reservation.id}/accepter/")
    assert reponse.status_code == 200
    assert "code_depart" not in reponse.json()["reponse"]

    vue_conducteur = client_de(conducteur).get(f"/api/v1/reservations/{reservation.id}/").json()
    vue_passager = client_de(passager).get(f"/api/v1/reservations/{reservation.id}/").json()
    reservation.refresh_from_db()  # récupère le sel généré à l'acceptation
    assert "code_depart" not in vue_conducteur["reponse"]
    assert vue_passager["reponse"]["code_depart"] == calculer_code(reservation)


def test_parcours_conducteur_via_api(client_de, passager, conducteur, reservation):
    client = client_de(conducteur)
    demandes = client.get(f"/api/v1/trajets/{reservation.trajet_id}/reservations/").json()
    assert demandes["reponse"]["count"] == 1
    assert demandes["reponse"]["results"][0]["passager"]["prenom"] == "Afi"

    client.post(f"/api/v1/reservations/{reservation.id}/accepter/")
    reservation.refresh_from_db()
    reponse = client.post(
        f"/api/v1/reservations/{reservation.id}/code-depart/", {"code": "12"}, format="json"
    )
    assert reponse.status_code == 400
    reponse = client.post(
        f"/api/v1/reservations/{reservation.id}/code-depart/",
        {"code": calculer_code(reservation)},
        format="json",
    )
    assert reponse.json()["reponse"]["statut"] == "en_cours"

    client.post(f"/api/v1/trajets/{reservation.trajet_id}/terminer/")
    reponse = client_de(passager).post(f"/api/v1/reservations/{reservation.id}/confirmer-arrivee/")
    assert reponse.json()["reponse"]["statut"] == "cloturee"


def test_annulation_et_refus_via_api(client_de, passager, conducteur, reservation):
    reponse = client_de(passager).post(f"/api/v1/reservations/{reservation.id}/annuler/")
    assert reponse.json()["reponse"]["statut"] == "annulee"
    reponse = client_de(conducteur).post(f"/api/v1/reservations/{reservation.id}/refuser/")
    assert reponse.status_code == 409
    assert reponse.json()["reponse"]["code"] == "TRANSITION_INVALIDE"


def test_absence_via_api_trop_tot(client_de, conducteur, reservation_acceptee):
    reponse = client_de(conducteur).post(
        f"/api/v1/reservations/{reservation_acceptee.id}/absent/",
        {"lat": 6.17, "lng": 1.17},
        format="json",
    )

    assert reponse.status_code == 409
    assert reponse.json()["reponse"]["code"] == "ABSENCE_PREMATUREE"


def test_un_tiers_ne_voit_pas_la_reservation(client_utilisateur, reservation):
    assert client_utilisateur.get(f"/api/v1/reservations/{reservation.id}/").status_code == 404
    assert (
        client_utilisateur.post(f"/api/v1/reservations/{reservation.id}/accepter/").status_code
        == 404
    )


def test_mes_reservations_et_liste_admin(client_de, client_admin, passager, reservation):
    mes = client_de(passager).get("/api/v1/reservations/", {"statut": "demandee"}).json()
    assert mes["reponse"]["count"] == 1
    assert client_admin.get("/api/v1/admin/reservations/").json()["reponse"]["count"] == 1
