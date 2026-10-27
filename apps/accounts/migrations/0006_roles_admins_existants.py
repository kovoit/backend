"""Moindre privilège (D-36) : un admin sans rôle n'a plus accès à tout. Les admins existants
(is_staff, non superutilisateurs, actifs ou non) qui n'ont aucun rôle reçoivent les quatre rôles,
pour ne perdre aucun accès. Les admins qui ont déjà au moins un rôle ne sont pas modifiés.

Pas de retour arrière : avec l'ancienne règle, quatre rôles valaient « aucun rôle » ; retirer les
groupes enlèverait aussi des rôles attribués depuis."""

from django.db import migrations

# Figée : ne pas importer apps/accounts/roles.py (une migration ne dépend pas du code courant)
ROLES = ["moderation", "finance", "audit", "parametres"]


def donner_tous_les_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    User = apps.get_model("accounts", "User")
    groupes = [Group.objects.get_or_create(name=nom)[0] for nom in ROLES]
    sans_role = User.objects.filter(is_staff=True, is_superuser=False).exclude(
        groups__name__in=ROLES
    )
    for compte in sans_role:
        compte.groups.add(*groupes)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_cgu"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(donner_tous_les_roles, migrations.RunPython.noop)]
