import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.api.admin_auth_views import CHEMIN_COOKIE, COOKIE_REFRESH
from apps.accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

MOT_DE_PASSE = "Admin123!"
CONNEXION = "/api/v1/auth/admin/connexion/"
RAFRAICHIR = "/api/v1/auth/admin/jeton/rafraichir/"
DECONNEXION = "/api/v1/auth/admin/deconnexion/"
MOI = "/api/v1/auth/admin/moi/"
COOKIE = COOKIE_REFRESH


def _compte(**champs):
    utilisateur = UserFactory(**champs)
    utilisateur.set_password(MOT_DE_PASSE)
    utilisateur.save()
    return utilisateur


@pytest.fixture
def admin_mdp():
    return _compte(is_staff=True, email="admin@kovoit.tg")


def _connecter(client, email="admin@kovoit.tg", mot_de_passe=MOT_DE_PASSE):
    return client.post(CONNEXION, {"email": email, "mot_de_passe": mot_de_passe}, format="json")


def test_connexion_admin_pose_le_refresh_en_cookie_httponly(api_client, admin_mdp):
    reponse = _connecter(api_client, email="  ADMIN@kovoit.tg ")

    assert reponse.status_code == 200
    corps = reponse.json()["reponse"]
    assert corps["access"]
    assert "refresh" not in corps
    assert corps["utilisateur"]["email"] == "admin@kovoit.tg"
    assert corps["utilisateur"]["is_staff"] is True
    cookie = reponse.cookies[COOKIE]
    assert cookie["httponly"] is True
    assert cookie["samesite"] == "Lax"
    assert cookie["path"] == CHEMIN_COOKIE
    admin_mdp.refresh_from_db()
    assert admin_mdp.last_login is not None


@pytest.mark.parametrize(
    ("email", "mot_de_passe"),
    [("admin@kovoit.tg", "mauvais"), ("inconnu@kovoit.tg", MOT_DE_PASSE)],
)
def test_identifiants_incorrects_meme_reponse(api_client, admin_mdp, email, mot_de_passe):
    reponse = _connecter(api_client, email, mot_de_passe)

    assert reponse.status_code == 401
    assert reponse.json()["reponse"]["code"] == "IDENTIFIANTS_INVALIDES"
    assert COOKIE not in reponse.cookies


def test_compte_desactive_refuse(api_client):
    _compte(is_staff=True, email="ancien@kovoit.tg", is_active=False)

    reponse = _connecter(api_client, email="ancien@kovoit.tg")

    assert reponse.status_code == 401


def test_compte_non_admin_refuse(api_client):
    _compte(email="conducteur@kovoit.tg")

    reponse = _connecter(api_client, email="conducteur@kovoit.tg")

    assert reponse.status_code == 403
    assert reponse.json()["reponse"]["code"] == "COMPTE_NON_ADMIN"
    assert COOKIE not in reponse.cookies


def test_champs_obligatoires(api_client):
    reponse = api_client.post(CONNEXION, {}, format="json")

    assert reponse.status_code == 400
    assert set(reponse.json()["reponse"]["erreurs"]) == {"email", "mot_de_passe"}


def test_nombre_de_tentatives_limite(api_client, admin_mdp):
    cache.clear()
    for _ in range(5):
        _connecter(api_client, mot_de_passe="mauvais")

    reponse = _connecter(api_client)

    assert reponse.status_code == 429
    assert reponse.json()["reponse"]["code"] == "TROP_DE_REQUETES"


def test_rafraichir_avec_le_cookie_fait_tourner_le_refresh(api_client, admin_mdp):
    _connecter(api_client)
    ancien = api_client.cookies[COOKIE].value

    reponse = api_client.post(RAFRAICHIR)

    assert reponse.status_code == 200
    assert reponse.json()["reponse"]["access"]
    assert "refresh" not in reponse.json()["reponse"]
    nouveau = reponse.cookies[COOKIE].value
    assert nouveau != ancien
    # L'ancien refresh est en liste noire après rotation
    rejoue = APIClient()
    rejoue.cookies[COOKIE] = ancien
    assert rejoue.post(RAFRAICHIR).status_code == 401


def test_rafraichir_sans_cookie(api_client):
    reponse = api_client.post(RAFRAICHIR)

    assert reponse.status_code == 401
    assert reponse.json()["reponse"]["code"] == "SESSION_EXPIREE"


def test_rafraichir_compte_desactive_entre_temps(api_client, admin_mdp):
    _connecter(api_client)
    admin_mdp.is_active = False
    admin_mdp.save()

    assert api_client.post(RAFRAICHIR).status_code == 401


def test_moi_reserve_aux_admins(api_client, admin_mdp, client_utilisateur):
    access = _connecter(api_client).json()["reponse"]["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    assert api_client.get(MOI).json()["reponse"]["email"] == "admin@kovoit.tg"
    assert client_utilisateur.get(MOI).status_code == 403
    assert APIClient().get(MOI).status_code == 401


def test_deconnexion_revoque_le_refresh_et_supprime_le_cookie(api_client, admin_mdp):
    _connecter(api_client)
    refresh = api_client.cookies[COOKIE].value

    reponse = api_client.post(DECONNEXION)

    assert reponse.status_code == 200
    assert reponse.cookies[COOKIE].value == ""
    rejoue = APIClient()
    rejoue.cookies[COOKIE] = refresh
    assert rejoue.post(RAFRAICHIR).status_code == 401


def test_deconnexion_sans_session_est_sans_effet(api_client):
    api_client.cookies[COOKIE] = "jeton-invalide"

    assert api_client.post(DECONNEXION).status_code == 200
