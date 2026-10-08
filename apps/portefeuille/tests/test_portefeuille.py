import pytest

from apps.core.exceptions import DonneesInvalides
from apps.portefeuille import services
from apps.portefeuille.models import Transaction

pytestmark = pytest.mark.django_db


def test_recharge_simulee_avec_reference(utilisateur):
    solde = services.recharger(utilisateur, 2000)

    assert solde.total == solde.disponible == 2000
    assert Transaction.objects.get().reference_externe.startswith("SIM-RCH-")


def test_recharge_et_retrait_sous_le_minimum(utilisateur):
    with pytest.raises(DonneesInvalides):
        services.recharger(utilisateur, 100)
    with pytest.raises(DonneesInvalides):
        services.retirer(utilisateur, 100)


def test_retrait_limite_au_disponible(passager, reservation):
    with pytest.raises(services.SoldeInsuffisant):
        services.retirer(passager, 4800)  # 300 F sont bloqués

    assert services.retirer(passager, 4700).total == 300


def test_api_portefeuille(client_de, passager, reservation):
    client = client_de(passager)

    solde = client.get("/api/v1/portefeuille/").json()["reponse"]
    assert solde == {"total": 5000, "bloque": 300, "disponible": 4700}
    reponse = client.post("/api/v1/portefeuille/recharger/", {"montant": 1000})
    assert reponse.json()["reponse"]["total"] == 6000
    historique = client.get("/api/v1/portefeuille/transactions/").json()["reponse"]
    assert historique["count"] == 3
    reponse = client.post("/api/v1/portefeuille/retirer/", {"montant": 9999})
    assert reponse.status_code == 409
    assert reponse.json()["reponse"]["code"] == "SOLDE_INSUFFISANT"
