import pytest
from django.core.management import CommandError, call_command

from apps.accounts.models import User
from apps.accounts.tests.factories import UserFactory
from apps.audit.models import EvenementAudit
from apps.kyc.models import KycDossier, KycPiece
from apps.parametres.models import Parametre
from apps.portefeuille import services as portefeuille
from apps.portefeuille.models import Transaction
from apps.reservations.models import Reservation
from apps.trajets.models import Trajet
from conftest import demander, publier_trajet

pytestmark = pytest.mark.django_db


@pytest.fixture
def en_dev(settings, admin, tmp_path):
    settings.DEBUG = True
    settings.PRIVATE_MEDIA_ROOT = str(tmp_path)
    return admin


def test_supprime_les_donnees_de_demo_et_garde_le_reste(
    en_dev, conducteur, passager, tmp_path, django_capture_on_commit_callbacks
):
    reel = Reservation.objects.get(id=demander(passager, publier_trajet(conducteur)).id)
    parametres = Parametre.objects.count()
    call_command("seed_backoffice")
    call_command("seed_demo")
    assert any(tmp_path.rglob("*.png"))

    with django_capture_on_commit_callbacks(execute=True):
        call_command("purger_demo", oui=True)

    restants = set(User.objects.values_list("id", flat=True))
    assert restants == {en_dev.id, conducteur.id, passager.id}
    assert list(Reservation.objects.values_list("id", flat=True)) == [reel.id]
    assert set(Trajet.objects.values_list("conducteur_id", flat=True)) == {conducteur.id}
    assert set(Transaction.objects.values_list("utilisateur_id", flat=True)) == {passager.id}
    assert portefeuille.solde(passager).total == 5000
    assert set(KycDossier.objects.values_list("utilisateur_id", flat=True)) == {
        conducteur.id,
        passager.id,
    }
    assert not KycPiece.objects.exists()
    assert not any(tmp_path.rglob("*.png"))
    assert not any(path.is_dir() for path in (tmp_path / "kyc").iterdir())
    assert Parametre.objects.count() == parametres
    demo = EvenementAudit.objects.exclude(acteur_id__in=restants).exclude(acteur_id=None)
    assert not demo.exists()


def test_simuler_ne_supprime_rien(en_dev):
    call_command("seed_demo")
    avant = User.objects.count()

    call_command("purger_demo", simuler=True)

    assert User.objects.count() == avant


def test_demande_confirmation(en_dev, monkeypatch):
    call_command("seed_demo")
    monkeypatch.setattr("builtins.input", lambda _message: "non")

    call_command("purger_demo")

    assert User.objects.filter(email__endswith=".demo@kovoit.tg").exists()


def test_ne_supprime_jamais_un_administrateur(en_dev):
    UserFactory(email="chef.demo@kovoit.tg", is_staff=True)

    call_command("purger_demo", oui=True)

    assert User.objects.filter(email="chef.demo@kovoit.tg").exists()


def test_refuse_hors_developpement(settings):
    settings.DEBUG = False

    with pytest.raises(CommandError, match="développement"):
        call_command("purger_demo", oui=True)
