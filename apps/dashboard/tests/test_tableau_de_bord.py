from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from freezegun import freeze_time

from apps.accounts.tests.factories import UserFactory
from apps.confiance.services import signaler
from apps.dashboard.services import bornes
from apps.kyc.models import KycDossier, StatutKyc
from apps.portefeuille import services as portefeuille
from apps.portefeuille.models import StatutTransaction, Transaction, TypeTransaction
from apps.reservations import services as reservations
from apps.reservations.code_depart import calculer_code
from apps.reservations.models import StatutReservation
from apps.trajets.services import terminer
from conftest import demander, publier_trajet

pytestmark = pytest.mark.django_db

URL = "/api/v1/admin/tableau-de-bord/"
LOME = ZoneInfo("Africa/Lome")


@pytest.mark.parametrize(
    ("periode", "debut"),
    [("7j", date(2026, 10, 2)), ("30j", date(2026, 9, 9)), ("mois", date(2026, 10, 1))],
)
def test_bornes_de_la_periode(periode, debut):
    maintenant = datetime(2026, 10, 8, 15, 30, tzinfo=LOME)

    premier, dernier = bornes(periode, maintenant)

    assert premier == datetime.combine(debut, datetime.min.time(), tzinfo=LOME)
    assert dernier == maintenant


def _trajet_termine(conducteur, passager):
    """Trajet publié pour dans 2 h puis terminé : une réservation passée par « en_cours »."""
    trajet = publier_trajet(conducteur)
    reservation = reservations.accepter(conducteur, demander(passager, trajet).id)
    reservations.saisir_code(conducteur, reservation.id, calculer_code(reservation))
    terminer(conducteur, trajet.id)
    return reservation


def test_tableau_de_bord_sur_30_jours(client_admin, conducteur, passager):
    with freeze_time("2026-10-08 06:00:00") as horloge:
        reservation = _trajet_termine(conducteur, passager)
        reservations.confirmer_arrivee(passager, reservation.id)
        publier_trajet(conducteur, places=2)  # publié, pas encore parti
        horloge.move_to("2026-10-08 12:00:00")
        corps = client_admin.get(URL).json()["reponse"]

    assert corps["periode"] == {"code": "30j", "debut": "2026-09-09", "fin": "2026-10-08"}
    assert corps["indicateurs"] == {
        "trajets_publies": 2,
        "trajets_termines": 1,
        "passagers_transportes": 1,
        "economies_realisees": 255,  # net des conducteurs
        "commissions_kovoit": 45,  # lignes « commission » du journal
        "utilisateurs_verifies": 2,
        "conducteurs_verifies": 1,
    }
    assert len(corps["evolution"]) == 30
    assert corps["evolution"][-1] == {"date": "2026-10-08", "trajets": 1, "passagers": 1}
    assert corps["evolution"][0] == {"date": "2026-09-09", "trajets": 0, "passagers": 0}
    assert set(corps["reservations_par_statut"]) == set(StatutReservation.values)
    assert corps["reservations_par_statut"]["cloturee"] == 1
    assert sum(corps["reservations_par_statut"].values()) == 1


def test_la_periode_exclut_les_donnees_anterieures(client_admin, conducteur, passager):
    with freeze_time("2026-09-20 06:00:00") as horloge:
        _trajet_termine(conducteur, passager)
        horloge.move_to("2026-10-08 12:00:00")
        corps = client_admin.get(URL, {"periode": "7j"}).json()["reponse"]

    assert len(corps["evolution"]) == 7
    assert corps["indicateurs"]["trajets_publies"] == 0
    assert corps["indicateurs"]["trajets_termines"] == 0
    assert sum(corps["reservations_par_statut"].values()) == 0
    # Les vérifications KYC sont un état actuel, indépendant de la période
    assert corps["indicateurs"]["conducteurs_verifies"] == 1


def test_files_de_travail(client_admin, conducteur, passager):
    reservation = _trajet_termine(conducteur, passager)
    signaler(passager, reservation.id, "Le conducteur a fait un détour important.")
    KycDossier.objects.create(
        utilisateur=UserFactory(), type="passager", statut=StatutKyc.EN_ATTENTE
    )

    corps = client_admin.get(URL, {"periode": "mois"}).json()["reponse"]

    assert corps["a_traiter"] == {
        "kyc_en_attente": 1,
        "signalements_ouverts": 1,
        "litiges": 1,
        "retraits_en_attente": 0,
    }


def test_retraits_en_attente_seulement(client_admin_sans_role, admin_sans_role, passager, settings):
    """Retraits à verser (D-55) : ni les retraits déjà versés ou refusés, ni les recharges en
    attente."""
    portefeuille.retirer(passager, 1000, "flooz")  # simulation : validee tout de suite
    settings.PAIEMENT_PROVIDER = "apps.portefeuille.paygate.PayGateProvider"
    settings.PAYGATE_CALLBACK_SECRET = "cle-callback"
    a_refuser = portefeuille.retirer(passager, 500, "flooz")
    portefeuille.retirer(passager, 500, "mixx")
    Transaction.objects.create(
        utilisateur=passager, type=TypeTransaction.RECHARGE, montant=2000,
        statut=StatutTransaction.EN_ATTENTE,
    )  # fmt: skip

    reponse = client_admin_sans_role.get(URL)

    assert reponse.status_code == 200
    assert reponse.json()["reponse"]["a_traiter"]["retraits_en_attente"] == 2
    portefeuille.traiter_retrait(admin_sans_role, a_refuser.id, verse=False, motif="Numéro faux")
    reponse = client_admin_sans_role.get(URL)
    assert reponse.json()["reponse"]["a_traiter"]["retraits_en_attente"] == 1


def test_signale_les_donnees_de_demo(client_admin):
    assert client_admin.get(URL).json()["reponse"]["donnees_demo"] is False

    UserFactory(email="afi.demo@kovoit.tg")
    assert client_admin.get(URL).json()["reponse"]["donnees_demo"] is True


def test_detecte_les_comptes_de_seed_backoffice(client_admin):
    UserFactory(email="kodjo.mensah@demo.kovoit.tg")

    assert client_admin.get(URL).json()["reponse"]["donnees_demo"] is True


def test_periode_invalide(client_admin):
    reponse = client_admin.get(URL, {"periode": "1an"})

    assert reponse.status_code == 400
    assert "periode" in reponse.json()["reponse"]["erreurs"]


def test_reserve_a_l_admin(client_utilisateur):
    assert client_utilisateur.get(URL).status_code == 403
