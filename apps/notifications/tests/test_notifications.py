from unittest import mock

import pytest
from django.core import mail
from kombu.exceptions import OperationalError

from apps.notifications import services
from apps.notifications.push import FakePushSender

pytestmark = pytest.mark.django_db


def test_sans_appareil_la_notification_part_par_email(
    utilisateur, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        services.notifier(utilisateur, "Réservation acceptée", "Votre place est confirmée.")

    assert mail.outbox[-1].subject == "Kovoit — Réservation acceptée"
    assert FakePushSender.envoyes == []


def test_avec_appareil_la_notification_part_en_push(
    client_utilisateur, utilisateur, django_capture_on_commit_callbacks
):
    reponse = client_utilisateur.post(
        "/api/v1/notifications/appareils/", {"jeton": "fcm-123", "plateforme": "android"}
    )
    assert reponse.status_code == 201

    with django_capture_on_commit_callbacks(execute=True):
        services.notifier(utilisateur, "Bon trajet", "Prise en charge confirmée.")

    (envoi,) = FakePushSender.envoyes
    assert (envoi["jeton"], envoi["titre"]) == ("fcm-123", "Bon trajet")
    assert envoi["message"] == "Prise en charge confirmée."
    assert set(envoi["donnees"]) == {"notification_id"}  # notification conservée pour l'app
    assert mail.outbox == []


def test_retirer_un_appareil(client_utilisateur):
    client_utilisateur.post("/api/v1/notifications/appareils/", {"jeton": "x", "plateforme": "ios"})

    assert client_utilisateur.delete("/api/v1/notifications/appareils/x/").status_code == 200
    assert client_utilisateur.delete("/api/v1/notifications/appareils/x/").status_code == 404


def test_sans_broker_la_tache_s_execute_sur_place(utilisateur):
    from apps.notifications.tasks import envoyer_email_tache

    with mock.patch.object(envoyer_email_tache, "delay", side_effect=OperationalError):
        services.envoyer_email(utilisateur.email, "Sujet", "Message")

    assert mail.outbox[-1].subject == "Sujet"
