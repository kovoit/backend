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

    assert economies["mois_en_cours"] == economies["total"] == 300
    assert economies["par_trajet"][0]["trajet_id"] == str(trajet_cloture.id)


def test_indicateurs_admin(client_admin, trajet_cloture):
    indicateurs = client_admin.get("/api/v1/admin/indicateurs/").json()["reponse"]

    assert indicateurs["trajets_termines"] == 1
    assert indicateurs["passagers_transportes"] == 1
    assert indicateurs["economies_realisees"] == 300
    assert indicateurs["conducteurs_verifies"] == 1


def test_indicateurs_reserves_a_l_admin(client_utilisateur):
    assert client_utilisateur.get("/api/v1/admin/indicateurs/").status_code == 403
