import pytest
from django.core.management import CommandError, call_command

from apps.accounts.models import User
from apps.accounts.tests.aides_auth import connecter
from apps.accounts.tests.factories import UserFactory
from apps.confiance.models import Signalement
from apps.dashboard.demo import DEMO_MOT_DE_PASSE
from apps.dashboard.demo.personnes import DOMAINE, email_de
from apps.kyc.models import KycDossier, KycPiece, StatutKyc
from apps.reservations.models import Reservation, StatutReservation
from apps.trajets.models import StatutTrajet, Trajet

pytestmark = pytest.mark.django_db


@pytest.fixture
def en_dev(settings, admin):
    settings.DEBUG = True
    return admin


def test_seed_backoffice_genere_un_jeu_coherent(en_dev):
    call_command("seed_backoffice")

    statuts_kyc = set(KycDossier.objects.values_list("statut", flat=True))
    assert {StatutKyc.VERIFIE, StatutKyc.EN_ATTENTE, StatutKyc.REJETE} <= statuts_kyc
    assert KycPiece.objects.exists()
    assert Trajet.objects.filter(statut=StatutTrajet.TERMINE).count() > 30
    assert Trajet.objects.filter(statut=StatutTrajet.PUBLIE).exists()
    statuts = set(Reservation.objects.values_list("statut", flat=True))
    assert {StatutReservation.CLOTUREE, StatutReservation.DEMANDEE} <= statuts
    assert Signalement.objects.filter(statut="traite").exists()
    comptes = User.objects.filter(email__endswith=f"@{DOMAINE}")
    assert comptes.count() == 24
    assert all(c.email_verifie and c.check_password(DEMO_MOT_DE_PASSE) for c in comptes)
    assert connecter(email_de(0), DEMO_MOT_DE_PASSE).status_code == 200


def test_seed_backoffice_ne_s_execute_qu_une_fois(en_dev):
    UserFactory(email=f"deja@{DOMAINE}")

    with pytest.raises(CommandError, match="déjà présentes"):
        call_command("seed_backoffice")


def test_seed_backoffice_refuse_hors_developpement(settings, admin):
    settings.DEBUG = False

    with pytest.raises(CommandError, match="développement"):
        call_command("seed_backoffice")


def test_seed_backoffice_exige_un_admin(settings, db):
    settings.DEBUG = True

    with pytest.raises(CommandError, match="administrateur"):
        call_command("seed_backoffice")
