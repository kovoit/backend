"""Mot de passe oublié du back-office."""

import re

import pytest
from django.core import mail

from apps.accounts.tests.factories import UserFactory
from apps.audit.models import EvenementAudit

pytestmark = pytest.mark.django_db

OUBLIE = "/api/v1/auth/admin/mot-de-passe/oublie/"
REINITIALISER = "/api/v1/auth/admin/mot-de-passe/reinitialiser/"
CONNEXION = "/api/v1/auth/admin/connexion/"
NOUVEAU = "Kovoit-Lome-2026!"


@pytest.fixture
def admin_kovoit(db):
    compte = UserFactory(email="chef@kovoittg.com", is_staff=True)
    compte.set_password("Ancien-mot-de-passe-1")
    compte.save()
    return compte


def _lien(api_client, email="chef@kovoittg.com"):
    reponse = api_client.post(OUBLIE, {"email": email}, format="json")
    assert reponse.status_code == 200
    uid, jeton = re.search(r"uid=([^&\s]+)&jeton=(\S+)", mail.outbox[-1].body).groups()
    return uid, jeton


def test_lien_envoye_puis_mot_de_passe_change(api_client, admin_kovoit, settings):
    settings.BACKOFFICE_URL = "https://admin.kovoittg.com"
    uid, jeton = _lien(api_client, " CHEF@kovoittg.com ")

    assert "https://admin.kovoittg.com/reinitialiser?uid=" in mail.outbox[-1].body
    reponse = api_client.post(
        REINITIALISER, {"uid": uid, "jeton": jeton, "mot_de_passe": NOUVEAU}, format="json"
    )
    assert reponse.status_code == 200
    connexion = api_client.post(
        CONNEXION, {"email": "chef@kovoittg.com", "mot_de_passe": NOUVEAU}, format="json"
    )
    assert connexion.status_code == 200
    # Lien à usage unique : le jeton ne vaut plus une fois le mot de passe changé
    encore = api_client.post(
        REINITIALISER,
        {"uid": uid, "jeton": jeton, "mot_de_passe": "Autre-Mdp-2026!"},
        format="json",
    )
    assert encore.json()["reponse"]["code"] == "LIEN_INVALIDE"
    actions = set(EvenementAudit.objects.values_list("action", flat=True))
    assert {"session.demander_reinitialisation", "session.reinitialiser_mot_de_passe"} <= actions
    assert jeton not in str(list(EvenementAudit.objects.values_list("details", flat=True)))


@pytest.mark.parametrize("email", ["inconnu@kovoittg.com", "passager@kovoittg.com"])
def test_aucune_enumeration_des_comptes(api_client, admin_kovoit, email):
    UserFactory(email="passager@kovoittg.com")  # compte non admin

    reponse = api_client.post(OUBLIE, {"email": email}, format="json")

    assert reponse.status_code == 200
    assert "Si cette adresse" in reponse.json()["message"]
    assert mail.outbox == []


def test_mot_de_passe_faible_refuse(api_client, admin_kovoit):
    uid, jeton = _lien(api_client)

    reponse = api_client.post(
        REINITIALISER, {"uid": uid, "jeton": jeton, "mot_de_passe": "123"}, format="json"
    )

    assert reponse.status_code == 400
    assert reponse.json()["reponse"]["code"] == "MOT_DE_PASSE_FAIBLE"


@pytest.mark.parametrize(("uid", "jeton"), [("xx", "faux"), ("", "abc"), ("MTIz", "faux")])
def test_lien_falsifie_refuse(api_client, admin_kovoit, uid, jeton):
    reponse = api_client.post(
        REINITIALISER, {"uid": uid or "a", "jeton": jeton, "mot_de_passe": NOUVEAU}, format="json"
    )

    assert reponse.status_code == 400
    assert reponse.json()["reponse"]["code"] == "LIEN_INVALIDE"


def test_les_sessions_ouvertes_sont_revoquees(api_client, admin_kovoit):
    api_client.post(
        CONNEXION,
        {"email": "chef@kovoittg.com", "mot_de_passe": "Ancien-mot-de-passe-1"},
        format="json",
    )
    uid, jeton = _lien(api_client)
    api_client.post(
        REINITIALISER, {"uid": uid, "jeton": jeton, "mot_de_passe": NOUVEAU}, format="json"
    )

    rafraichir = api_client.post("/api/v1/auth/admin/jeton/rafraichir/")
    assert rafraichir.status_code == 401
