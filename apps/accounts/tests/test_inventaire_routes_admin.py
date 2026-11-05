"""Rattachement de chaque route d'administration à un domaine (F-058, D-36).

Toute route sous /api/v1/admin/ et /api/v1/auth/admin/ déclare un rôle (ADMIN_*) ou figure dans
la liste fermée ci-dessous, avec ses permissions exactes. Une route ajoutée plus tard avec
`ADMIN` seul au lieu d'`ADMIN_*` (accessible à l'admin sans rôle) fait échouer ce test : il faut
alors lui donner un rôle, ou l'ajouter ici en connaissance de cause."""

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.accounts.api.permissions import ADMIN
from apps.accounts.tests.routes_admin import protegee_par_un_role, routes_sous_admin

# Tout administrateur, même sans rôle : profil, tableau de bord, consultation des paramètres.
TOUT_ADMIN = [
    ("get", "api/v1/auth/admin/moi/"),
    ("get", "api/v1/admin/tableau-de-bord/"),
    ("get", "api/v1/admin/parametres/"),
]
# Connexion au back-office : publiques par nature (le service vérifie identifiants et is_staff)
PUBLIQUES = [
    ("post", "api/v1/auth/admin/connexion/"),
    ("post", "api/v1/auth/admin/jeton/rafraichir/"),
    ("post", "api/v1/auth/admin/deconnexion/"),
    ("post", "api/v1/auth/admin/mot-de-passe/oublie/"),
    ("post", "api/v1/auth/admin/mot-de-passe/reinitialiser/"),
]
SANS_ROLE = {**dict.fromkeys(TOUT_ADMIN, ADMIN), **dict.fromkeys(PUBLIQUES, [AllowAny])}


def test_l_inventaire_parcourt_les_deux_prefixes():
    chemins = {chemin for _, chemin, _ in routes_sous_admin()}

    assert any(c.startswith("api/v1/admin/") for c in chemins)
    assert any(c.startswith("api/v1/auth/admin/") for c in chemins)


def test_chaque_route_d_administration_est_une_vue_de_classe():
    assert [chemin for _, chemin, vue in routes_sous_admin() if vue is None] == []


def test_les_permissions_se_lisent_dans_permission_classes():
    """L'inventaire lit `permission_classes` : une vue qui calculerait ses permissions autrement
    (get_permissions surchargé) échapperait au contrôle."""
    surchargees = [
        chemin
        for _, chemin, vue in routes_sous_admin()
        if vue is not None and vue.get_permissions is not APIView.get_permissions
    ]

    assert surchargees == []


def test_toute_route_sans_role_est_dans_la_liste_fermee():
    sans_role = {
        (methode, chemin)
        for methode, chemin, vue in routes_sous_admin()
        if vue is not None and not protegee_par_un_role(vue)
    }

    assert sans_role == set(SANS_ROLE)


def test_les_routes_de_la_liste_fermee_ont_exactement_les_permissions_attendues():
    vues = {(methode, chemin): vue for methode, chemin, vue in routes_sous_admin()}

    for route, attendues in SANS_ROLE.items():
        assert list(vues[route].permission_classes) == attendues, route
