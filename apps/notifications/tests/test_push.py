"""Push réel (FCM) ou simulé, nettoyage des jetons périmés et email de secours."""

from unittest import mock

import pytest
from django.core import mail

from apps.notifications import services
from apps.notifications.fcm import FcmPushSender
from apps.notifications.models import AppareilNotification
from apps.notifications.push import FakePushSender

pytestmark = pytest.mark.django_db


@pytest.fixture
def appareil(utilisateur):
    return services.enregistrer_appareil(utilisateur, "fcm-abc", "android")


def test_firebase_non_configure_push_journalise_et_email_envoye(settings, utilisateur, appareil):
    settings.NOTIFICATIONS_PUSH_SENDER = "apps.notifications.push.JournalPushSender"

    services.notifier(utilisateur, "Réservation acceptée", "Votre place est confirmée.")

    assert [m.subject for m in mail.outbox] == ["Kovoit — Réservation acceptée"]


def test_jeton_perime_supprime_et_email_de_secours(utilisateur, appareil):
    FakePushSender.jetons_invalides = {"fcm-abc"}
    try:
        services.notifier(utilisateur, "Bon trajet", "Prise en charge confirmée.")
    finally:
        FakePushSender.jetons_invalides = set()

    assert not AppareilNotification.objects.filter(jeton="fcm-abc").exists()
    assert mail.outbox[-1].subject == "Kovoit — Bon trajet"


def test_un_appareil_valide_suffit_pas_d_email(utilisateur, appareil):
    services.enregistrer_appareil(utilisateur, "fcm-perime", "ios")
    FakePushSender.jetons_invalides = {"fcm-perime"}
    try:
        services.notifier(utilisateur, "Bon trajet", "Prise en charge confirmée.")
    finally:
        FakePushSender.jetons_invalides = set()

    assert [e["jeton"] for e in FakePushSender.envoyes] == ["fcm-abc"]
    assert mail.outbox == []


@mock.patch("apps.notifications.fcm._application")
@mock.patch("apps.notifications.fcm.messaging.send")
def test_fcm_envoie_titre_message_et_donnees_en_texte(envoyer, _application):
    assert FcmPushSender().envoyer("jeton", "Titre", "Message", {"reservation_id": 42}) is True

    message = envoyer.call_args.args[0]
    assert message.token == "jeton"
    assert message.notification.title == "Titre"
    assert message.data == {"reservation_id": "42"}


@mock.patch("apps.notifications.fcm._application")
def test_fcm_jeton_desinscrit(_application):
    from firebase_admin import messaging

    erreur = messaging.UnregisteredError("jeton inconnu")
    with mock.patch("apps.notifications.fcm.messaging.send", side_effect=erreur):
        assert FcmPushSender().envoyer("jeton", "Titre", "Message", {}) is False


def test_fcm_choisi_quand_la_cle_firebase_est_fournie():
    from apps.notifications.fcm import _application

    with (
        mock.patch("apps.notifications.fcm.firebase_admin.get_app", side_effect=ValueError),
        mock.patch("apps.notifications.fcm.credentials.Certificate") as certificat,
        mock.patch("apps.notifications.fcm.firebase_admin.initialize_app") as initialiser,
    ):
        _application()

    certificat.assert_called_once()
    initialiser.assert_called_once()
