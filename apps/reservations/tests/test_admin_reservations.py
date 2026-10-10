import pytest
from freezegun import freeze_time

from apps.accounts.tests.factories import UserFactory
from apps.confiance.services import signaler
from apps.kyc.tests.factories import verifier_kyc
from apps.portefeuille import services as portefeuille
from apps.reservations import services as reservations
from apps.reservations.code_depart import calculer_code
from apps.trajets.services import terminer
from conftest import demander, publier_trajet

pytestmark = pytest.mark.django_db

URL = "/api/v1/admin/reservations/"


def _passager(prenom: str):
    utilisateur = UserFactory(prenom=prenom)
    verifier_kyc(utilisateur, "passager")
    portefeuille.recharger(utilisateur, 5000, "flooz")
    return utilisateur


def test_liste_au_format_admin(client_admin, reservation, passager, conducteur):
    ligne = client_admin.get(URL).json()["reponse"]["results"][0]

    assert ligne["passager"]["telephone"] == passager.telephone
    assert ligne["conducteur"]["id"] == str(conducteur.id)
    assert ligne["point_libelle"] == "Carrefour Adidogomé"
    assert ligne["trajet_id"] == str(reservation.trajet_id)
    assert "code_depart" not in ligne


def test_recherche_passager_ou_conducteur(client_admin, trajet, reservation):
    autre = demander(_passager("Yawa"), trajet)

    par_passager = client_admin.get(URL, {"recherche": "yawa"}).json()["reponse"]["results"]
    par_conducteur = client_admin.get(URL, {"recherche": "kodjo"}).json()["reponse"]

    assert [ligne["id"] for ligne in par_passager] == [str(autre.id)]
    assert par_conducteur["count"] == 2


def test_filtre_par_trajet(client_admin, conducteur, reservation):
    autre_trajet = publier_trajet(conducteur)
    demander(_passager("Ama"), autre_trajet)

    lignes = client_admin.get(URL, {"trajet": str(reservation.trajet_id)}).json()["reponse"]

    assert [ligne["id"] for ligne in lignes["results"]] == [str(reservation.id)]


def test_filtres_invalides(client_admin):
    reponse = client_admin.get(URL, {"statut": "perdue", "trajet": "abc"})

    assert reponse.status_code == 400
    assert set(reponse.json()["reponse"]["erreurs"]) == {"statut", "trajet"}


def test_detail_historique_dans_l_ordre_du_cycle(client_admin, passager, conducteur):
    with freeze_time("2026-10-08 06:00") as horloge:
        trajet = publier_trajet(conducteur)
        reservation = demander(passager, trajet)
        horloge.tick(60)
        reservation = reservations.accepter(conducteur, reservation.id)
        horloge.move_to("2026-10-08 08:05")
        reservations.saisir_code(conducteur, reservation.id, calculer_code(reservation))
        horloge.move_to("2026-10-08 08:45")
        terminer(conducteur, trajet.id)
        horloge.tick(600)
        signaler(passager, reservation.id, "Déposé loin de mon arrêt.")

    detail = client_admin.get(f"{URL}{reservation.id}/").json()["reponse"]

    assert [etape["statut"] for etape in detail["historique"]] == [
        "demandee",
        "acceptee",
        "en_cours",
        "terminee",
        "litige",
    ]
    assert detail["historique"][0]["le"].startswith("2026-10-08T06:00")
    assert detail["statut"] == "litige"
    assert detail["signalements"][0]["motif"] == "Déposé loin de mon arrêt."
    assert detail["signalements"][0]["statut"] == "ouvert"
    assert detail["point"]["ordre"] == 1
    assert detail["arrivee"]["libelle"] == "Grand Marché"
    assert isinstance(detail["distance_km"], float)


def test_detail_ne_montre_jamais_le_code_de_depart(client_admin, reservation_acceptee):
    corps = client_admin.get(f"{URL}{reservation_acceptee.id}/").content.decode()

    assert "code_depart" not in corps
    assert "code_depart_sel" not in corps
    assert "essais_code" not in corps


def test_detail_introuvable(client_admin):
    assert client_admin.get(f"{URL}00000000-0000-0000-0000-000000000000/").status_code == 404


def test_reserve_aux_admins(client_utilisateur, reservation):
    assert client_utilisateur.get(URL).status_code == 403
    assert client_utilisateur.get(f"{URL}{reservation.id}/").status_code == 403
