"""F-038 · Les routes d'administration exigent un jeton du back-office (`canal` = web, D-71)."""

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.accounts.api.admin_auth_views import COOKIE_REFRESH
from apps.accounts.services import emettre_jetons
from apps.accounts.tests.aides_auth import (
    MOT_DE_PASSE,
    avec_mot_de_passe,
    client_porteur,
    code_de,
)
from apps.accounts.tests.factories import AdminFactory, UserFactory
from apps.audit.models import Canal, EvenementAudit

pytestmark = pytest.mark.django_db
AUDIT = "/api/v1/admin/audit/evenements/"
MOI_ADMIN = "/api/v1/auth/admin/moi/"


@pytest.fixture
def auditrice():
    return avec_mot_de_passe(AdminFactory(roles=["audit"], email="auditrice@kovoit.tg"))


def connexion_web(compte) -> APIClient:
    """Vraie connexion au back-office : le client garde le cookie du refresh."""
    client = APIClient()
    reponse = client.post(
        "/api/v1/auth/admin/connexion/",
        {"email": compte.email, "mot_de_passe": MOT_DE_PASSE},
        format="json",
    )
    assert reponse.status_code == 200
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {reponse.json()['reponse']['access']}")
    return client


@pytest.mark.parametrize("route", [AUDIT, MOI_ADMIN])
def test_ca_038_2_jeton_mobile_d_un_admin_refuse(auditrice, route):
    mobile = client_porteur(emettre_jetons(auditrice, Canal.MOBILE)["access"])

    reponse = mobile.get(route)

    assert reponse.status_code == 403 and code_de(reponse) == "CANAL_WEB_REQUIS"
    assert connexion_web(auditrice).get(route).status_code == 200


def test_jeton_sans_canal_refuse(auditrice):
    """Jeton signé mais émis sans claim (ex. avant D-71) : refusé lui aussi."""
    client = client_porteur(str(AccessToken.for_user(auditrice)))

    assert code_de(client.get(AUDIT)) == "CANAL_WEB_REQUIS"


def test_non_admin_recoit_acces_refuse_avant_le_canal():
    passager = UserFactory()
    client = client_porteur(emettre_jetons(passager, Canal.MOBILE)["access"])

    reponse = client.get(AUDIT)

    assert reponse.status_code == 403 and code_de(reponse) == "ACCES_REFUSE"


def test_refus_de_canal_journalise_en_securite(auditrice):
    client_porteur(emettre_jetons(auditrice, Canal.MOBILE)["access"]).get(AUDIT)

    refus = EvenementAudit.objects.get(action="api.acces_refuse")
    assert refus.code_motif == "CANAL_WEB_REQUIS" and refus.categorie == "securite"
    assert refus.canal == Canal.MOBILE


def test_ca_038_3_refresh_enregistre_avec_le_claim_puis_rafraichissement(auditrice):
    client = connexion_web(auditrice)

    copie = OutstandingToken.objects.get(user=auditrice)
    assert RefreshToken(copie.token, verify=False)["canal"] == Canal.WEB
    rafraichi = client.post("/api/v1/auth/admin/jeton/rafraichir/")
    assert rafraichi.status_code == 200
    access = rafraichi.json()["reponse"]["access"]
    assert AccessToken(access)["canal"] == Canal.WEB
    assert client_porteur(access).get(AUDIT).status_code == 200
    nouveau = RefreshToken(rafraichi.cookies[COOKIE_REFRESH].value)
    assert nouveau["canal"] == Canal.WEB
    copie = OutstandingToken.objects.get(jti=nouveau["jti"])
    assert RefreshToken(copie.token, verify=False)["canal"] == Canal.WEB


def test_jetons_mobiles_enregistres_avec_le_claim():
    compte = UserFactory()

    jetons = emettre_jetons(compte, Canal.MOBILE)

    copie = OutstandingToken.objects.get(user=compte)
    assert copie.jti == RefreshToken(jetons["refresh"])["jti"]
    assert RefreshToken(copie.token, verify=False)["canal"] == Canal.MOBILE
