"""Cycle de vie d'une réservation et mouvements du portefeuille associés (PRD §6, §7)."""

from datetime import timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from apps.core.exceptions import ActionInterdite, Conflit, TransitionInvalide
from apps.portefeuille import services as portefeuille
from apps.reservations import services
from apps.reservations.code_depart import calculer_code
from apps.reservations.models import StatutReservation as S
from apps.trajets.models import StatutTrajet
from conftest import demander, publier_trajet

pytestmark = pytest.mark.django_db


def test_demande_bloque_le_montant(passager, reservation):
    solde = portefeuille.solde(passager)

    assert reservation.statut == S.DEMANDEE
    assert reservation.prix == 300
    assert (solde.total, solde.bloque, solde.disponible) == (5000, 300, 4700)


def test_demande_refusee_si_solde_insuffisant(utilisateur, trajet):
    with pytest.raises(portefeuille.SoldeInsuffisant):
        demander(utilisateur, trajet)


def test_pas_de_reservation_sur_son_propre_trajet_ni_en_double(conducteur, passager, trajet):
    with pytest.raises(ActionInterdite):
        demander(conducteur, trajet)
    demander(passager, trajet)
    with pytest.raises(Conflit):
        demander(passager, trajet)


def test_acceptation_retire_une_place_et_rend_le_trajet_complet(conducteur, passager):
    trajet = publier_trajet(conducteur, places=1)

    reservation = services.accepter(conducteur, demander(passager, trajet).id)

    trajet.refresh_from_db()
    assert reservation.statut == S.ACCEPTEE and reservation.acceptee_le
    assert (trajet.places_restantes, trajet.statut) == (0, StatutTrajet.COMPLET)
    assert len(calculer_code(reservation)) == 4


def test_plus_de_place_pour_une_seconde_acceptation(conducteur, passager, utilisateur):
    trajet = publier_trajet(conducteur, places=1)
    portefeuille.recharger(utilisateur, 1000)
    premiere, seconde = demander(passager, trajet), None
    from apps.kyc.tests.factories import verifier_kyc

    verifier_kyc(utilisateur, "passager")
    seconde = demander(utilisateur, trajet)
    services.accepter(conducteur, premiere.id)

    with pytest.raises(Conflit) as exc:
        services.accepter(conducteur, seconde.id)
    assert exc.value.code == "PLUS_DE_PLACE"


def test_refus_debloque_le_montant(conducteur, passager, reservation):
    services.refuser(conducteur, reservation.id)

    assert portefeuille.solde(passager).bloque == 0


def test_annulation_rend_la_place_et_n_est_pas_tardive_longtemps_avant(
    conducteur, passager, reservation_acceptee
):
    reservation = services.annuler(passager, reservation_acceptee.id)

    reservation_acceptee.trajet.refresh_from_db()
    assert reservation.statut == S.ANNULEE and not reservation.annulation_tardive
    assert reservation_acceptee.trajet.places_restantes == 3
    assert portefeuille.solde(passager).disponible == 5000


def test_annulation_tardive_moins_de_30_minutes_avant(conducteur, passager):
    trajet = publier_trajet(conducteur, depart_dans=timedelta(minutes=20))
    reservation = services.accepter(conducteur, demander(passager, trajet).id)

    assert services.annuler(passager, reservation.id).annulation_tardive


def test_code_de_depart_correct_debite_le_passager(conducteur, passager, reservation_acceptee):
    code = calculer_code(reservation_acceptee)

    reservation = services.saisir_code(conducteur, reservation_acceptee.id, code)

    reservation.trajet.refresh_from_db()
    assert reservation.statut == S.EN_COURS
    assert reservation.trajet.statut == StatutTrajet.EN_COURS
    solde = portefeuille.solde(passager)
    assert (solde.total, solde.bloque) == (4700, 0)


def test_code_de_depart_faux_puis_bloque(conducteur, reservation_acceptee):
    bon = calculer_code(reservation_acceptee)
    faux = "0000" if bon != "0000" else "1111"
    for _ in range(5):
        with pytest.raises(services.CodeDepartInvalide):
            services.saisir_code(conducteur, reservation_acceptee.id, faux)

    with pytest.raises(services.CodeDepartBloque):
        services.saisir_code(conducteur, reservation_acceptee.id, bon)


def test_absence_trop_tot_puis_acceptee_apres_la_tolerance(
    conducteur, passager, reservation_acceptee
):
    with pytest.raises(Conflit):
        services.declarer_absent(conducteur, reservation_acceptee.id, 6.17, 1.17)

    with freeze_time(reservation_acceptee.trajet.depart_le + timedelta(minutes=11)):
        reservation = services.declarer_absent(conducteur, reservation_acceptee.id, 6.17, 1.17)

    assert reservation.statut == S.ABSENT and reservation.absence_lat == 6.17
    assert portefeuille.solde(passager).total == 4700
    assert portefeuille.solde(conducteur).total == 300


def monter_puis_terminer(conducteur, reservation):
    services.saisir_code(conducteur, reservation.id, calculer_code(reservation))
    from apps.trajets.services import terminer

    terminer(conducteur, reservation.trajet_id)
    reservation.refresh_from_db()
    return reservation


def test_fin_de_trajet_puis_confirmation_credite_le_conducteur(
    conducteur, passager, reservation_acceptee
):
    reservation = monter_puis_terminer(conducteur, reservation_acceptee)
    assert reservation.statut == S.TERMINEE

    reservation = services.confirmer_arrivee(passager, reservation.id)

    assert reservation.statut == S.CLOTUREE
    assert portefeuille.solde(conducteur).total == 300


def test_cloture_automatique_apres_le_delai(conducteur, reservation_acceptee):
    reservation = monter_puis_terminer(conducteur, reservation_acceptee)

    assert services.cloturer_automatiquement() == 0
    with freeze_time(timezone.now() + timedelta(hours=3, minutes=1)):
        from apps.reservations.tasks import cloturer_reservations

        assert cloturer_reservations() == 1
    reservation.refresh_from_db()
    assert reservation.statut == S.CLOTUREE


def test_transitions_interdites(conducteur, passager, reservation):
    with pytest.raises(Conflit):
        services.confirmer_arrivee(passager, reservation.id)
    services.refuser(conducteur, reservation.id)
    with pytest.raises(TransitionInvalide):
        services.accepter(conducteur, reservation.id)
