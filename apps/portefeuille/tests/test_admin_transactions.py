"""Back-office : journal des transactions et retraits à verser (API /api/v1/admin/)."""

import pytest

from apps.audit.models import EvenementAudit
from apps.portefeuille import services

pytestmark = pytest.mark.django_db

URL = "/api/v1/admin/transactions/"


@pytest.fixture
def retraits(passager, settings):
    """Deux retraits en attente (versement manuel, comme avec PayGate)."""
    settings.PAIEMENT_PROVIDER = "apps.portefeuille.paygate.PayGateProvider"
    settings.PAYGATE_CALLBACK_SECRET = "cle-callback"
    return services.retirer(passager, 1000, "flooz"), services.retirer(passager, 500, "mixx")


def _resultats(reponse):
    assert reponse.status_code == 200
    return reponse.json()["reponse"]["results"]


def test_retraits_a_verser_les_plus_anciens_d_abord(client_admin, retraits):
    lignes = _resultats(client_admin.get(URL, {"type": "retrait", "statut": "en_attente"}))

    assert [ligne["id"] for ligne in lignes] == [str(retraits[0].id), str(retraits[1].id)]
    premiere = lignes[0]
    assert (premiere["montant"], premiere["moyen_paiement"]) == (1000, "flooz")
    assert premiere["telephone"] and premiere["utilisateur"]["email"]


def test_filtres_et_recherche(client_admin, passager, retraits):
    assert len(_resultats(client_admin.get(URL, {"moyen": "mixx"}))) == 1
    tout = _resultats(client_admin.get(URL, {"recherche": passager.email}))
    assert {ligne["type"] for ligne in tout} >= {"retrait", "recharge"}
    assert _resultats(client_admin.get(URL, {"recherche": "personne-inconnue"})) == []
    assert client_admin.get(URL, {"type": "inconnu"}).status_code == 400


def test_verser_un_retrait_avec_sa_reference(client_admin, passager, retraits):
    reponse = client_admin.post(
        f"{URL}{retraits[0].id}/verser/", {"reference": "FLZ-VIR-42"}, format="json"
    )

    assert reponse.status_code == 200
    ligne = reponse.json()["reponse"]
    assert (ligne["statut"], ligne["reference_externe"]) == ("validee", "FLZ-VIR-42")
    assert services.solde(passager).total == 3500  # 1 000 versés, 500 toujours retenus
    evenement = EvenementAudit.objects.get(action="portefeuille.verser")
    assert evenement.resultat == "succes"

    deja = client_admin.post(f"{URL}{retraits[0].id}/verser/", {"reference": "X42"}, format="json")
    assert deja.status_code == 409


def test_refuser_un_retrait_avec_un_motif(client_admin, passager, retraits):
    sans_motif = client_admin.post(f"{URL}{retraits[1].id}/refuser/", {}, format="json")
    assert sans_motif.status_code == 400

    reponse = client_admin.post(
        f"{URL}{retraits[1].id}/refuser/", {"motif": "Numéro Mixx invalide"}, format="json"
    )

    assert reponse.json()["reponse"]["statut"] == "echouee"
    assert services.solde(passager).disponible == 5000 - 1000
    evenement = EvenementAudit.objects.get(action="portefeuille.verser")
    assert (evenement.resultat, evenement.details["motif"]) == ("refus", "Numéro Mixx invalide")


def test_verser_exige_une_reference(client_admin, retraits):
    reponse = client_admin.post(f"{URL}{retraits[0].id}/verser/", {}, format="json")
    assert reponse.status_code == 400


def test_reserve_aux_admins(client_utilisateur, retraits):
    assert client_utilisateur.get(URL).status_code == 403
    reponse = client_utilisateur.post(
        f"{URL}{retraits[0].id}/verser/", {"reference": "FLZ-1"}, format="json"
    )
    assert reponse.status_code == 403
