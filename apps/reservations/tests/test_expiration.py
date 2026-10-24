"""Expiration automatique : aucun montant ne reste bloqué après le départ."""

from datetime import timedelta

import pytest
from freezegun import freeze_time

from apps.audit.models import EvenementAudit
from apps.portefeuille import services as portefeuille
from apps.reservations import services
from apps.reservations.models import StatutReservation as S
from apps.reservations.repository import reservation_repository
from apps.reservations.tasks import expirer_reservations_en_suspens

pytestmark = pytest.mark.django_db


def test_rien_n_expire_avant_le_depart(passager, reservation, reservation_acceptee):
    assert services.expirer_reservations() == 0
    assert portefeuille.solde(passager).bloque == 300


def test_demande_sans_reponse_refusee_au_depart(passager, reservation):
    with freeze_time(reservation.trajet.depart_le + timedelta(minutes=1)):
        assert expirer_reservations_en_suspens() == 1

    reservation.refresh_from_db()
    assert reservation.statut == S.REFUSEE
    solde = portefeuille.solde(passager)
    assert (solde.bloque, solde.disponible) == (0, 5000)
    evenement = EvenementAudit.objects.get(action="reservation.expirer")
    assert evenement.details["cause"] == "sans_reponse_du_conducteur"


def test_place_acceptee_non_resolue_annulee_sans_incident(
    passager, conducteur, reservation_acceptee
):
    depart = reservation_acceptee.trajet.depart_le
    with freeze_time(depart + timedelta(hours=5)):
        assert services.expirer_reservations() == 0  # le conducteur a encore le temps
    with freeze_time(depart + timedelta(hours=6, minutes=1)):
        assert services.expirer_reservations() == 2  # la place, puis le trajet resté vide
        incidents = reservation_repository.compter_incidents(conducteur, depart - timedelta(days=1))

    reservation_acceptee.refresh_from_db()
    assert reservation_acceptee.statut == S.ANNULEE
    assert reservation_acceptee.annulation_tardive is False
    assert incidents == 0
    assert portefeuille.solde(passager).disponible == 5000


def test_une_reservation_deja_prise_en_charge_n_expire_pas(
    conducteur, passager, reservation_acceptee
):
    from apps.reservations.code_depart import calculer_code

    services.saisir_code(conducteur, reservation_acceptee.id, calculer_code(reservation_acceptee))
    with freeze_time(reservation_acceptee.trajet.depart_le + timedelta(days=1)):
        assert services.expirer_reservations() == 1  # seul le trajet est clos

    reservation_acceptee.refresh_from_db()
    assert reservation_acceptee.statut == S.TERMINEE  # pas annulée : le passager était monté
    assert portefeuille.solde(passager).total == 4700  # débité une seule fois


def test_trajet_jamais_termine_clos_et_conducteur_paye(conducteur, passager, reservation_acceptee):
    """Le conducteur oublie « Terminer le trajet » : le passager monté ne reste pas bloqué."""
    from apps.reservations.code_depart import calculer_code
    from apps.trajets.models import StatutTrajet

    services.saisir_code(conducteur, reservation_acceptee.id, calculer_code(reservation_acceptee))
    depart = reservation_acceptee.trajet.depart_le
    with freeze_time(depart + timedelta(hours=6, minutes=1)):
        assert services.expirer_reservations() == 1
    reservation_acceptee.refresh_from_db()
    reservation_acceptee.trajet.refresh_from_db()
    assert reservation_acceptee.statut == S.TERMINEE
    assert reservation_acceptee.trajet.statut == StatutTrajet.TERMINE

    with freeze_time(depart + timedelta(hours=10)):  # puis clôture automatique habituelle
        services.cloturer_automatiquement()
    assert portefeuille.solde(conducteur).total == 255  # payé, net de commission


def test_trajet_sans_passager_monte_annule(conducteur, trajet):
    from apps.trajets.models import StatutTrajet

    with freeze_time(trajet.depart_le + timedelta(hours=7)):
        services.expirer_reservations()
    trajet.refresh_from_db()
    assert trajet.statut == StatutTrajet.ANNULE
