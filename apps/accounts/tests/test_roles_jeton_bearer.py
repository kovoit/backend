"""Rôles recalculés à chaque requête (F-058, D-36), avec un vrai jeton d'accès obtenu par la
connexion au back-office et envoyé en `Authorization: Bearer` (sans force_authenticate) : un
droit retiré prend effet alors que le jeton est encore valide."""

import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from apps.accounts.tests.factories import AdminFactory

pytestmark = pytest.mark.django_db

MOT_DE_PASSE = "Admin123!"
AUDIT = "/api/v1/admin/audit/evenements/"
TABLEAU_DE_BORD = "/api/v1/admin/tableau-de-bord/"
MOI = "/api/v1/auth/admin/moi/"


@pytest.fixture
def auditrice():
    compte = AdminFactory(roles=["audit"], email="auditrice@kovoit.tg")
    compte.set_password(MOT_DE_PASSE)
    compte.save()
    return compte


@pytest.fixture
def client_bearer(auditrice):
    """Client porteur du jeton d'accès émis par la vraie connexion admin."""
    client = APIClient()
    connexion = client.post(
        "/api/v1/auth/admin/connexion/",
        {"email": auditrice.email, "mot_de_passe": MOT_DE_PASSE},
        format="json",
    )
    assert connexion.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {connexion.json()['reponse']['access']}")
    return client


def _refus(reponse, code=None):
    corps = reponse.json()
    assert reponse.status_code == 403
    assert corps["statut"] == "failed" and corps["message"]
    if code:
        assert corps["reponse"]["code"] == code


def test_jeton_reel_ouvre_le_domaine_du_role(client_bearer):
    assert client_bearer.get(AUDIT).status_code == 200
    assert client_bearer.get(MOI).json()["reponse"]["roles"] == ["audit"]


def test_role_retire_refuse_avec_le_meme_jeton(client_bearer, auditrice):
    assert client_bearer.get(AUDIT).status_code == 200

    auditrice.groups.remove(Group.objects.get(name="audit"))

    _refus(client_bearer.get(AUDIT), "ROLE_ADMIN_INSUFFISANT")
    # Le jeton reste valide : seul le domaine retiré est fermé
    assert client_bearer.get(TABLEAU_DE_BORD).status_code == 200


def test_is_staff_retire_refuse_avec_le_meme_jeton(client_bearer, auditrice):
    assert client_bearer.get(TABLEAU_DE_BORD).status_code == 200

    auditrice.is_staff = False
    auditrice.save(update_fields=["is_staff"])

    _refus(client_bearer.get(TABLEAU_DE_BORD))
    _refus(client_bearer.get(AUDIT))
    _refus(client_bearer.get(MOI))
