"""Supervision : /api/v1/sante/ signale les composants en panne (503)."""

from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone
from freezegun import freeze_time

from apps.core.supervision import battre

pytestmark = pytest.mark.django_db

URL = "/api/v1/sante/"


def test_tout_va_bien(api_client):
    battre()

    reponse = api_client.get(URL)

    assert reponse.status_code == 200
    assert reponse.json()["reponse"]["composants"] == {
        "base_de_donnees": True,
        "cache": True,
        "taches_planifiees": True,
    }


def test_planificateur_arrete_503(api_client):
    battre()
    with freeze_time(timezone.now() + timedelta(minutes=16)):
        reponse = api_client.get(URL)

    assert reponse.status_code == 503
    assert reponse.json()["message"] == "Service dégradé : taches_planifiees."


def test_jamais_demarre_503(api_client):
    assert api_client.get(URL).status_code == 503


@pytest.fixture
def retrait_ancien(passager, settings):
    """Un retrait de 1 000 F en attente de versement (comme avec PayGate)."""
    from apps.portefeuille import services

    settings.PAIEMENT_PROVIDER = "apps.portefeuille.paygate.PayGateProvider"
    settings.PAYGATE_CALLBACK_SECRET = "cle"
    return services.retirer(passager, 1000, "flooz")


def test_alerte_finance_retraits_en_attente(retrait_ancien):
    from apps.accounts.tests.factories import AdminFactory
    from apps.portefeuille.tasks import alerter_retraits_en_attente

    finance = AdminFactory(roles=["finance"])
    superutilisateur = AdminFactory(is_superuser=True, roles=[])
    exclus = [
        AdminFactory(roles=["moderation"]),
        AdminFactory(roles=[]),  # sans rôle : tableau de bord et paramètres seulement (D-36)
        AdminFactory(roles=["finance"], is_active=False),
    ]
    assert alerter_retraits_en_attente() == 0  # pas encore 24 h

    with freeze_time(timezone.now() + timedelta(hours=25)):
        assert alerter_retraits_en_attente() == 1
    alertes = [m for m in mail.outbox if "à verser" in m.subject]
    destinataires = sorted(m.to[0] for m in alertes)
    assert destinataires == sorted([finance.email, superutilisateur.email])
    assert not {compte.email for compte in exclus} & set(destinataires)
    assert "1000 F CFA" in alertes[0].body
