"""Contrôle du paiement au démarrage (gunicorn ne lance pas les system checks de Django)."""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def verifier_configuration_paiement() -> None:
    """En production, PayGate exige un secret de callback : sinon le serveur refuse de démarrer."""
    paygate_actif = settings.PAIEMENT_PROVIDER.endswith("PayGateProvider")
    if paygate_actif and not settings.DEBUG and not settings.PAYGATE_CALLBACK_SECRET:
        raise ImproperlyConfigured(
            "PAYGATE_CALLBACK_SECRET est obligatoire quand PayGate est activé en production."
        )
