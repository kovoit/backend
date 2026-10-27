"""Faux PayGate partagé par les tests du portefeuille : aucun appel réseau."""

import pytest


class FauxPayGate:
    """Remplace paygate._appeler : enregistre les appels, répond selon `statut_paiement`."""

    def __init__(self):
        self.appels = []
        self.statut_paiement = 2  # en cours
        self.statut_initiation = 0

    def __call__(self, chemin, donnees):
        self.appels.append((chemin, donnees))
        if chemin == "/api/v1/pay":
            return {"tx_reference": "PG-123", "status": self.statut_initiation}
        return {
            "tx_reference": "PG-123",
            "payment_reference": "FLZ-789",
            "status": self.statut_paiement,
        }


@pytest.fixture
def paygate(settings, monkeypatch):
    settings.PAIEMENT_PROVIDER = "apps.portefeuille.paygate.PayGateProvider"
    settings.PAYGATE_AUTH_TOKEN = "jeton-marchand-secret"
    settings.PAYGATE_CALLBACK_SECRET = "cle-callback"
    faux = FauxPayGate()
    monkeypatch.setattr("apps.portefeuille.paygate._appeler", faux)
    return faux
