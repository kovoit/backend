"""Simulation avec versement manuel : recharge immédiate, retrait versé depuis le back-office."""

import pytest

from apps.audit.models import EvenementAudit
from apps.portefeuille import services

pytestmark = pytest.mark.django_db

URL = "/api/v1/admin/transactions/"


@pytest.fixture(autouse=True)
def versement_manuel(settings):
    settings.PAIEMENT_PROVIDER = "apps.portefeuille.provider.SimulationVersementManuelProvider"


def test_recharge_validee_immediatement(utilisateur):
    ligne = services.recharger(utilisateur, 2000, "flooz")

    assert ligne.statut == "validee"
    assert services.solde(utilisateur).disponible == 2000


def test_retrait_en_attente_puis_verse_par_la_finance(client_admin, utilisateur):
    services.recharger(utilisateur, 5000, "flooz")
    retrait = services.retirer(utilisateur, 1000, "mixx")
    assert retrait.statut == "en_attente"

    a_verser = client_admin.get(URL, {"type": "retrait", "statut": "en_attente"})
    assert a_verser.status_code == 200
    assert [ligne["id"] for ligne in a_verser.json()["reponse"]["results"]] == [str(retrait.id)]

    reponse = client_admin.post(
        f"{URL}{retrait.id}/verser/", {"reference": "MIXX-VIR-7"}, format="json"
    )

    assert reponse.status_code == 200
    ligne = reponse.json()["reponse"]
    assert (ligne["statut"], ligne["reference_externe"]) == ("validee", "MIXX-VIR-7")
    assert services.solde(utilisateur).total == 4000
    evenement = EvenementAudit.objects.get(action="portefeuille.verser")
    assert evenement.resultat == "succes"
