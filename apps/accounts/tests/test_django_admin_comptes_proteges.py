"""Django admin (F-058, D-37) : pour un staff non superutilisateur, un autre staff ou un
superutilisateur est intouchable (fiche, mot de passe, suppression unitaire ou en masse) ; sur sa
propre fiche, email et is_active sont en lecture seule ; un compte non-staff reste modifiable."""

import pytest

from apps.accounts.models import User
from apps.accounts.tests.aides_django_admin import (
    NOUVEAU_MOT_DE_PASSE,
    creer_gestionnaire,
    formulaire,
    formulaire_mot_de_passe,
    supprimer_en_masse,
    url_fiche,
)
from apps.accounts.tests.factories import AdminFactory, UserFactory

pytestmark = pytest.mark.django_db

ANCIEN_MOT_DE_PASSE = "Super-Mdp-2026!"


@pytest.fixture
def gestionnaire(client):
    compte = creer_gestionnaire()
    client.force_login(compte)
    return compte


@pytest.fixture
def cible_superutilisateur(superutilisateur):
    superutilisateur.set_password(ANCIEN_MOT_DE_PASSE)
    superutilisateur.save()
    return superutilisateur


@pytest.fixture(params=["staff", "superutilisateur"])
def compte_protege(request, cible_superutilisateur):
    if request.param == "superutilisateur":
        return cible_superutilisateur
    return AdminFactory(roles=["finance"], prenom="Kodjo")


def sans_is_active(donnees: dict) -> dict:
    """Case « Actif » décochée : la clé est absente du formulaire."""
    return {cle: valeur for cle, valeur in donnees.items() if cle != "is_active"}


def test_mot_de_passe_d_un_superutilisateur_refuse(client, gestionnaire, cible_superutilisateur):
    hachage = cible_superutilisateur.password
    url = url_fiche(cible_superutilisateur, "password")

    assert client.get(url).status_code == 403
    assert client.post(url, formulaire_mot_de_passe()).status_code == 403

    cible_superutilisateur.refresh_from_db()
    assert cible_superutilisateur.password == hachage
    assert cible_superutilisateur.check_password(ANCIEN_MOT_DE_PASSE)


def test_fiche_d_un_compte_protege_en_consultation_seule(client, gestionnaire, compte_protege):
    reponse = client.get(url_fiche(compte_protege))

    assert reponse.status_code == 200
    assert reponse.context["has_change_permission"] is False
    assert reponse.context["has_delete_permission"] is False


def test_modifier_un_compte_protege_refuse(client, gestionnaire, compte_protege):
    donnees = sans_is_active(formulaire(compte_protege, email="pirate@kovoit.tg"))

    assert client.post(url_fiche(compte_protege), donnees).status_code == 403

    compte_protege.refresh_from_db()
    assert compte_protege.email != "pirate@kovoit.tg"
    assert compte_protege.is_active is True


def test_supprimer_un_compte_protege_refuse(client, gestionnaire, compte_protege):
    url = url_fiche(compte_protege, "delete")

    assert client.get(url).status_code == 403
    assert client.post(url, {"post": "yes"}).status_code == 403
    assert User.objects.filter(pk=compte_protege.pk).exists()


def test_suppression_en_masse_d_un_compte_protege_refusee(client, gestionnaire, compte_protege):
    passager = UserFactory()

    assert supprimer_en_masse(client, compte_protege, passager).status_code == 403

    assert User.objects.filter(pk__in=[compte_protege.pk, passager.pk]).count() == 2


def test_email_et_is_active_en_lecture_seule_sur_sa_propre_fiche(client, gestionnaire):
    fiche = client.get(url_fiche(gestionnaire)).context["adminform"]
    assert {"email", "is_active"} <= set(fiche.readonly_fields)
    email = gestionnaire.email

    donnees = sans_is_active(formulaire(gestionnaire, email="nouveau@kovoit.tg", prenom="Ama-2"))
    assert client.post(url_fiche(gestionnaire), donnees).status_code == 302

    gestionnaire.refresh_from_db()
    assert gestionnaire.prenom == "Ama-2"  # fiche enregistrée…
    assert (gestionnaire.email, gestionnaire.is_active) == (email, True)  # … sans ces champs


def test_email_et_is_active_d_un_passager_modifiables(client, gestionnaire):
    passager = UserFactory()

    donnees = sans_is_active(formulaire(passager, email="Nouveau.Passager@kovoit.tg"))
    assert client.post(url_fiche(passager), donnees).status_code == 302

    passager.refresh_from_db()
    assert passager.email == "nouveau.passager@kovoit.tg"
    assert passager.is_active is False


def test_mot_de_passe_d_un_passager_modifiable(client, gestionnaire):
    passager = UserFactory()
    url = url_fiche(passager, "password")

    assert client.get(url).status_code == 200
    assert client.post(url, formulaire_mot_de_passe()).status_code == 302

    passager.refresh_from_db()
    assert passager.check_password(NOUVEAU_MOT_DE_PASSE)


def test_suppression_en_masse_d_un_passager_possible(client, gestionnaire):
    passager = UserFactory()

    assert supprimer_en_masse(client, passager).status_code == 302

    assert not User.objects.filter(pk=passager.pk).exists()


def test_le_superutilisateur_modifie_et_supprime_les_comptes_proteges(client, superutilisateur):
    autre_super = AdminFactory(is_superuser=True, roles=[])
    kodjo = AdminFactory(roles=["finance"], prenom="Kodjo")
    client.force_login(superutilisateur)

    url_mdp = url_fiche(autre_super, "password")
    assert client.post(url_mdp, formulaire_mot_de_passe()).status_code == 302
    donnees = sans_is_active(formulaire(kodjo, email="kodjo.finance@kovoit.tg"))
    assert client.post(url_fiche(kodjo), donnees).status_code == 302

    autre_super.refresh_from_db()
    kodjo.refresh_from_db()
    assert autre_super.check_password(NOUVEAU_MOT_DE_PASSE)
    assert (kodjo.email, kodjo.is_active) == ("kodjo.finance@kovoit.tg", False)
    assert supprimer_en_masse(client, autre_super, kodjo).status_code == 302
    assert not User.objects.filter(pk__in=[autre_super.pk, kodjo.pk]).exists()


def test_le_superutilisateur_modifie_sa_propre_fiche(client, superutilisateur):
    client.force_login(superutilisateur)

    fiche = client.get(url_fiche(superutilisateur)).context["adminform"]

    assert not {"email", "is_active"} & set(fiche.readonly_fields)
