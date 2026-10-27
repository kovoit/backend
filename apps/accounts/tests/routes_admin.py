"""Inventaire des routes d'administration, lu dans la configuration d'URL.

`routes_par_role` : routes qui déclarent un rôle (ADMIN_MODERATION, ADMIN_FINANCE, ADMIN_AUDIT,
ADMIN_PARAMETRES) ; une telle route ajoutée plus tard est testée sans modifier les tests. À lui
seul, il ne prouve pas qu'une route est rattachée à un domaine : `routes_sous_admin` sert à
vérifier (test_inventaire_routes_admin.py) que toute route sous /api/v1/admin/ et
/api/v1/auth/admin/ déclare un rôle ou figure dans une liste fermée."""

import re

from django.urls import URLResolver, get_resolver

from apps.accounts.api.permissions import _Role

METHODES = ("get", "post", "put", "patch", "delete")
# Valeur substituée à chaque paramètre de route (ressource inexistante : la permission passe avant)
VALEURS = {"uuid": "00000000-0000-4000-8000-000000000000", "str": "recharge_min"}
PARAMETRE = re.compile(r"<(?:(\w+):)?\w+>")


def _parcourir(motifs, prefixe=""):
    for motif in motifs:
        if isinstance(motif, URLResolver):
            yield from _parcourir(motif.url_patterns, prefixe + str(motif.pattern))
        else:
            yield prefixe + str(motif.pattern), motif


def protegee_par_un_role(vue) -> bool:
    permissions = getattr(vue, "permission_classes", None) or []
    return any(isinstance(p, type) and issubclass(p, _Role) for p in permissions)


def routes_par_role() -> list[tuple[str, str]]:
    """(méthode, url) de chaque route d'API réservée à un rôle d'administrateur."""
    routes = []
    for chemin, motif in _parcourir(get_resolver().url_patterns):
        vue = getattr(motif.callback, "view_class", None)
        if vue is None or not protegee_par_un_role(vue):
            continue
        url = "/" + PARAMETRE.sub(lambda m: VALEURS[m.group(1) or "str"], chemin)
        routes += [(methode, url) for methode in METHODES if hasattr(vue, methode)]
    return sorted(set(routes))


PREFIXES_ADMIN = ("api/v1/admin/", "api/v1/auth/admin/")


def routes_sous_admin() -> list[tuple[str, str, type | None]]:
    """(méthode, chemin brut, vue) de chaque route sous PREFIXES_ADMIN ; méthode « ? » et vue
    None pour une route qui n'est pas une vue de classe (non vérifiable : le test la refuse)."""
    routes = []
    for chemin, motif in _parcourir(get_resolver().url_patterns):
        if not chemin.startswith(PREFIXES_ADMIN):
            continue
        vue = getattr(motif.callback, "view_class", None)
        if vue is None:
            routes.append(("?", chemin, None))
            continue
        routes += [(methode, chemin, vue) for methode in METHODES if hasattr(vue, methode)]
    return routes
