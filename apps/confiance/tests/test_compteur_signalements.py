"""F-062 : badge du menu « Signalements & litiges » (D-07, D-28, D-41)."""

import pytest

from apps.accounts.tests.factories import AdminFactory, UserFactory
from apps.confiance.services import signaler, traiter_signalement
from apps.kyc.tests.factories import verifier_kyc
from apps.portefeuille import services as portefeuille
from apps.reservations import services as reservations
from apps.reservations.code_depart import calculer_code
from apps.trajets.services import terminer
from conftest import demander

pytestmark = pytest.mark.django_db

URL = "/api/v1/admin/signalements/compteur/"


@pytest.fixture
def deux_ouverts_dont_un_litige(passager, conducteur, trajet, admin):
    """Un litige (signalement ouvert), un signalement ouvert sur une réservation clôturée et un
    signalement traité : le compteur vaut 2."""
    passagere = UserFactory(prenom="Kafui")
    verifier_kyc(passagere, "passager")
    portefeuille.recharger(passagere, 5000, "flooz")
    premiere = reservations.accepter(conducteur, demander(passager, trajet).id)
    seconde = reservations.accepter(conducteur, demander(passagere, trajet).id)
    for reservation in (premiere, seconde):
        reservations.saisir_code(conducteur, reservation.id, calculer_code(reservation))
    terminer(conducteur, trajet.id)
    reservations.confirmer_arrivee(passagere, seconde.id)

    signaler(passager, premiere.id, "Déposé loin de mon arrêt.")  # litige
    signaler(passagere, seconde.id, "Comportement irrespectueux.")
    traite = signaler(passagere, seconde.id, "Retard au départ.")
    traiter_signalement(admin, traite.id, "Conducteur contacté.")


def test_admin_moderation_recoit_le_nombre_de_signalements_ouverts(
    client_de, deux_ouverts_dont_un_litige
):
    reponse = client_de(AdminFactory(roles=["moderation"])).get(URL)

    assert reponse.status_code == 200
    assert reponse.json() == {
        "statut": "success",
        "message": "Compteur récupéré.",
        "reponse": {"signalements_ouverts": 2},
    }


def test_le_compteur_est_celui_du_tableau_de_bord(client_admin, deux_ouverts_dont_un_litige):
    a_traiter = client_admin.get("/api/v1/admin/tableau-de-bord/").json()["reponse"]["a_traiter"]

    assert a_traiter["litiges"] == 1  # le litige n'est pas ajouté une seconde fois
    assert client_admin.get(URL).json()["reponse"]["signalements_ouverts"] == 2
    assert a_traiter["signalements_ouverts"] == 2


def test_zero_sans_signalement(client_admin):
    assert client_admin.get(URL).json()["reponse"] == {"signalements_ouverts": 0}


def test_admin_finance_refuse(client_de):
    reponse = client_de(AdminFactory(roles=["finance"])).get(URL)

    assert reponse.status_code == 403
    assert reponse.json()["statut"] == "failed"
    assert reponse.json()["reponse"]["code"] == "ROLE_ADMIN_INSUFFISANT"


def test_non_admin_refuse(client_utilisateur):
    reponse = client_utilisateur.get(URL)

    assert reponse.status_code == 403
    assert reponse.json()["statut"] == "failed"


def test_la_route_ne_masque_pas_le_detail(client_admin, passager, conducteur, reservation_acceptee):
    reservations.saisir_code(
        conducteur, reservation_acceptee.id, calculer_code(reservation_acceptee)
    )
    signalement = signaler(passager, reservation_acceptee.id, "Conduite brusque.")

    reponse = client_admin.get(f"/api/v1/admin/signalements/{signalement.id}/")

    assert reponse.status_code == 200
    assert reponse.json()["reponse"]["id"] == str(signalement.id)
