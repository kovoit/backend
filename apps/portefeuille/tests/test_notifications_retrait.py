"""F-063 (D-06, D-38) : retrait versé ou refusé (back-office), une notification par issue."""

import pytest
from django.core import mail
from django.db import transaction

from apps.notifications.models import Notification
from apps.portefeuille import services
from apps.portefeuille.models import StatutTransaction, Transaction, TypeTransaction
from apps.portefeuille.tests.test_notifications_recharge import SIMULATION, une_seule

pytestmark = pytest.mark.django_db

ADMIN = "/api/v1/admin/transactions/"
TELEPHONE = "+22890778899"


@pytest.fixture
def retrait(utilisateur, paygate):
    """PayGate configuré : 2 000 F disponibles, retrait de 1 500 F vers Mixx en attente."""
    Transaction.objects.create(
        utilisateur=utilisateur, type=TypeTransaction.RECHARGE, montant=2000,
        statut=StatutTransaction.VALIDEE, moyen_paiement="mixx",
    )  # fmt: skip
    ligne = services.retirer(utilisateur, 1500, "mixx", TELEPHONE)
    assert ligne.statut == StatutTransaction.EN_ATTENTE
    assert not Notification.objects.filter(utilisateur=utilisateur).exists()  # attente : rien
    return ligne


def test_retrait_verse(client_admin, utilisateur, retrait, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        reponse = client_admin.post(f"{ADMIN}{retrait.id}/verser/", {"reference": "MIXX-778899"})
        # Second clic : refusé (409), aucune seconde notification
        second = client_admin.post(f"{ADMIN}{retrait.id}/verser/", {"reference": "X-1"})
        assert second.status_code == 409

    assert reponse.status_code == 200
    notification = une_seule(
        utilisateur, "Retrait versé", "Retrait de 1 500 F versé sur votre compte Mixx", retrait
    )
    assert "MIXX-778899" not in notification.message
    assert "778899" not in notification.message  # ni référence ni numéro
    assert [(m.to, m.subject) for m in mail.outbox] == [
        ([utilisateur.email], "Kovoit — Retrait versé")
    ]


def test_retrait_refuse_avec_motif(
    client_admin, utilisateur, retrait, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        reponse = client_admin.post(
            f"{ADMIN}{retrait.id}/refuser/", {"motif": "Numéro Mixx introuvable"}
        )

    assert reponse.status_code == 200
    une_seule(
        utilisateur,
        "Retrait refusé",
        "Retrait refusé : Numéro Mixx introuvable — le montant est de nouveau disponible",
        retrait,
    )
    assert services.solde(utilisateur).disponible == 2000
    assert len(mail.outbox) == 1


def test_retrait_refuse_annule_avec_la_transaction_rien_n_est_envoye(
    admin, utilisateur, retrait, django_capture_on_commit_callbacks
):
    with (
        django_capture_on_commit_callbacks(execute=True) as rappels,
        pytest.raises(RuntimeError),
        transaction.atomic(),
    ):
        services.traiter_retrait(admin, retrait.id, verse=False, motif="Doublon")
        raise RuntimeError

    assert rappels == []
    assert not Notification.objects.filter(utilisateur=utilisateur).exists()
    assert mail.outbox == []
    assert Transaction.objects.get(id=retrait.id).statut == StatutTransaction.EN_ATTENTE


def test_retrait_verse_automatiquement(utilisateur, settings, django_capture_on_commit_callbacks):
    """Fournisseur à versement automatique (simulation) : versé tout de suite, notifié une fois."""
    settings.PAIEMENT_PROVIDER = SIMULATION
    Transaction.objects.create(
        utilisateur=utilisateur, type=TypeTransaction.RECHARGE, montant=1000,
        statut=StatutTransaction.VALIDEE, moyen_paiement="flooz",
    )  # fmt: skip

    with django_capture_on_commit_callbacks(execute=True):
        ligne = services.retirer(utilisateur, 1000, "flooz", TELEPHONE)

    assert ligne.statut == StatutTransaction.VALIDEE
    une_seule(
        utilisateur, "Retrait versé", "Retrait de 1 000 F versé sur votre compte Flooz", ligne
    )
    assert len(mail.outbox) == 1
