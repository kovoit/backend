import pytest
from django.core.management import CommandError, call_command

from apps.accounts.models import User
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
