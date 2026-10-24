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


def test_alerte_finance_retraits_en_attente(admin, passager, settings):
    from django.contrib.auth.models import Group

    from apps.accounts.tests.factories import UserFactory
    from apps.portefeuille import services
    from apps.portefeuille.tasks import alerter_retraits_en_attente

    settings.PAIEMENT_PROVIDER = "apps.portefeuille.paygate.PayGateProvider"
    settings.PAYGATE_CALLBACK_SECRET = "cle"
    moderateur = UserFactory(is_staff=True)
    moderateur.groups.set(Group.objects.filter(name="moderation"))
    services.retirer(passager, 1000, "flooz")
    assert alerter_retraits_en_attente() == 0  # pas encore 24 h

    with freeze_time(timezone.now() + timedelta(hours=25)):
        assert alerter_retraits_en_attente() == 1
    destinataires = [m.to[0] for m in mail.outbox]
    assert admin.email in destinataires  # admin sans rôle : tous les domaines
    assert moderateur.email not in destinataires  # Modération seulement
    assert "1000 F CFA" in mail.outbox[0].body
