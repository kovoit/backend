"""Django admin (F-058) : les écrans des jetons SimpleJWT sont retirés pour tous.

OutstandingToken affichait le refresh complet : un staff qui avait `view_outstandingtoken`
lisait le refresh d'un superutilisateur et le rejouait sur le rafraîchissement admin.
BlacklistedToken permettait de réactiver un refresh révoqué. Plus personne ne voit ces
écrans, superutilisateur compris. La révocation elle-même (déconnexion, rotation) est
couverte par test_connexion_admin.py ; on vérifie ici qu'elle laisse bien une trace en base.
"""

import pytest
from django.contrib import admin
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.api.admin_auth_views import COOKIE_REFRESH
from apps.accounts.tests.factories import AdminFactory

pytestmark = pytest.mark.django_db

ADMIN = "/django-admin"
MOT_DE_PASSE = "Mdp-Tres-Long-2026!"
CONNEXION = "/api/v1/auth/admin/connexion/"
RAFRAICHIR = "/api/v1/auth/admin/jeton/rafraichir/"
DECONNEXION = "/api/v1/auth/admin/deconnexion/"
DROITS_JETONS = [
    "view_outstandingtoken",
    "view_blacklistedtoken",
    "delete_blacklistedtoken",
    "add_blacklistedtoken",
]


def _connecter_superutilisateur():
    """Connexion admin réelle d'un superutilisateur : renvoie (client, refresh en clair)."""
    compte = AdminFactory(is_superuser=True, roles=[], email="sup@kovoit.tg")
    compte.set_password(MOT_DE_PASSE)
    compte.save()
    client = APIClient()
    reponse = client.post(
        CONNEXION, {"email": "sup@kovoit.tg", "mot_de_passe": MOT_DE_PASSE}, format="json"
    )
    assert reponse.status_code == 200
    return compte, client, client.cookies[COOKIE_REFRESH].value


def _jti(refresh):
    return RefreshToken(refresh, verify=False)["jti"]


@pytest.fixture
def refresh_superutilisateur():
    compte, _, refresh = _connecter_superutilisateur()
    return compte, refresh


@pytest.fixture
def staff_droits_jetons():
    """Staff non superutilisateur qui détient toutes les permissions Django sur les jetons."""
    compte = AdminFactory(roles=[], email="lecteur@kovoit.tg")
    compte.user_permissions.set(Permission.objects.filter(codename__in=DROITS_JETONS))
    return compte


@pytest.fixture(params=["superutilisateur", "staff_droits_jetons"])
def visiteur(request, refresh_superutilisateur, staff_droits_jetons):
    if request.param == "superutilisateur":
        return refresh_superutilisateur[0]
    return staff_droits_jetons


def _urls_jetons(refresh_superutilisateur):
    compte, _ = refresh_superutilisateur
    jeton = OutstandingToken.objects.get(user=compte)
    return [
        f"{ADMIN}/token_blacklist/outstandingtoken/",
        f"{ADMIN}/token_blacklist/outstandingtoken/{jeton.pk}/change/",
        f"{ADMIN}/token_blacklist/blacklistedtoken/",
        f"{ADMIN}/token_blacklist/blacklistedtoken/add/",
    ]


@pytest.mark.parametrize("modele", [OutstandingToken, BlacklistedToken])
def test_modeles_de_jetons_absents_du_django_admin(modele):
    assert not admin.site.is_registered(modele)
    assert modele not in admin.site._registry


def test_le_staff_detient_bien_les_permissions_sur_les_jetons(staff_droits_jetons):
    """Garde-fou : le 404 ci-dessous ne vient pas d'un manque de permission."""
    assert staff_droits_jetons.has_perms([f"token_blacklist.{droit}" for droit in DROITS_JETONS])


def test_ecrans_des_jetons_introuvables(client, visiteur, refresh_superutilisateur):
    client.force_login(visiteur)

    for url in _urls_jetons(refresh_superutilisateur):
        assert client.get(url).status_code == 404, url


def test_aucun_refresh_dans_les_reponses(client, visiteur, refresh_superutilisateur):
    """Ni le refresh du cookie, ni la copie stockée en base (émise avant l'ajout du claim
    `canal`, mais signée et rejouable), ni son jti."""
    compte, refresh = refresh_superutilisateur
    jeton = OutstandingToken.objects.get(user=compte)
    assert jeton.jti == RefreshToken(refresh)["jti"]
    client.force_login(visiteur)

    for url in [*_urls_jetons(refresh_superutilisateur), f"{ADMIN}/"]:
        contenu = client.get(url).content.decode()
        for secret in (refresh, jeton.token, jeton.jti):
            assert secret not in contenu, url


def test_index_du_django_admin_sans_token_blacklist(client, visiteur):
    client.force_login(visiteur)

    reponse = client.get(f"{ADMIN}/")

    assert reponse.status_code == 200
    contenu = reponse.content.decode()
    assert "token_blacklist" not in contenu
    assert "outstandingtoken" not in contenu.lower()
    assert "blacklistedtoken" not in contenu.lower()
    labels = {app["app_label"] for app in reponse.context["app_list"]}
    assert "token_blacklist" not in labels


def test_ajout_par_post_impossible(client, visiteur, refresh_superutilisateur):
    """Réactiver un refresh révoqué n'est plus possible : pas d'écran pour écrire non plus."""
    compte, _ = refresh_superutilisateur
    jeton = OutstandingToken.objects.get(user=compte)
    client.force_login(visiteur)

    reponse = client.post(f"{ADMIN}/token_blacklist/blacklistedtoken/add/", {"token": jeton.pk})

    assert reponse.status_code == 404
    assert not BlacklistedToken.objects.filter(token=jeton).exists()


def test_deconnexion_admin_inscrit_le_refresh_en_liste_noire():
    compte, client, refresh = _connecter_superutilisateur()

    assert client.post(DECONNEXION).status_code == 200

    assert BlacklistedToken.objects.filter(token__jti=_jti(refresh)).exists()
    rejoue = APIClient()
    rejoue.cookies[COOKIE_REFRESH] = refresh
    assert rejoue.post(RAFRAICHIR).status_code == 401


def test_rotation_inscrit_l_ancien_refresh_en_liste_noire_et_le_nouveau_fonctionne():
    _, client, ancien = _connecter_superutilisateur()

    premiere = client.post(RAFRAICHIR)
    nouveau = premiere.cookies[COOKIE_REFRESH].value

    assert premiere.status_code == 200
    assert nouveau != ancien
    assert BlacklistedToken.objects.filter(token__jti=_jti(ancien)).exists()
    assert not BlacklistedToken.objects.filter(token__jti=_jti(nouveau)).exists()
    assert client.post(RAFRAICHIR).status_code == 200
