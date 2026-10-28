"""F-063 (D-06) : une notification par issue de recharge, jamais pendant l'attente."""

from datetime import timedelta

import pytest
from django.core import mail
from django.db import transaction
from django.utils import timezone
from freezegun import freeze_time

from apps.accounts.tests.factories import UserFactory
from apps.kyc.tests.factories import verifier_kyc
from apps.notifications.models import Notification
from apps.portefeuille import services
from apps.portefeuille.models import Transaction
from apps.portefeuille.tasks import verifier_paiements
from apps.reservations import services as reservations
from conftest import GRAND_MARCHE

pytestmark = pytest.mark.django_db

CALLBACK = "/api/v1/paiements/paygate/callback/"
SIMULATION = "apps.portefeuille.provider.SimulationPaiementProvider"


def notifications_argent(utilisateur):
    return list(Notification.objects.filter(utilisateur=utilisateur, donnees__type="transaction"))


def une_seule(utilisateur, titre: str, message: str, ligne) -> Notification:
    notifications = notifications_argent(utilisateur)
    assert len(notifications) == 1
    notification = notifications[0]
    assert (notification.titre, notification.message) == (titre, message)
    assert notification.donnees == {"type": "transaction", "transaction_id": str(ligne.id)}
    return notification


def test_recharge_validee_en_simulation(utilisateur, settings, django_capture_on_commit_callbacks):
    settings.PAIEMENT_PROVIDER = SIMULATION

    with django_capture_on_commit_callbacks(execute=True):
        ligne = services.recharger(utilisateur, 1000, "flooz", "+22890000001")

    une_seule(utilisateur, "Recharge validée", "Recharge de 1 000 F validée", ligne)
    assert [(m.to, m.subject, m.body) for m in mail.outbox] == [
        ([utilisateur.email], "Kovoit — Recharge validée", "Recharge de 1 000 F validée")
    ]


def test_recharge_paygate_notifiee_a_la_confirmation_seulement(
    api_client, utilisateur, paygate, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        ligne = services.recharger(utilisateur, 1000, "flooz", "+22890000001")
    assert notifications_argent(utilisateur) == []  # jamais pendant l'attente
    assert mail.outbox == []

    paygate.statut_paiement = 0
    with django_capture_on_commit_callbacks(execute=True):
        api_client.post(f"{CALLBACK}?cle=cle-callback", {"identifier": str(ligne.id)})
        # Second callback et passage de la tâche : déjà traitée, rien de plus
        api_client.post(f"{CALLBACK}?cle=cle-callback", {"identifier": str(ligne.id)})
        verifier_paiements()

    notification = une_seule(utilisateur, "Recharge validée", "Recharge de 1 000 F validée", ligne)
    assert "FLZ-789" not in notification.message and "PG-123" not in notification.message
    assert len(mail.outbox) == 1


def test_recharge_annulee_par_paygate_via_la_tache(
    utilisateur, paygate, django_capture_on_commit_callbacks
):
    ligne = services.recharger(utilisateur, 1000, "mixx", "+22890000001")
    paygate.statut_paiement = 6  # annulée par le client

    with django_capture_on_commit_callbacks(execute=True):
        verifier_paiements()
        verifier_paiements()  # second passage : ne notifie pas une deuxième fois

    une_seule(utilisateur, "Recharge non aboutie", "Recharge de 1 000 F non aboutie", ligne)
    assert Transaction.objects.get(id=ligne.id).statut == "echouee"
    assert services.solde(utilisateur).total == 0
    assert len(mail.outbox) == 1


def test_recharge_abandonnee_apres_le_delai(
    utilisateur, paygate, django_capture_on_commit_callbacks
):
    with freeze_time(timezone.now()) as horloge:
        ligne = services.recharger(utilisateur, 2500, "flooz", "+22890000001")
        horloge.tick(timedelta(minutes=61))  # paiement_attente_max_min = 60, toujours en cours
        with django_capture_on_commit_callbacks(execute=True):
            verifier_paiements()
            verifier_paiements()

    notification = une_seule(
        utilisateur, "Recharge non aboutie", "Recharge de 2 500 F non aboutie", ligne
    )
    assert "90000001" not in notification.message
    assert len(mail.outbox) == 1


def test_recharge_annulee_avec_la_transaction_rien_n_est_envoye(
    utilisateur, settings, django_capture_on_commit_callbacks
):
    settings.PAIEMENT_PROVIDER = SIMULATION

    with (
        django_capture_on_commit_callbacks(execute=True) as rappels,
        pytest.raises(RuntimeError),
        transaction.atomic(),
    ):
        services.recharger(utilisateur, 1000, "flooz", "+22890000001")
        raise RuntimeError

    assert rappels == []
    assert notifications_argent(utilisateur) == []
    assert mail.outbox == []


def test_le_complement_paye_pendant_la_reservation_ne_notifie_pas(
    trajet, settings, django_capture_on_commit_callbacks
):
    settings.PAIEMENT_PROVIDER = SIMULATION
    passager = UserFactory(prenom="Kafui")  # portefeuille vide : complément payé par Flooz
    verifier_kyc(passager, "passager")

    with django_capture_on_commit_callbacks(execute=True):
        reservations.demander_place(
            passager,
            trajet_id=trajet.id,
            point_id=trajet.points.first().id,
            arrivee_lat=GRAND_MARCHE["lat"] + 0.001,
            arrivee_lng=GRAND_MARCHE["lng"],
            moyen_paiement="flooz",
        )

    assert Transaction.objects.filter(utilisateur=passager, type="recharge").count() == 1
    assert notifications_argent(passager) == []
    assert passager.email not in [destinataire for m in mail.outbox for destinataire in m.to]
