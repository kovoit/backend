import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.core.exceptions import Conflit
from apps.parametres.services import get_param
from apps.portefeuille import services as portefeuille
from apps.portefeuille.models import Transaction, TypeTransaction
from apps.reservations import services as reservations
from apps.reservations.code_depart import calculer_code
from apps.reservations.models import Reservation, StatutReservation
from apps.trajets import services as trajets
from apps.trajets.models import Trajet
from conftest import demander, publier_trajet

pytestmark = pytest.mark.django_db


@pytest.fixture
def en_dev(settings):
    settings.DEBUG = True


def _recharger(objet):
    objet.refresh_from_db()
    return objet


def test_refusee_hors_developpement(settings, trajet):
    settings.DEBUG = False
    with pytest.raises(CommandError, match="réservé au développement"):
        call_command("avancer_trajet", str(trajet.id))


def test_sans_trajet_non_clos(en_dev):
    with pytest.raises(CommandError, match="Aucun trajet"):
        call_command("avancer_trajet")


def test_duree_nulle_refusee(en_dev, trajet):
    with pytest.raises(CommandError, match="au moins 1 minute"):
        call_command("avancer_trajet", str(trajet.id), minutes=0)


def test_par_defaut_jusqu_au_depart_du_dernier_trajet(en_dev, conducteur):
    ancien = publier_trajet(conducteur, places=1)
    recent = publier_trajet(conducteur)
    depart_ancien = ancien.depart_le

    call_command("avancer_trajet")

    assert _recharger(recent).depart_le <= timezone.now()
    assert _recharger(ancien).depart_le == depart_ancien


def test_recule_les_horodatages_des_reservations(en_dev, conducteur, passager):
    trajet = publier_trajet(conducteur)
    reservation = reservations.accepter(conducteur, demander(passager, trajet).id)
    acceptee_le, cree_le = reservation.acceptee_le, reservation.cree_le

    call_command("avancer_trajet", str(trajet.id), minutes=30)

    reservation = Reservation.objects.get(id=reservation.id)
    assert (acceptee_le - reservation.acceptee_le).total_seconds() == 30 * 60
    assert (cree_le - reservation.cree_le).total_seconds() == 30 * 60
    assert reservation.refusee_le is None
    assert reservation.statut == StatutReservation.ACCEPTEE


def test_demande_sans_reponse_expire_au_depart(en_dev, conducteur, passager):
    trajet = publier_trajet(conducteur)
    reservation = demander(passager, trajet)

    call_command("avancer_trajet", str(trajet.id))

    assert _recharger(reservation).statut == StatutReservation.REFUSEE


def test_absence_possible_apres_la_tolerance(en_dev, conducteur, passager):
    trajet = publier_trajet(conducteur)
    reservation = reservations.accepter(conducteur, demander(passager, trajet).id)

    call_command("avancer_trajet", str(trajet.id))  # jusqu'au départ : tolérance pas écoulée
    with pytest.raises(Conflit):
        reservations.declarer_absent(conducteur, reservation.id, 6.17, 1.17)

    call_command("avancer_trajet", str(trajet.id), minutes=get_param("tolerance_retard_min") + 1)

    reservation = reservations.declarer_absent(conducteur, reservation.id, 6.17, 1.17)
    assert reservation.statut == StatutReservation.ABSENT


def test_course_complete_puis_cloture_automatique(en_dev, conducteur, passager):
    trajet = publier_trajet(conducteur)
    reservation = reservations.accepter(conducteur, demander(passager, trajet).id)
    reservations.saisir_code(conducteur, reservation.id, calculer_code(reservation))
    trajets.terminer(conducteur, trajet.id)
    assert _recharger(reservation).statut == StatutReservation.TERMINEE

    call_command("avancer_trajet", str(trajet.id), heures=get_param("delai_confirmation_auto_h"))

    reservation = _recharger(reservation)
    assert reservation.statut == StatutReservation.CLOTUREE
    assert Trajet.objects.get(id=trajet.id).statut == "termine"
    assert portefeuille.solde(conducteur).total == reservation.prix - reservation.commission


def test_place_acceptee_sans_code_annulee_apres_le_delai_de_resolution(
    en_dev, conducteur, passager
):
    """Rapport M-005, test n° 20."""
    avant = portefeuille.solde(passager)
    trajet = publier_trajet(conducteur)
    reservation = reservations.accepter(conducteur, demander(passager, trajet).id)
    assert _recharger(trajet).places_restantes == trajet.places_total - 1

    call_command("avancer_trajet", str(trajet.id))
    assert _recharger(reservation).statut == StatutReservation.ACCEPTEE
    call_command("avancer_trajet", str(trajet.id), heures=get_param("delai_resolution_h"))

    reservation = _recharger(reservation)
    assert reservation.statut == StatutReservation.ANNULEE
    assert reservation.annulation_tardive is False
    deblocage = Transaction.objects.get(reservation=reservation, type=TypeTransaction.DEBLOCAGE)
    assert deblocage.montant == reservation.montant_total
    apres = portefeuille.solde(passager)
    assert (apres.total, apres.bloque, apres.disponible) == (avant.total, 0, avant.disponible)
    assert _recharger(trajet).places_restantes == trajet.places_total
