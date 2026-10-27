"""F-013 : la notification est écrite dans la transaction de l'appelant ; push et email ne
partent qu'après sa validation (aussitôt hors transaction), jamais après une annulation."""

import logging
from smtplib import SMTPException
from unittest import mock

import pytest
from django.core import mail
from django.db import transaction

from apps.notifications import services
from apps.notifications.models import Notification
from apps.notifications.push import FakePushSender

# serialized_rollback : le vidage de fin de test ne recrée pas les content types, que les
# tests suivants avec serialized_rollback (portefeuille) rechargent eux-mêmes.
VRAIES_TRANSACTIONS = {"transaction": True, "serialized_rollback": True}


class Erreur(Exception):
    pass


@pytest.mark.django_db
def test_transaction_annulee_rien_n_est_envoye(utilisateur, django_capture_on_commit_callbacks):
    services.enregistrer_appareil(utilisateur, "fcm-1", "android")

    with (
        django_capture_on_commit_callbacks(execute=True) as rappels,
        pytest.raises(Erreur),
        transaction.atomic(),
    ):
        services.notifier(utilisateur, "Titre", "Message")
        raise Erreur

    assert rappels == []
    assert FakePushSender.envoyes == []
    assert mail.outbox == []
    assert not Notification.objects.filter(utilisateur=utilisateur).exists()


@pytest.mark.django_db
def test_atomic_imbriques_rien_avant_la_sortie_puis_un_seul_email(
    utilisateur, django_capture_on_commit_callbacks
):
    with (
        django_capture_on_commit_callbacks(execute=True) as rappels,
        transaction.atomic(),
        transaction.atomic(),
    ):
        services.notifier(utilisateur, "Titre", "Message")
        assert mail.outbox == []
        assert Notification.objects.filter(utilisateur=utilisateur).count() == 1

    assert len(rappels) == 1
    assert [m.subject for m in mail.outbox] == ["Kovoit — Titre"]


@pytest.mark.django_db(**VRAIES_TRANSACTIONS)
def test_hors_transaction_l_email_part_aussitot(utilisateur):
    services.notifier(utilisateur, "Titre", "Message")

    assert [m.subject for m in mail.outbox] == ["Kovoit — Titre"]


@pytest.mark.django_db(**VRAIES_TRANSACTIONS)
def test_vraie_transaction_envoi_apres_validation_et_rien_si_annulee(utilisateur):
    with transaction.atomic():
        services.notifier(utilisateur, "Validée", "Message")
        assert mail.outbox == []
    assert [m.subject for m in mail.outbox] == ["Kovoit — Validée"]

    with pytest.raises(Erreur), transaction.atomic():
        services.notifier(utilisateur, "Annulée", "Message")
        raise Erreur

    assert [m.subject for m in mail.outbox] == ["Kovoit — Validée"]
    titres = Notification.objects.filter(utilisateur=utilisateur).values_list("titre", flat=True)
    assert list(titres) == ["Validée"]


@pytest.mark.django_db
def test_boucle_les_push_partent_dans_l_ordre(utilisateur, django_capture_on_commit_callbacks):
    services.enregistrer_appareil(utilisateur, "fcm-1", "android")

    with django_capture_on_commit_callbacks(execute=True), transaction.atomic():
        for n in range(3):
            services.notifier(utilisateur, f"T{n}", "Message")

    assert [e["titre"] for e in FakePushSender.envoyes] == ["T0", "T1", "T2"]


@pytest.mark.django_db
def test_un_envoi_en_echec_n_empeche_pas_le_suivant_et_est_journalise(
    utilisateur, django_capture_on_commit_callbacks, caplog
):
    def envoyer(sujet, *args, **kwargs):
        if sujet == "Kovoit — T1":
            raise SMTPException("SMTP en panne")
        return 1

    caplog.set_level(logging.ERROR)
    with (
        mock.patch("apps.notifications.tasks.send_mail", side_effect=envoyer) as send_mail,
        django_capture_on_commit_callbacks(execute=True),
        transaction.atomic(),
    ):
        services.notifier(utilisateur, "T1", "Message")
        services.notifier(utilisateur, "T2", "Message")

    assert [appel.args[0] for appel in send_mail.call_args_list] == ["Kovoit — T1", "Kovoit — T2"]
    erreurs = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(erreurs) == 1
    assert "diffuser" in erreurs[0].getMessage()


@pytest.mark.django_db
def test_tache_eager_en_echec_tentee_une_seule_fois(utilisateur):
    panne = SMTPException("SMTP en panne")
    with (
        mock.patch("apps.notifications.tasks.send_mail", side_effect=panne) as send_mail,
        pytest.raises(SMTPException),
    ):
        services.envoyer_email(utilisateur.email, "Sujet", "Message")

    assert send_mail.call_count == 1
