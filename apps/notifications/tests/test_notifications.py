from unittest import mock

import pytest
from django.core import mail

from apps.notifications import services
from apps.notifications.push import FakePushSender

pytestmark = pytest.mark.django_db


def test_sans_appareil_la_notification_part_par_email(utilisateur):
    services.notifier(utilisateur, "Réservation acceptée", "Votre place est confirmée.")

    assert mail.outbox[-1].subject == "Kovoit — Réservation acceptée"
    assert FakePushSender.envoyes == []


def test_avec_appareil_la_notification_part_en_push(client_utilisateur, utilisateur):
    reponse = client_utilisateur.post(
        "/api/v1/notifications/appareils/", {"jeton": "fcm-123", "plateforme": "android"}
    )
    assert reponse.status_code == 201

    services.notifier(utilisateur, "Bon trajet", "Prise en charge confirmée.")

    assert FakePushSender.envoyes == [
        {"jeton": "fcm-123", "titre": "Bon trajet", "message": "Prise en charge confirmée."}
    ]
    assert mail.outbox == []


def test_retirer_un_appareil(client_utilisateur):
    client_utilisateur.post("/api/v1/notifications/appareils/", {"jeton": "x", "plateforme": "ios"})

    assert client_utilisateur.delete("/api/v1/notifications/appareils/x/").status_code == 200
    assert client_utilisateur.delete("/api/v1/notifications/appareils/x/").status_code == 404


def test_sans_broker_la_tache_s_execute_sur_place(utilisateur):
    from apps.notifications.tasks import envoyer_email_tache

    with mock.patch.object(envoyer_email_tache, "delay", side_effect=ConnectionError):
        services.envoyer_email(utilisateur.email, "Sujet", "Message")

    assert mail.outbox[-1].subject == "Sujet"
