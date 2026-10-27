"""D-57 : codes HTTP de POST /portefeuille/recharger/ (201 validée, 202 en attente, 200 échouée)
et non-régression de POST /portefeuille/retirer/ (201 / 202)."""

import pytest

from apps.audit.models import EvenementAudit
from apps.portefeuille import services
from apps.portefeuille.models import Transaction
from apps.portefeuille.paygate import PayGateProvider
from apps.portefeuille.provider import PaiementIndisponible, Resultat
from apps.portefeuille.services.commun import ecrire

pytestmark = pytest.mark.django_db

RECHARGER = "/api/v1/portefeuille/recharger/"
RETIRER = "/api/v1/portefeuille/retirer/"
SIMULATION = "apps.portefeuille.provider.SimulationPaiementProvider"


@pytest.fixture
def simulation(settings):
    settings.PAIEMENT_PROVIDER = SIMULATION
    settings.PAYGATE_AUTH_TOKEN = ""


def _poster(client_de, utilisateur, chemin=RECHARGER, montant=2000):
    return client_de(utilisateur).post(chemin, {"montant": montant, "moyen": "flooz"})


def test_recharge_en_attente_renvoie_202(client_de, utilisateur, paygate):
    reponse = _poster(client_de, utilisateur)

    assert reponse.status_code == 202
    corps = reponse.json()
    assert corps["statut"] == "success"
    assert corps["message"] == (
        "Validez le paiement sur votre téléphone pour terminer l'opération."
    )
    assert corps["reponse"]["transaction"]["statut"] == "en_attente"


def test_recharge_validee_en_simulation_renvoie_201(client_de, utilisateur, simulation):
    reponse = _poster(client_de, utilisateur)

    assert reponse.status_code == 201
    corps = reponse.json()
    assert (corps["statut"], corps["message"]) == ("success", "Opération effectuée.")
    assert corps["reponse"]["transaction"]["statut"] == "validee"
    assert corps["reponse"]["solde"]["total"] == 2000


def _callback_d_echec_pendant_l_appel(monkeypatch, paygate, statut, panne=False):
    """`collecter` : PayGate enregistre la demande, puis son callback d'échec (expiré ou
    annulé) arrive avant la réponse, qui est tardive ou perdue."""
    original = PayGateProvider.collecter

    def collecter(self, utilisateur, montant, moyen, telephone, identifiant):
        original(self, utilisateur, montant, moyen, telephone, identifiant)
        paygate.statut_paiement = statut
        services.confirmer_par_callback(identifiant)
        if panne:
            raise PaiementIndisponible()
        return Resultat("PG-REPONSE-TARDIVE", "en_attente")

    monkeypatch.setattr(PayGateProvider, "collecter", collecter)


@pytest.mark.parametrize("panne", [False, True], ids=["reponse_tardive", "reponse_perdue"])
@pytest.mark.parametrize(("statut", "code"), [(4, "EXPIRE"), (6, "ANNULE")])
def test_callback_d_echec_pendant_l_appel_renvoie_200_echouee(
    client_de, utilisateur, paygate, monkeypatch, statut, code, panne
):
    ecrire(utilisateur, "recharge", 3000, reference="SIM-AVANT")  # solde déjà présent
    _callback_d_echec_pendant_l_appel(monkeypatch, paygate, statut, panne)

    reponse = _poster(client_de, utilisateur)

    assert reponse.status_code == 200
    corps = reponse.json()
    assert (corps["statut"], corps["message"]) == ("success", "Le paiement n'a pas abouti.")
    assert corps["reponse"]["transaction"]["statut"] == "echouee"
    assert corps["reponse"]["solde"] == {"total": 3000, "bloque": 0, "disponible": 3000}
    ligne = Transaction.objects.get(id=corps["reponse"]["transaction"]["id"])
    assert (ligne.statut, ligne.reference_externe) == ("echouee", "PG-123")
    echec = EvenementAudit.objects.get(action="paiement.confirmer")
    assert (echec.resultat, echec.code_motif) == ("echec", code)
    assert not EvenementAudit.objects.filter(action="paiement.initier").exists()


def test_retrait_valide_en_simulation_renvoie_201(client_de, utilisateur, simulation):
    ecrire(utilisateur, "recharge", 3000, reference="SIM-AVANT")

    reponse = _poster(client_de, utilisateur, RETIRER, 1000)

    assert reponse.status_code == 201
    corps = reponse.json()
    assert (corps["statut"], corps["message"]) == ("success", "Opération effectuée.")
    assert corps["reponse"]["transaction"]["statut"] == "validee"
    assert corps["reponse"]["solde"]["total"] == 2000


def test_retrait_en_attente_avec_paygate_renvoie_202(client_de, utilisateur, paygate):
    ecrire(utilisateur, "recharge", 3000, reference="SIM-AVANT")

    reponse = _poster(client_de, utilisateur, RETIRER, 1000)

    assert reponse.status_code == 202
    corps = reponse.json()
    assert corps["statut"] == "success"
    assert corps["reponse"]["transaction"]["statut"] == "en_attente"
    assert corps["reponse"]["solde"]["disponible"] == 2000
