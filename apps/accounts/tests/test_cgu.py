"""Conditions d'utilisation : version acceptée enregistrée, nouvelle version à réaccepter."""

import pytest

from apps.accounts.cgu import CGU_URL
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
