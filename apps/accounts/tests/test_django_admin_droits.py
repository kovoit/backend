"""Django admin (F-058, D-37) : seuls les superutilisateurs attribuent les droits d'administration.
Un staff autorisé à modifier les comptes ne peut ni s'attribuer un rôle, ni devenir
superutilisateur, ni promouvoir un autre compte, ni modifier, ni supprimer un staff ou un
superutilisateur (voir test_django_admin_comptes_proteges.py et test_django_admin_groupes.py)."""

import pytest
from django.contrib.auth.models import Group

from apps.accounts.tests.aides_django_admin import (
    creer_gestionnaire,
    formulaire,
    groupes,
    url_fiche,
)
from apps.accounts.tests.factories import AdminFactory, UserFactory

pytestmark = pytest.mark.django_db

DROITS = {"is_staff", "is_superuser", "groups"}


@pytest.fixture
def gestionnaire_comptes():
    return creer_gestionnaire()


def test_droits_en_lecture_seule_pour_un_non_superutilisateur(client, gestionnaire_comptes):
    client.force_login(gestionnaire_comptes)

    reponse = client.get(url_fiche(gestionnaire_comptes))

    assert reponse.status_code == 200
    fiche = reponse.context["adminform"]
    assert set(fiche.readonly_fields) >= DROITS
    assert not DROITS & set(fiche.form.fields)


def test_un_non_superutilisateur_ne_peut_pas_s_attribuer_de_droits(client, gestionnaire_comptes):
    client.force_login(gestionnaire_comptes)

    reponse = client.post(
        url_fiche(gestionnaire_comptes), formulaire(gestionnaire_comptes, prenom="Ama-Modifiee")
    )

    assert reponse.status_code == 302  # fiche enregistrée…
    gestionnaire_comptes.refresh_from_db()
    assert gestionnaire_comptes.prenom == "Ama-Modifiee"
    assert gestionnaire_comptes.is_superuser is False  # … sans les droits demandés
    assert groupes(gestionnaire_comptes) == set()


def test_un_non_superutilisateur_ne_peut_pas_promouvoir_un_compte(client, gestionnaire_comptes):
    passager = UserFactory()
    client.force_login(gestionnaire_comptes)

    assert client.post(url_fiche(passager), formulaire(passager)).status_code == 302

    passager.refresh_from_db()
    assert (passager.is_staff, passager.is_superuser) == (False, False)
    assert groupes(passager) == set()


def test_un_superutilisateur_attribue_les_droits(client, superutilisateur):
    ama = AdminFactory(roles=[], prenom="Ama")
    client.force_login(superutilisateur)

    fiche = client.get(url_fiche(ama)).context["adminform"]
    assert not DROITS & set(fiche.readonly_fields)
    assert client.post(url_fiche(ama), formulaire(ama)).status_code == 302

    ama.refresh_from_db()
    assert ama.is_superuser is True
    assert groupes(ama) == {"finance", "audit"}


def test_ca7_groupe_ajoute_dans_le_django_admin_visible_a_la_requete_suivante(
    client, client_de, superutilisateur
):
    ama = AdminFactory(roles=[], prenom="Ama")
    api = client_de(ama)
    assert api.get("/api/v1/admin/audit/evenements/").status_code == 403
    client.force_login(superutilisateur)

    donnees = formulaire(ama, groups=[Group.objects.get(name="audit").pk])
    del donnees["is_superuser"]
    assert client.post(url_fiche(ama), donnees).status_code == 302

    assert api.get("/api/v1/auth/admin/moi/").json()["reponse"]["roles"] == ["audit"]
    assert api.get("/api/v1/admin/audit/evenements/").status_code == 200
