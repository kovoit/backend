"""F-013, non-régression : chaque flux métier notifie une seule fois, après validation ;
une opération annulée (journal d'audit en échec) n'envoie rien."""

from unittest import mock

import pytest
from django.core import mail

from apps.accounts import services as comptes
from apps.accounts.tests.factories import UserFactory
from apps.kyc.tests.factories import verifier_kyc
from apps.notifications.models import Notification
from apps.notifications.push import FakePushSender
from apps.notifications.services import enregistrer_appareil
from apps.portefeuille import services as portefeuille
from apps.reservations import services as reservations
from apps.reservations.code_depart import calculer_code
from apps.reservations.models import StatutReservation as S
from apps.trajets import services as trajets
from apps.trajets.models import StatutTrajet
from conftest import demander

pytestmark = pytest.mark.django_db

JOURNAL_TRAJET = "apps.trajets.services.gestion.journaliser"
JOURNAL_SUSPENSION = "apps.accounts.services.suspension.journaliser"


def _passager_avec_telephone(prenom):
    utilisateur = UserFactory(prenom=prenom)
    verifier_kyc(utilisateur, "passager")
    portefeuille.recharger(utilisateur, 5000, "flooz")
    enregistrer_appareil(utilisateur, f"jeton-{prenom}", "android")
    return utilisateur


def _push():
    return [(e["jeton"], e["titre"]) for e in FakePushSender.envoyes]


def test_acceptation_un_seul_push_au_passager(
    conducteur, passager, reservation, django_capture_on_commit_callbacks
):
    enregistrer_appareil(passager, "jeton-passager", "android")
    enregistrer_appareil(conducteur, "jeton-conducteur", "android")
    FakePushSender.envoyes = []

    with django_capture_on_commit_callbacks(execute=True):
        reservations.accepter(conducteur, reservation.id)

    assert [jeton for jeton, _ in _push()] == ["jeton-passager"]


def test_annulation_par_le_passager_un_seul_push_au_conducteur(
    conducteur, passager, reservation, django_capture_on_commit_callbacks
):
    enregistrer_appareil(passager, "jeton-passager", "android")
    enregistrer_appareil(conducteur, "jeton-conducteur", "android")
    FakePushSender.envoyes = []

    with django_capture_on_commit_callbacks(execute=True):
        reservations.annuler(passager, reservation.id)

    assert _push() == [("jeton-conducteur", "Réservation annulée par le passager")]


def test_annulation_du_trajet_un_push_par_passager(
    conducteur, trajet, django_capture_on_commit_callbacks
):
    demander(_passager_avec_telephone("A"), trajet)
    demander(_passager_avec_telephone("B"), trajet)
    FakePushSender.envoyes = []

    with django_capture_on_commit_callbacks(execute=True):
        trajets.annuler(conducteur, trajet.id)

    assert sorted(jeton for jeton, _ in _push()) == ["jeton-A", "jeton-B"]


def test_annulation_du_trajet_annulee_rien_n_est_envoye(
    conducteur, trajet, django_capture_on_commit_callbacks
):
    premiere = demander(_passager_avec_telephone("A"), trajet)
    seconde = demander(_passager_avec_telephone("B"), trajet)
    FakePushSender.envoyes = []
    avant = Notification.objects.count()

    with (
        django_capture_on_commit_callbacks(execute=True),
        mock.patch(JOURNAL_TRAJET, side_effect=RuntimeError),
        pytest.raises(RuntimeError),
    ):
        trajets.annuler(conducteur, trajet.id)

    assert FakePushSender.envoyes == []
    assert Notification.objects.count() == avant
    for reservation in (premiere, seconde, trajet):
        reservation.refresh_from_db()
    assert (premiere.statut, seconde.statut) == (S.DEMANDEE, S.DEMANDEE)
    assert trajet.statut == StatutTrajet.PUBLIE


def _monter(conducteur, passager, reservation):
    enregistrer_appareil(passager, "jeton-passager", "android")
    reservations.saisir_code(conducteur, reservation.id, calculer_code(reservation))
    FakePushSender.envoyes = []


def test_fin_de_trajet_un_seul_trajet_termine(
    conducteur, passager, reservation_acceptee, django_capture_on_commit_callbacks
):
    _monter(conducteur, passager, reservation_acceptee)

    with django_capture_on_commit_callbacks(execute=True):
        trajets.terminer(conducteur, reservation_acceptee.trajet_id)

    assert _push() == [("jeton-passager", "Trajet terminé")]


def test_fin_de_trajet_annulee_rien_n_est_envoye(
    conducteur, passager, reservation_acceptee, django_capture_on_commit_callbacks
):
    _monter(conducteur, passager, reservation_acceptee)
    mail.outbox = []

    with (
        django_capture_on_commit_callbacks(execute=True),
        mock.patch(JOURNAL_TRAJET, side_effect=RuntimeError),
        pytest.raises(RuntimeError),
    ):
        trajets.terminer(conducteur, reservation_acceptee.trajet_id)

    assert FakePushSender.envoyes == []
    assert mail.outbox == []
    reservation_acceptee.refresh_from_db()
    assert reservation_acceptee.statut == S.EN_COURS


def test_suspension_par_admin_validee_email_envoye(
    passager, reservation, django_capture_on_commit_callbacks
):
    mail.outbox = []

    with django_capture_on_commit_callbacks(execute=True):
        comptes.suspendre_par_admin(passager, "motif", 7)

    assert "Kovoit — Compte suspendu" in [m.subject for m in mail.outbox]


def test_suspension_par_admin_annulee_aucun_email(
    passager, reservation, django_capture_on_commit_callbacks
):
    mail.outbox = []

    with (
        django_capture_on_commit_callbacks(execute=True),
        mock.patch(JOURNAL_SUSPENSION, side_effect=RuntimeError),
        pytest.raises(RuntimeError),
    ):
        comptes.suspendre_par_admin(passager, "motif", 7)

    assert mail.outbox == []
