import pytest
from freezegun import freeze_time

from apps.confiance.services import signaler
from apps.portefeuille import services as portefeuille
from apps.reservations import services as reservations
from apps.reservations.code_depart import calculer_code
from apps.reservations.models import Reservation, StatutReservation
from apps.trajets.services import terminer
from conftest import demander

pytestmark = pytest.mark.django_db

URL = "/api/v1/admin/signalements/"
RESOLUTION = "Les deux parties ont été contactées par téléphone."


def _monter(conducteur, reservation):
    reservations.saisir_code(conducteur, reservation.id, calculer_code(reservation))


@pytest.fixture
def litige(passager, conducteur, reservation_acceptee):
    """Trajet terminé puis contesté : la réservation passe en litige, le montant reste gelé."""
    _monter(conducteur, reservation_acceptee)
    terminer(conducteur, reservation_acceptee.trajet_id)
    return signaler(passager, reservation_acceptee.id, "Déposé loin de mon arrêt.")


@pytest.fixture
def signalement_simple(passager, conducteur, reservation_acceptee):
    """Signalé pendant le trajet : pas de litige."""
    _monter(conducteur, reservation_acceptee)
    return signaler(conducteur, reservation_acceptee.id, "Passager très en retard au point.")


def _traiter(client, signalement, **donnees):
    return client.post(f"{URL}{signalement.id}/traiter/", donnees, format="json")


def test_liste_plus_anciens_d_abord(client_admin, passager, conducteur, trajet):
    with freeze_time("2026-10-08 06:00") as horloge:
        premiere = reservations.accepter(conducteur, demander(passager, trajet).id)
        _monter(conducteur, premiere)
        ancien = signaler(passager, premiere.id, "Conduite brusque.")
        horloge.tick(3600)
        recent = signaler(conducteur, premiere.id, "Passager impoli.")

    lignes = client_admin.get(URL, {"statut": "ouvert"}).json()["reponse"]["results"]

    assert [ligne["id"] for ligne in lignes] == [str(ancien.id), str(recent.id)]
    assert lignes[0]["auteur"]["telephone"] == passager.telephone
    assert lignes[0]["cible"]["id"] == str(conducteur.id)
    assert lignes[0]["reservation"] == {
        "id": str(premiere.id),
        "statut": "en_cours",
        "trajet_id": str(premiere.trajet_id),
    }


def test_detail(client_admin, litige, passager):
    detail = client_admin.get(f"{URL}{litige.id}/").json()["reponse"]

    assert detail["reservation"]["statut"] == "litige"
    assert detail["reservation"]["passager"]["id"] == str(passager.id)
    assert detail["resolution"] == ""
    assert detail["decision"] == ""
    assert detail["traite_par"] is None


def test_traitement_simple(client_admin, admin, signalement_simple):
    reponse = _traiter(client_admin, signalement_simple, resolution=RESOLUTION)

    corps = reponse.json()["reponse"]
    assert reponse.status_code == 200
    assert corps["statut"] == "traite"
    assert corps["resolution"] == RESOLUTION
    assert corps["traite_par"]["id"] == str(admin.id)
    assert corps["reservation"]["statut"] == "en_cours"


def test_resolution_trop_courte(client_admin, signalement_simple):
    reponse = _traiter(client_admin, signalement_simple, resolution="Vu.")

    assert reponse.status_code == 400
    assert "resolution" in reponse.json()["reponse"]["erreurs"]


def test_litige_exige_une_decision(client_admin, litige):
    reponse = _traiter(client_admin, litige, resolution=RESOLUTION)

    assert reponse.status_code == 400
    assert reponse.json()["reponse"]["code"] == "DECISION_REQUISE"


def test_litige_tranche_pour_le_conducteur_le_paie(client_admin, litige, conducteur):
    avant = portefeuille.solde(conducteur).disponible

    reponse = _traiter(client_admin, litige, resolution=RESOLUTION, decision="crediter_conducteur")

    assert reponse.json()["reponse"]["reservation"]["statut"] == "cloturee"
    assert reponse.json()["reponse"]["decision"] == "crediter_conducteur"
    reservation = Reservation.objects.get(pk=litige.reservation_id)
    assert portefeuille.solde(conducteur).disponible == avant + reservation.prix


def test_litige_tranche_pour_le_passager_le_rembourse(client_admin, litige, passager):
    avant = portefeuille.solde(passager).disponible
    reservation = Reservation.objects.get(pk=litige.reservation_id)

    _traiter(client_admin, litige, resolution=RESOLUTION, decision="rembourser_passager")

    reservation.refresh_from_db()
    assert reservation.statut == StatutReservation.CLOTUREE
    assert portefeuille.solde(passager).disponible == avant + reservation.montant_total


def test_deja_traite(client_admin, signalement_simple):
    _traiter(client_admin, signalement_simple, resolution=RESOLUTION)

    reponse = _traiter(client_admin, signalement_simple, resolution=RESOLUTION)

    assert reponse.status_code == 409
    assert reponse.json()["reponse"]["code"] == "DEJA_TRAITE"


def test_reserve_aux_admins(client_utilisateur, signalement_simple):
    assert client_utilisateur.get(URL).status_code == 403
    assert client_utilisateur.get(f"{URL}{signalement_simple.id}/").status_code == 403
    assert (
        _traiter(client_utilisateur, signalement_simple, resolution=RESOLUTION).status_code == 403
    )
