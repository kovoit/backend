"""Client HTTP PayGate (urlopen simulé : aucun appel réseau)."""

import pytest


def test_client_http_paygate(settings, monkeypatch):
    import io
    import json
    import urllib.error

    from apps.portefeuille import paygate
    from apps.portefeuille.provider import PaiementIndisponible

    settings.PAYGATE_AUTH_TOKEN = "jeton"
    settings.PAYGATE_URL = "https://paygate.test/"
    envoyees = []

    def urlopen(requete, timeout):
        envoyees.append((requete.full_url, json.loads(requete.data), timeout))
        return io.StringIO(json.dumps({"tx_reference": "PG-9", "status": 6}))

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    resultat = paygate.PayGateProvider().verifier("id-1", "")
    assert envoyees == [
        ("https://paygate.test/api/v2/status", {"auth_token": "jeton", "identifier": "id-1"}, 15)
    ]
    assert (resultat.statut, resultat.code, resultat.reference) == ("echouee", "ANNULE", "PG-9")

    with pytest.raises(PaiementIndisponible) as refus:
        paygate.PayGateProvider().collecter(None, 500, "flooz", "+22890000001", "id-2")
    assert refus.value.code == "DOUBLON"

    def panne(requete, timeout):
        raise urllib.error.URLError("hors ligne")

    monkeypatch.setattr("urllib.request.urlopen", panne)
    with pytest.raises(PaiementIndisponible):
        paygate.PayGateProvider().verifier("id-1", "")
