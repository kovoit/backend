import pytest
from django.core.management import CommandError, call_command

from apps.accounts.tests.factories import UserFactory
from apps.confiance.models import Signalement
from apps.core.demo.personnes import DOMAINE
from apps.kyc.models import KycDossier, KycPiece, StatutKyc
from apps.reservations.models import Reservation, StatutReservation
from apps.trajets.models import StatutTrajet, Trajet

pytestmark = pytest.mark.django_db


@pytest.fixture
def en_dev(settings, admin):
    settings.DEBUG = True
    return admin


def test_seed_demo_genere_un_jeu_coherent(en_dev):
    call_command("seed_demo")

    statuts_kyc = set(KycDossier.objects.values_list("statut", flat=True))
    assert {StatutKyc.VERIFIE, StatutKyc.EN_ATTENTE, StatutKyc.REJETE} <= statuts_kyc
    assert KycPiece.objects.exists()
    assert Trajet.objects.filter(statut=StatutTrajet.TERMINE).count() > 30
    assert Trajet.objects.filter(statut=StatutTrajet.PUBLIE).exists()
    statuts = set(Reservation.objects.values_list("statut", flat=True))
    assert {StatutReservation.CLOTUREE, StatutReservation.DEMANDEE} <= statuts
    assert Signalement.objects.filter(statut="traite").exists()


def test_seed_demo_ne_s_execute_qu_une_fois(en_dev):
    UserFactory(email=f"deja@{DOMAINE}")

    with pytest.raises(CommandError, match="déjà présentes"):
        call_command("seed_demo")


def test_seed_demo_refuse_hors_developpement(settings, admin):
    settings.DEBUG = False

    with pytest.raises(CommandError, match="développement"):
        call_command("seed_demo")


def test_seed_demo_exige_un_admin(settings, db):
    settings.DEBUG = True

    with pytest.raises(CommandError, match="administrateur"):
        call_command("seed_demo")
