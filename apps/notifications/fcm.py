"""Firebase Cloud Messaging. Activé quand `FIREBASE_CREDENTIALS` pointe vers la clé de
compte de service (fichier JSON téléchargé depuis la console Firebase, jamais commité)."""

import firebase_admin
from django.conf import settings
from firebase_admin import credentials, messaging

from apps.notifications.push import PushSender


def _application() -> firebase_admin.App:
    try:
        return firebase_admin.get_app()
    except ValueError:  # pas encore initialisée dans ce processus
        return firebase_admin.initialize_app(credentials.Certificate(settings.FIREBASE_CREDENTIALS))


class FcmPushSender(PushSender):
    envoi_reel = True

    def envoyer(self, jeton: str, titre: str, message: str, donnees: dict) -> bool:
        notification = messaging.Message(
            token=jeton,
            notification=messaging.Notification(title=titre, body=message),
            # FCM n'accepte que des chaînes dans `data`
            data={cle: str(valeur) for cle, valeur in donnees.items()},
        )
        try:
            messaging.send(notification, app=_application())
        except (messaging.UnregisteredError, messaging.SenderIdMismatchError):
            return False
        return True
