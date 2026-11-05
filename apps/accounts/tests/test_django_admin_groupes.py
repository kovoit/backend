"""Django admin (F-058, D-37) : les rôles reposent sur le nom des groupes. Seul un
superutilisateur crée, renomme, modifie les permissions ou supprime un groupe, même si un staff a
reçu toutes les permissions Django sur les groupes ; la consultation reste possible."""

import pytest
from django.contrib.auth.models import Group, Permission

from apps.accounts.tests.aides_django_admin import (
    ADMIN,
    creer_gestionnaire,
    formulaire_groupe,
    url_groupe,
)

pytestmark = pytest.mark.django_db

LISTE = f"{ADMIN}/auth/group/"


@pytest.fixture
def gestionnaire(client):
    compte = creer_gestionnaire()
    client.force_login(compte)
    return compte


@pytest.fixture
def finance():
    return Group.objects.get(name="finance")


def une_permission():
    return Permission.objects.get(content_type__app_label="accounts", codename="delete_user")


def test_groupes_consultables(client, gestionnaire, finance):
    assert client.get(LISTE).status_code == 200

    reponse = client.get(url_groupe(finance))

    assert reponse.status_code == 200
    assert reponse.context["has_change_permission"] is False
    assert reponse.context["has_delete_permission"] is False


def test_renommer_un_groupe_refuse(client, gestionnaire, finance):
    reponse = client.post(url_groupe(finance), formulaire_groupe(finance, nom="tresorerie"))

    assert reponse.status_code == 403
    finance.refresh_from_db()
    assert finance.name == "finance"


def test_ajouter_un_groupe_refuse(client, gestionnaire):
    assert client.get(url_groupe()).status_code == 403
    assert client.post(url_groupe(), {"name": "pirates", "permissions": []}).status_code == 403

    assert not Group.objects.filter(name="pirates").exists()


def test_supprimer_un_groupe_refuse(client, gestionnaire, finance):
    url = url_groupe(finance, "delete")

    assert client.get(url).status_code == 403
    assert client.post(url, {"post": "yes"}).status_code == 403
    assert Group.objects.filter(name="finance").exists()


def test_suppression_en_masse_d_un_groupe_sans_effet(client, gestionnaire, finance):
    client.post(
        LISTE, {"action": "delete_selected", "_selected_action": [finance.pk], "post": "yes"}
    )

    assert Group.objects.filter(pk=finance.pk).exists()


def test_ajouter_une_permission_a_son_groupe_refuse(client, gestionnaire, finance):
    gestionnaire.groups.add(finance)
    avant = set(finance.permissions.all())
    assert une_permission() not in avant
    permissions = [p.pk for p in avant] + [une_permission().pk]

    reponse = client.post(url_groupe(finance), formulaire_groupe(finance, permissions=permissions))

    assert reponse.status_code == 403
    assert set(finance.permissions.all()) == avant


def test_le_superutilisateur_gere_les_groupes(client, superutilisateur, finance):
    client.force_login(superutilisateur)
    permissions = [une_permission().pk]

    assert client.post(url_groupe(), {"name": "stagiaires", "permissions": []}).status_code == 302
    reponse = client.post(url_groupe(finance), formulaire_groupe(finance, permissions=permissions))
    assert reponse.status_code == 302
    stagiaires = Group.objects.get(name="stagiaires")
    assert client.post(url_groupe(stagiaires, "delete"), {"post": "yes"}).status_code == 302

    assert list(finance.permissions.values_list("pk", flat=True)) == permissions
    assert not Group.objects.filter(name="stagiaires").exists()


def test_le_superutilisateur_renomme_un_groupe(client, superutilisateur):
    groupe = Group.objects.create(name="stagiaires")
    client.force_login(superutilisateur)

    reponse = client.post(url_groupe(groupe), formulaire_groupe(groupe, nom="apprentis"))

    assert reponse.status_code == 302
    groupe.refresh_from_db()
    assert groupe.name == "apprentis"
