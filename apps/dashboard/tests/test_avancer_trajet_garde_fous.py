"""Garde-fous de `avancer_trajet` : erreurs, plafond, départ passé, périmètre du recul."""

import uuid
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.core.exceptions import ActionInterdite
from apps.dashboard.demo import horloge
from apps.parametres.services import get_param
from apps.reservations import services as reservations
from apps.reservations.models import Reservation
from apps.trajets.models import Trajet
from conftest import demander, publier_trajet

pytestmark = pytest.mark.django_db


@pytest.fixture
def en_dev(settings):
    settings.DEBUG = True


def _depart(trajet):
    return Trajet.objects.get(id=trajet.id).depart_le


def test_service_refuse_hors_developpement(settings, trajet):
    settings.DEBUG = False
    with pytest.raises(ActionInterdite, match="réservé au développement"):
        horloge.avancer_trajet(trajet.id, 30)
    assert _depart(trajet) == trajet.depart_le


@pytest.mark.parametrize("trajet_id", [str(uuid.uuid4()), "pas-un-uuid"])
def test_trajet_inconnu_ou_id_invalide(en_dev, trajet_id):
    with pytest.raises(CommandError, match="introuvable"):
        call_command("avancer_trajet", trajet_id, minutes=5)


def test_minutes_et_heures_ne_se_combinent_pas(en_dev, trajet):
    with pytest.raises(CommandError, match="not allowed with"):
        call_command("avancer_trajet", str(trajet.id), "--minutes", "5", "--heures", "1")
    assert _depart(trajet) == trajet.depart_le


def test_duree_au_dela_du_plafond_refusee(en_dev, trajet):
    plafond = get_param("periode_incidents_j") * 24 * 60
    with pytest.raises(CommandError, match="fiabilité et les économies du mois"):
        call_command("avancer_trajet", str(trajet.id), minutes=plafond + 1)
    with pytest.raises(CommandError, match="fiabilité"):
        call_command("avancer_trajet", str(trajet.id), heures=plafond // 60 + 1)
    assert _depart(trajet) == trajet.depart_le


def test_depart_deja_passe_affiche_clairement(en_dev, trajet):
    call_command("avancer_trajet", str(trajet.id))
    depart = _depart(trajet)
    sortie = StringIO()

    call_command("avancer_trajet", str(trajet.id), stdout=sortie)

    assert "Départ déjà passé : utilisez --minutes ou --heures" in sortie.getvalue()
    assert "avancé de 0 min" not in sortie.getvalue()
    assert _depart(trajet) == depart


def test_rappel_precis_sur_l_expiration(en_dev, trajet):
    sortie = StringIO()
    call_command("avancer_trajet", str(trajet.id), minutes=5, stdout=sortie)
    assert "demandes sans réponse refusées au départ" in sortie.getvalue()
    assert (
        f"places acceptées non résolues annulées {get_param('delai_resolution_h')} h "
        "après le départ" in sortie.getvalue()
    )


def test_position_reculee(en_dev, trajet):
    position_le = timezone.now()
    Trajet.objects.filter(id=trajet.id).update(position_le=position_le)

    call_command("avancer_trajet", str(trajet.id), minutes=30)

    assert Trajet.objects.get(id=trajet.id).position_le == position_le - timedelta(minutes=30)


def test_un_autre_trajet_ne_bouge_pas(en_dev, conducteur, passager):
    avance = publier_trajet(conducteur)
    autre = publier_trajet(conducteur, depart_dans=timedelta(hours=5))
    reservations.accepter(conducteur, demander(passager, avance).id)
    reservation = reservations.accepter(conducteur, demander(passager, autre).id)

    call_command("avancer_trajet", str(avance.id), minutes=30)

    assert _depart(avance) == avance.depart_le - timedelta(minutes=30)
    assert _depart(autre) == autre.depart_le
    intacte = Reservation.objects.get(id=reservation.id)
    assert (intacte.cree_le, intacte.acceptee_le) == (reservation.cree_le, reservation.acceptee_le)
