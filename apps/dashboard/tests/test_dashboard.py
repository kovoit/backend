import pytest

from apps.reservations import services as reservations
from apps.reservations.code_depart import calculer_code
from apps.trajets.services import terminer

pytestmark = pytest.mark.django_db


@pytest.fixture
def trajet_cloture(passager, conducteur, reservation_acceptee):
    reservations.saisir_code(
        conducteur, reservation_acceptee.id, calculer_code(reservation_acceptee)
    )
    terminer(conducteur, reservation_acceptee.trajet_id)
    reservations.confirmer_arrivee(passager, reservation_acceptee.id)
    return reservation_acceptee.trajet


def test_economies_du_conducteur(client_de, conducteur, trajet_cloture):
    economies = client_de(conducteur).get("/api/v1/moi/economies/").json()["reponse"]

    assert (
        economies["mois_en_cours"] == economies["total"] == 255
    )  # 300 F payés − 45 F de commission Kovoit (15 %)
    assert economies["par_trajet"][0]["trajet_id"] == str(trajet_cloture.id)


def test_d39_l_ancienne_route_des_indicateurs_n_existe_plus(client_admin, admin):
    """D-39 : GET /api/v1/admin/indicateurs/ est supprimée, même pour un admin doté des quatre
    rôles. Ses chiffres sont servis par /api/v1/admin/tableau-de-bord/."""
    assert admin.groups.count() == 4

    reponse = client_admin.get("/api/v1/admin/indicateurs/")

    assert reponse.status_code == 404
    corps = reponse.json()
    assert corps["statut"] == "failed"
    assert corps["message"]
    assert corps["reponse"]["code"] == "RESSOURCE_INTROUVABLE"
