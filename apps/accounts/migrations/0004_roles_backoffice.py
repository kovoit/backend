"""Crée les groupes des rôles du back-office (apps/accounts/roles.py). Aucun compte n'est modifié :
un admin sans rôle garde l'accès à tout."""

from django.db import migrations

ROLES = ["moderation", "finance", "audit", "parametres"]


def creer_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for nom in ROLES:
        Group.objects.get_or_create(name=nom)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_motif_suspension"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(creer_roles, migrations.RunPython.noop)]
