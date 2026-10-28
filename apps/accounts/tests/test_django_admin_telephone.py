"""F-003 (D-62, D-63) : le Django admin applique la même règle que l'API au téléphone.

Saisie libre normalisée en +228XXXXXXXX, numéro non mobile refusé avec un message. Un ancien
numéro illisible (laissé tel quel par la migration 0007) ne bloque pas la modification d'un
autre champ de la fiche."""

import pytest

from apps.accounts.models import User
from apps.accounts.tests.aides_django_admin import ADMIN, formulaire, url_fiche
from apps.accounts.tests.factories import UserFactory
from apps.core.telephone import MESSAGE_TELEPHONE_INVALIDE

pytestmark = pytest.mark.django_db

AJOUT = f"{ADMIN}/accounts/user/add/"


@pytest.fixture
def client_super(client, superutilisateur):
    client.force_login(superutilisateur)
    return client


@pytest.fixture
def passager():
    return UserFactory(prenom="Afi", telephone="+22890000001")


def fiche_passager(compte, **changes) -> dict:
    """Fiche d'un compte non staff, sans droits d'administration."""
    donnees = formulaire(compte, **changes)
    for droit in ("is_staff", "is_superuser", "groups"):
        donnees.pop(droit)
    return donnees


def erreurs_telephone(reponse) -> list[str]:
    return list(reponse.context["adminform"].form.errors.get("telephone", []))


def test_modification_avec_tirets_enregistree_au_format_international(client_super, passager):
    reponse = client_super.post(
        url_fiche(passager), fiche_passager(passager, telephone="90-11-22-33")
    )

    assert reponse.status_code == 302
    passager.refresh_from_db()
    assert passager.telephone == "+22890112233"


def test_numero_fixe_refuse_avec_un_message(client_super, passager):
    reponse = client_super.post(
        url_fiche(passager), fiche_passager(passager, telephone="22 11 22 33")
    )

    assert reponse.status_code == 200  # fiche réaffichée avec l'erreur
    assert erreurs_telephone(reponse) == [MESSAGE_TELEPHONE_INVALIDE]
    passager.refresh_from_db()
    assert passager.telephone == "+22890000001"


def test_ancien_numero_illisible_ne_bloque_pas_un_autre_champ(client_super, passager):
    User.objects.filter(pk=passager.pk).update(telephone="22112233")  # fixe, laissé par 0007
    passager.refresh_from_db()

    reponse = client_super.post(url_fiche(passager), fiche_passager(passager, prenom="Afiwa"))

    assert reponse.status_code == 302
    passager.refresh_from_db()
    assert (passager.prenom, passager.telephone) == ("Afiwa", "22112233")


def test_ancien_numero_illisible_modifie_doit_etre_valide(client_super, passager):
    User.objects.filter(pk=passager.pk).update(telephone="22112233")
    passager.refresh_from_db()

    reponse = client_super.post(url_fiche(passager), fiche_passager(passager, telephone="22112234"))

    assert erreurs_telephone(reponse) == [MESSAGE_TELEPHONE_INVALIDE]
    passager.refresh_from_db()
    assert passager.telephone == "22112233"


def test_telephone_vide_accepte_et_enregistre_vide(client_super, passager):
    reponse = client_super.post(url_fiche(passager), fiche_passager(passager, telephone=""))

    assert reponse.status_code == 302
    passager.refresh_from_db()
    assert passager.telephone == ""


def _ajout(telephone: str) -> dict:
    return {
        "email": "Yao@Exemple.tg",
        "prenom": "Yao",
        "nom": "Mensah",
        "telephone": telephone,
        "usable_password": "true",
        "password1": "Mdp-Solide-2026!",
        "password2": "Mdp-Solide-2026!",
    }


def test_creation_normalise_le_telephone(client_super):
    reponse = client_super.post(AJOUT, _ajout("(228) 70.11.22.33"))

    assert reponse.status_code == 302
    assert User.objects.get(email="yao@exemple.tg").telephone == "+22870112233"


def test_creation_refuse_un_numero_invalide(client_super):
    reponse = client_super.post(AJOUT, _ajout("12345"))

    assert reponse.status_code == 200
    assert erreurs_telephone(reponse) == [MESSAGE_TELEPHONE_INVALIDE]
    assert not User.objects.filter(email="yao@exemple.tg").exists()


def test_creation_sans_telephone_possible(client_super):
    assert client_super.post(AJOUT, _ajout("")).status_code == 302
    assert User.objects.get(email="yao@exemple.tg").telephone == ""
