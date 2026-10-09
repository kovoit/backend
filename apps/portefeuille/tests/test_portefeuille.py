import pytest

from apps.core.exceptions import DonneesInvalides
from apps.portefeuille import services
from apps.portefeuille.models import Transaction

pytestmark = pytest.mark.django_db


def test_recharge_simulee_par_flooz(utilisateur):
    solde = services.recharger(utilisateur, 2000, "flooz")

    assert solde.total == solde.disponible == 2000
    transaction = Transaction.objects.get()
    assert transaction.moyen_paiement == "flooz"
    assert transaction.reference_externe.startswith("SIM-FLOOZ-")


def test_moyen_inconnu_refuse(utilisateur):
    with pytest.raises(DonneesInvalides):
        services.recharger(utilisateur, 2000, "tmoney")


def test_recharge_et_retrait_sous_le_minimum(utilisateur):
    with pytest.raises(DonneesInvalides):
        services.recharger(utilisateur, 100, "mixx")
    with pytest.raises(DonneesInvalides):
        services.retirer(utilisateur, 100, "mixx")


def test_retrait_limite_au_disponible(passager, reservation):
    with pytest.raises(services.SoldeInsuffisant):
        services.retirer(passager, 4800, "mixx")  # 300 F sont bloqués

    assert services.retirer(passager, 4700, "mixx").total == 300


def test_apercu_paiement(utilisateur):
    services.recharger(utilisateur, 500, "flooz")

    apercu = services.apercu_paiement(utilisateur, 800)

    assert apercu["solde_disponible"] == 500
    assert apercu["complement_a_payer"] == 300
    assert [m["code"] for m in apercu["moyens_paiement"]] == ["flooz", "mixx"]


def test_api_portefeuille(client_de, passager, reservation):
    client = client_de(passager)

    solde = client.get("/api/v1/portefeuille/").json()["reponse"]
    assert solde == {"total": 5000, "bloque": 300, "disponible": 4700}
    moyens = client.get("/api/v1/portefeuille/moyens/").json()["reponse"]
    assert moyens == [
        {"code": "flooz", "libelle": "Flooz (Moov Africa)"},
        {"code": "mixx", "libelle": "Mixx (Togocom)"},
    ]
    reponse = client.post("/api/v1/portefeuille/recharger/", {"montant": 1000, "moyen": "mixx"})
    assert reponse.json()["reponse"]["total"] == 6000
    assert client.post("/api/v1/portefeuille/recharger/", {"montant": 1000}).status_code == 400
    historique = client.get("/api/v1/portefeuille/transactions/").json()["reponse"]
    assert historique["count"] == 3
    reponse = client.post("/api/v1/portefeuille/retirer/", {"montant": 9999, "moyen": "flooz"})
    assert reponse.status_code == 409
    assert reponse.json()["reponse"]["code"] == "SOLDE_INSUFFISANT"
