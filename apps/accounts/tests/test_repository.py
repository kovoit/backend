import pytest

from apps.accounts.repository import user_repository

pytestmark = pytest.mark.django_db


def test_creer_met_l_email_en_minuscules_et_mot_de_passe_inutilisable():
    utilisateur = user_repository.creer(
        "  Kossi.Amegah@Exemple.TG ", telephone="+22890000001", nom="Amegah", prenom="Kossi"
    )

    assert utilisateur.email == "kossi.amegah@exemple.tg"
    assert not utilisateur.has_usable_password()
    assert utilisateur.mode_actif == "passager"
    assert utilisateur.statut_compte == "actif"


def test_get_par_email_ignore_la_casse(utilisateur):
    assert user_repository.get_par_email(utilisateur.email.upper()) == utilisateur


def test_get_par_email_inconnu_renvoie_none():
    assert user_repository.get_par_email("inconnu@exemple.tg") is None
