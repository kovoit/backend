"""Aides des tests du Django admin (F-058, D-37) : compte gestionnaire, URL et formulaires."""

from django.contrib.auth.models import Group, Permission
from django.db.models import Q

from apps.accounts.tests.factories import AdminFactory

ADMIN = "/django-admin"
NOUVEAU_MOT_DE_PASSE = "Nouveau-Mdp-2026!"


def creer_gestionnaire():
    """Staff sans rôle, non superutilisateur : consulte, modifie et supprime les comptes, et a
    toutes les permissions Django sur les groupes."""
    compte = AdminFactory(roles=[], prenom="Ama")
    compte.user_permissions.set(
        Permission.objects.filter(
            Q(
                content_type__app_label="accounts",
                codename__in=["change_user", "delete_user", "view_user"],
            )
            | Q(content_type__app_label="auth", content_type__model="group")
        )
    )
    return compte


def url_fiche(compte, vue="change") -> str:
    return f"{ADMIN}/accounts/user/{compte.pk}/{vue}/"


def url_groupe(groupe=None, vue="change") -> str:
    return (
        f"{ADMIN}/auth/group/add/" if groupe is None else f"{ADMIN}/auth/group/{groupe.pk}/{vue}/"
    )


def formulaire(compte, **changes) -> dict:
    """Fiche « Modifier l'utilisateur » soumise avec tous les droits demandés."""
    return {
        "email": compte.email,
        "prenom": compte.prenom,
        "nom": compte.nom,
        "telephone": compte.telephone,
        "mode_actif": compte.mode_actif,
        "statut_compte": compte.statut_compte,
        "suspendu_jusqu_au_0": "",
        "suspendu_jusqu_au_1": "",
        "email_verifie": "on",
        "is_active": "on",
        "is_staff": "on",
        "is_superuser": "on",
        "groups": [g.pk for g in Group.objects.filter(name__in=["finance", "audit"])],
        **changes,
    }


def formulaire_mot_de_passe(mot_de_passe=NOUVEAU_MOT_DE_PASSE) -> dict:
    return {"usable_password": "true", "password1": mot_de_passe, "password2": mot_de_passe}


def formulaire_groupe(groupe, nom=None, permissions=None) -> dict:
    if permissions is None:
        permissions = list(groupe.permissions.values_list("pk", flat=True))
    return {"name": nom or groupe.name, "permissions": permissions}


def supprimer_en_masse(client, *comptes):
    """Action « Supprimer les utilisateurs sélectionnés », confirmation comprise."""
    return client.post(
        f"{ADMIN}/accounts/user/",
        {
            "action": "delete_selected",
            "_selected_action": [c.pk for c in comptes],
            "post": "yes",
        },
    )


def groupes(compte) -> set[str]:
    return set(compte.groups.values_list("name", flat=True))
