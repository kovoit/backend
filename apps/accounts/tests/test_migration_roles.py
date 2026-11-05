"""Migration de données accounts/0006 (F-058, D-36) : les admins existants sans rôle reçoivent les
quatre rôles ; personne d'autre n'est modifié."""

from importlib import import_module

import pytest
from django.apps import apps as registre
from django.contrib.auth.models import Group
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.accounts import roles
from apps.accounts.tests.factories import AdminFactory, UserFactory

migration = import_module("apps.accounts.migrations.0006_roles_admins_existants")

QUATRE = {"audit", "finance", "moderation", "parametres"}
AVANT, APRES = ("accounts", "0005_cgu"), ("accounts", "0006_roles_admins_existants")


def migrer():
    migration.donner_tous_les_roles(registre, None)


def groupes(compte) -> set[str]:
    return set(compte.groups.values_list("name", flat=True))


@pytest.mark.django_db
def test_ca6_ama_recoit_les_quatre_roles_kodjo_reste_finance():
    ama = AdminFactory(roles=[], prenom="Ama")
    kodjo = AdminFactory(roles=["finance"], prenom="Kodjo")

    migrer()

    assert groupes(ama) == QUATRE
    assert groupes(kodjo) == {"finance"}


@pytest.mark.django_db
def test_ca6_ama_garde_tous_ses_acces_apres_la_migration(client_de):
    ama = AdminFactory(roles=[], prenom="Ama")
    migrer()
    client = client_de(ama)

    for url in ("kyc/", "transactions/", "audit/evenements/"):
        assert client.get(f"/api/v1/admin/{url}").status_code == 200, url


@pytest.mark.django_db
def test_admin_inactif_sans_role_recoit_aussi_les_quatre_roles():
    inactif = AdminFactory(roles=[], is_active=False)

    migrer()

    assert groupes(inactif) == QUATRE


@pytest.mark.django_db
def test_admin_avec_un_groupe_hors_roles_recoit_les_quatre_roles():
    compte = AdminFactory(roles=[])
    compte.groups.add(Group.objects.create(name="stagiaires"))

    migrer()

    assert groupes(compte) == QUATRE | {"stagiaires"}


@pytest.mark.django_db
def test_superutilisateur_et_non_staff_non_modifies():
    superutilisateur = AdminFactory(is_superuser=True, roles=[])
    passager = UserFactory()

    migrer()

    assert groupes(superutilisateur) == set()
    assert groupes(passager) == set()


@pytest.mark.django_db
def test_groupe_supprime_puis_recree():
    Group.objects.filter(name="audit").delete()
    ama = AdminFactory(roles=[])

    migrer()

    assert Group.objects.filter(name="audit").count() == 1
    assert groupes(ama) == QUATRE


@pytest.mark.django_db
def test_migration_idempotente():
    ama = AdminFactory(roles=[])
    kodjo = AdminFactory(roles=["finance"])

    migrer()
    migrer()

    assert groupes(ama) == QUATRE
    assert groupes(kodjo) == {"finance"}
    assert Group.objects.filter(name__in=QUATRE).count() == 4


def test_roles_figes_de_la_migration():
    """Valeur figée comparée à une liste littérale : un rôle ajouté plus tard au code ne doit pas
    pousser à modifier une migration déjà appliquée (claude.md §9)."""
    assert migration.ROLES == ["moderation", "finance", "audit", "parametres"]
    assert set(migration.ROLES) <= set(roles.ROLES)


def test_pas_de_retour_arriere_destructeur():
    (operation,) = migration.Migration.operations
    assert operation.reverse_code.__name__ == "noop"


@pytest.mark.django_db(transaction=True, serialized_rollback=True)
def test_de_bout_en_bout_0005_vers_0006():
    executor = MigrationExecutor(connection)
    try:
        executor.migrate([AVANT])
        anciens = executor.loader.project_state([AVANT]).apps
        User, Group0005 = anciens.get_model("accounts", "User"), anciens.get_model("auth", "Group")
        ama = User.objects.create(email="ama@kovoit.tg", is_staff=True, telephone="+22890000001")
        kodjo = User.objects.create(
            email="kodjo@kovoit.tg", is_staff=True, telephone="+22890000002"
        )
        kodjo.groups.add(Group0005.objects.get(name="finance"))

        executor = MigrationExecutor(connection)
        executor.migrate([APRES])

        nouveaux = executor.loader.project_state([APRES]).apps.get_model("accounts", "User")
        assert groupes(nouveaux.objects.get(pk=ama.pk)) == QUATRE
        assert groupes(nouveaux.objects.get(pk=kodjo.pk)) == {"finance"}
    finally:
        # Revenir au dernier état de toutes les apps : migrate([AVANT]) a annulé tous les
        # descendants de accounts/0005, et une exception a pu survenir entre les deux migrate
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
