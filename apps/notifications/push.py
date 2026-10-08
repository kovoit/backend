"""Envoi de notifications push. Le fournisseur est choisi par `NOTIFICATIONS_PUSH_SENDER`."""

import logging

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class PushSender:
    def envoyer(self, jeton: str, titre: str, message: str, donnees: dict) -> None:
        raise NotImplementedError


class JournalPushSender(PushSender):
    """Fournisseur par défaut : écrit la notification dans les logs (FCM à brancher plus tard)."""

    def envoyer(self, jeton: str, titre: str, message: str, donnees: dict) -> None:
        logger.info("Push [%s…] %s : %s %s", jeton[:12], titre, message, donnees)


class FakePushSender(PushSender):
    """Utilisé en test : garde les notifications envoyées en mémoire."""

    envoyes: list[dict] = []

    def envoyer(self, jeton: str, titre: str, message: str, donnees: dict) -> None:
        self.envoyes.append({"jeton": jeton, "titre": titre, "message": message})


def obtenir_push_sender() -> PushSender:
    return import_string(settings.NOTIFICATIONS_PUSH_SENDER)()
