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
