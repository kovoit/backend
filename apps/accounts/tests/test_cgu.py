"""Conditions d'utilisation : version acceptée enregistrée, nouvelle version à réaccepter."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from freezegun import freeze_time

from apps.accounts.cgu import CGU_URL
from apps.accounts.models import User
from apps.accounts.tests.aides_auth import (
    AMA,
    VERIFIER,
    client_porteur,
    connecter,
    dernier_code,
    inscrire,
    poster,
)
from apps.audit.models import EvenementAudit

pytestmark = pytest.mark.django_db

MOI = "/api/v1/moi/"


def test_acceptation_enregistree_et_tracee(client_utilisateur, utilisateur):
    assert client_utilisateur.get(MOI).json()["reponse"]["cgu_acceptees"] is False

    reponse = client_utilisateur.patch(MOI, {"accepter_cgu": True}, format="json")

    profil = reponse.json()["reponse"]
    assert (profil["cgu_acceptees"], profil["cgu_url"]) == (True, CGU_URL)
    utilisateur.refresh_from_db()
    assert utilisateur.cgu_acceptees_le is not None
    assert EvenementAudit.objects.filter(action="profil.accepter_cgu").count() == 1


def test_nouvelle_version_a_accepter(client_utilisateur, utilisateur, monkeypatch):
    client_utilisateur.patch(MOI, {"accepter_cgu": True}, format="json")
    monkeypatch.setattr("apps.accounts.cgu.CGU_VERSION", "2099-01-01")

    assert client_utilisateur.get(MOI).json()["reponse"]["cgu_acceptees"] is False


def test_avec_le_profil_en_une_fois(client_utilisateur):
    reponse = client_utilisateur.patch(
        MOI, {"prenom": "Ama", "nom": "Lawson", "accepter_cgu": True}, format="json"
    )

    profil = reponse.json()["reponse"]
    assert (profil["prenom"], profil["cgu_acceptees"]) == ("Ama", True)


def test_ca_004_3_nouvelle_version_reacceptee_de_bout_en_bout(monkeypatch):
    """Inscription sous la version 2026-10-24, puis CGU 2026-12-01 : l'app redemande."""
    monkeypatch.setattr("apps.accounts.cgu.CGU_VERSION", "2026-10-24")
    with freeze_time("2026-10-30 10:00:00"):
        inscrire()
        reponse = poster(VERIFIER, {"email": AMA, "code": dernier_code()})
        session = client_porteur(reponse.json()["reponse"]["access"])
        assert session.get(MOI).json()["reponse"]["cgu_acceptees"] is True

    monkeypatch.setattr("apps.accounts.cgu.CGU_VERSION", "2026-12-01")
    with freeze_time("2026-12-01 09:00:00"):
        client = client_porteur(connecter(AMA).json()["reponse"]["access"])
        avant = client.get(MOI).json()["reponse"]
        apres = client.patch(MOI, {"accepter_cgu": True}, format="json")

    assert avant["cgu_acceptees"] is False
    assert apres.status_code == 200 and apres.json()["statut"] == "success"
    assert apres.json()["reponse"]["cgu_acceptees"] is True
    compte = User.objects.get(email=AMA)
    assert compte.cgu_version == "2026-12-01"
    assert compte.cgu_acceptees_le == datetime(2026, 12, 1, 9, tzinfo=ZoneInfo("UTC"))
