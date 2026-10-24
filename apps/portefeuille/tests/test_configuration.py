"""Le secret du callback PayGate est obligatoire en production."""

import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.portefeuille.configuration import verifier_configuration_paiement


@pytest.mark.parametrize(
    ("debug", "secret", "refuse"), [(False, "", True), (False, "s3cret", False), (True, "", False)]
)
def test_secret_callback_obligatoire_en_production(settings, debug, secret, refuse):
    settings.PAIEMENT_PROVIDER = "apps.portefeuille.paygate.PayGateProvider"
    settings.DEBUG, settings.PAYGATE_CALLBACK_SECRET = debug, secret
    if refuse:
        with pytest.raises(ImproperlyConfigured):
            verifier_configuration_paiement()
    else:
        verifier_configuration_paiement()


def test_paiement_simule_sans_secret(settings):
    settings.PAIEMENT_PROVIDER = "apps.portefeuille.provider.SimulationPaiementProvider"
    settings.DEBUG, settings.PAYGATE_CALLBACK_SECRET = False, ""
    verifier_configuration_paiement()


@pytest.mark.parametrize(
    "saisi", ["90123456", "90 12 34 56", "+228 90 12 34 56", "0022890123456", "22890123456"]
)
def test_numero_mobile_money_normalise_a_8_chiffres(saisi):
    from apps.portefeuille.services.commun import numero_mobile_money

    assert numero_mobile_money(saisi) == "90123456"


@pytest.mark.parametrize("saisi", ["9012345", "+33612345678", "901234567"])
def test_numero_mobile_money_invalide(saisi):
    from apps.core.exceptions import DonneesInvalides
    from apps.portefeuille.services.commun import numero_mobile_money

    with pytest.raises(DonneesInvalides):
        numero_mobile_money(saisi)


def test_reponse_paygate_inattendue(settings, monkeypatch):
    import io

    from apps.portefeuille import paygate
    from apps.portefeuille.provider import PaiementIndisponible

    settings.PAYGATE_AUTH_TOKEN = "jeton"
    monkeypatch.setattr("urllib.request.urlopen", lambda requete, timeout: io.StringIO("[]"))
    with pytest.raises(PaiementIndisponible):
        paygate.PayGateProvider().verifier("id-1", "")


def test_recharge_plafonnee(passager):
    from apps.core.exceptions import DonneesInvalides
    from apps.portefeuille import services

    with pytest.raises(DonneesInvalides) as exc:
        services.recharger(passager, 100_001, "flooz")
    assert exc.value.code == "RECHARGE_TROP_ELEVEE"
    assert services.recharger(passager, 100_000, "flooz").montant == 100_000


def test_numero_refuse_par_l_operateur_message_clair(settings, monkeypatch, passager):
    from apps.portefeuille import services
    from apps.portefeuille.models import Transaction
    from apps.portefeuille.provider import NumeroRefuseParOperateur

    settings.PAIEMENT_PROVIDER = "apps.portefeuille.paygate.PayGateProvider"
    monkeypatch.setattr("apps.portefeuille.paygate._appeler", lambda chemin, donnees: {"status": 4})
    with pytest.raises(NumeroRefuseParOperateur) as exc:
        services.recharger(passager, 1000, "mixx")

    assert exc.value.http_status == 400
    assert "Flooz (Moov) ou Mixx (Yas)" in exc.value.message
    assert Transaction.objects.filter(type="recharge", statut="echouee").count() == 1
