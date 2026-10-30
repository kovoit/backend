import pytest
from django.core.management import CommandError, call_command

from apps.accounts.models import User
from apps.accounts.tests.aides_auth import connecter
from apps.dashboard.demo import COMPTES_DEMO, DEMO_MOT_DE_PASSE
from apps.trajets.models import Trajet

pytestmark = pytest.mark.django_db


def test_seed_demo_cree_les_donnees_une_seule_fois(settings, capsys):
    settings.DEBUG = True

    call_command("seed_demo")
    call_command("seed_demo")

    sortie = capsys.readouterr().out
    assert "afi.demo@kovoit.tg" in sortie and "access" in sortie
    assert User.objects.filter(email__endswith="demo@kovoit.tg").count() == 2
    assert Trajet.objects.count() == 1
    conducteur = User.objects.get(email="kodjo.demo@kovoit.tg")
    assert conducteur.vehicules.count() == 1


def test_seed_demo_refuse_hors_developpement(settings):
    settings.DEBUG = False

    with pytest.raises(CommandError):
        call_command("seed_demo")


def test_seed_demo_comptes_connectables_par_mot_de_passe(settings, capsys):
    settings.DEBUG = True

    call_command("seed_demo")

    assert DEMO_MOT_DE_PASSE in capsys.readouterr().out
    comptes = list(User.objects.filter(COMPTES_DEMO))
    assert len(comptes) == 2
    for compte in comptes:
        assert compte.has_usable_password() and compte.email_verifie
        assert compte.check_password(DEMO_MOT_DE_PASSE)
    reponse = connecter("afi.demo@kovoit.tg", DEMO_MOT_DE_PASSE)
    assert reponse.status_code == 200
    jetons = reponse.json()["reponse"]
    assert jetons["access"] and jetons["refresh"]
