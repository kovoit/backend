"""Écran « Notifications » : chaque notification envoyée est conservée et consultable."""

import pytest

from apps.notifications import services
from apps.notifications.push import FakePushSender

pytestmark = pytest.mark.django_db

URL = "/api/v1/notifications/"


def test_notification_conservee_meme_sans_telephone(client_utilisateur, utilisateur):
    services.notifier(utilisateur, "Réservation acceptée", "Votre place est confirmée.", {"x": "1"})

    reponse = client_utilisateur.get(URL)

    notification = reponse.json()["reponse"]["results"][0]
    assert (notification["titre"], notification["donnees"]) == ("Réservation acceptée", {"x": "1"})
    assert notification["lue_le"] is None
    assert client_utilisateur.get(f"{URL}non-lues/").json()["reponse"]["nombre"] == 1


def test_le_push_porte_l_identifiant_de_la_notification(
    client_utilisateur, utilisateur, django_capture_on_commit_callbacks
):
    services.enregistrer_appareil(utilisateur, "jeton-1", "android")
    with django_capture_on_commit_callbacks(execute=True):
        services.notifier(utilisateur, "Titre", "Message")

    identifiant = client_utilisateur.get(URL).json()["reponse"]["results"][0]["id"]
    assert FakePushSender.envoyes[-1]["donnees"]["notification_id"] == identifiant


def test_marquer_lue_et_tout_lire(client_utilisateur, utilisateur):
    for n in range(3):
        services.notifier(utilisateur, f"Titre {n}", "Message")
    premiere = client_utilisateur.get(URL).json()["reponse"]["results"][0]

    lue = client_utilisateur.post(f"{URL}{premiere['id']}/lue/").json()["reponse"]
    assert lue["lue_le"] is not None
    assert client_utilisateur.get(f"{URL}non-lues/").json()["reponse"]["nombre"] == 2
    client_utilisateur.post(f"{URL}tout-lire/")
    assert client_utilisateur.get(f"{URL}non-lues/").json()["reponse"]["nombre"] == 0


def test_chacun_ne_voit_que_ses_notifications(client_de, utilisateur, admin):
    services.notifier(admin, "Privé", "Pour l'admin seulement")
    autre = client_de(utilisateur)

    assert autre.get(URL).json()["reponse"]["results"] == []
    identifiant = client_de(admin).get(URL).json()["reponse"]["results"][0]["id"]
    assert autre.post(f"{URL}{identifiant}/lue/").status_code == 404


def test_notifications_anciennes_supprimees(utilisateur):
    from datetime import timedelta

    from django.utils import timezone
    from freezegun import freeze_time

    from apps.notifications.models import Notification
    from apps.notifications.tasks import purger_notifications_anciennes

    with freeze_time(timezone.now() - timedelta(days=91)):
        services.notifier(utilisateur, "Ancienne", "Message")
    services.notifier(utilisateur, "Récente", "Message")

    assert purger_notifications_anciennes() == 1
    assert list(Notification.objects.values_list("titre", flat=True)) == ["Récente"]
