from datetime import timedelta

import pytest

from apps.confiance import services
from apps.core.exceptions import Conflit, DonneesInvalides
from apps.parametres.services import modifier_param
from apps.portefeuille import services as portefeuille
from apps.reservations import services as reservations
from apps.reservations.code_depart import calculer_code
from apps.reservations.models import StatutReservation as S
from apps.trajets.services import terminer
from conftest import demander, publier_trajet

pytestmark = pytest.mark.django_db


@pytest.fixture
def reservation_terminee(conducteur, reservation_acceptee):
    reservations.saisir_code(
        conducteur, reservation_acceptee.id, calculer_code(reservation_acceptee)
    )
    terminer(conducteur, reservation_acceptee.trajet_id)
    reservation_acceptee.refresh_from_db()
    return reservation_acceptee


def test_note_apres_le_trajet_une_seule_fois(passager, conducteur, reservation_terminee):
    note = services.noter(passager, reservation_terminee.id, 5, "Très ponctuel")

    assert note.cible == conducteur
    with pytest.raises(Conflit):
        services.noter(passager, reservation_terminee.id, 4)
    assert services.resume_confiance(conducteur)["note_moyenne"] == 5.0


def test_note_impossible_avant_le_trajet(passager, reservation):
    with pytest.raises(Conflit):
        services.noter(passager, reservation.id, 5)


def test_signalement_apres_trajet_ouvre_un_litige_et_gele_le_montant(
    passager, admin, conducteur, reservation_terminee
):
    signalement = services.signaler(passager, reservation_terminee.id, "Conduite dangereuse")
    reservation_terminee.refresh_from_db()
    assert reservation_terminee.statut == S.LITIGE
    assert reservations.cloturer_automatiquement() == 0

    with pytest.raises(DonneesInvalides):
        services.traiter_signalement(admin, signalement.id, "Vérifié")
    services.traiter_signalement(admin, signalement.id, "Fondé", "rembourser_passager")

    reservation_terminee.refresh_from_db()
    assert reservation_terminee.statut == S.CLOTUREE
    assert portefeuille.solde(passager).total == 5000
    assert portefeuille.solde(conducteur).total == 0
    with pytest.raises(Conflit):
        services.traiter_signalement(admin, signalement.id, "Encore")


def test_litige_tranche_en_faveur_du_conducteur(passager, admin, conducteur, reservation_terminee):
    signalement = services.signaler(passager, reservation_terminee.id, "Retard")

    services.traiter_signalement(admin, signalement.id, "Non fondé", "crediter_conducteur")

    assert portefeuille.solde(conducteur).total == 300


def test_fiabilite_et_suspension_automatique(passager, conducteur):
    modifier_param("seuil_incidents", 2)
    for _ in range(2):
        trajet = publier_trajet(conducteur, depart_dans=timedelta(minutes=10))
        reservation = reservations.accepter(conducteur, demander(passager, trajet).id)
        reservations.annuler(passager, reservation.id)

    passager.refresh_from_db()
    assert services.fiabilite_pct(passager) == 0
    assert passager.statut_compte == "suspendu"


def test_api_note_signalement_et_profil_public(
    client_de, client_admin, passager, conducteur, reservation_terminee
):
    url = f"/api/v1/reservations/{reservation_terminee.id}/"
    assert client_de(passager).post(url + "note/", {"note": 4}).status_code == 201
    assert client_de(passager).post(url + "note/", {"note": 9}).status_code == 400
    reponse = client_de(conducteur).post(url + "signalement/", {"motif": "Passager impoli"})
    assert reponse.status_code == 201

    profil = client_de(passager).get(f"/api/v1/utilisateurs/{conducteur.id}/").json()["reponse"]
    assert profil["confiance"]["note_moyenne"] == 4.0
    assert "email" not in profil

    liste = client_admin.get("/api/v1/admin/signalements/", {"statut": "ouvert"}).json()
    signalement_id = liste["reponse"]["results"][0]["id"]
    reponse = client_admin.post(
        f"/api/v1/admin/signalements/{signalement_id}/traiter/",
        {"resolution": "Médiation faite", "decision": "crediter_conducteur"},
        format="json",
    )
    assert reponse.json()["reponse"]["statut"] == "traite"
