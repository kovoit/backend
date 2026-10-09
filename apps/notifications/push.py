"""Envoi de notifications push. Le fournisseur est choisi par `NOTIFICATIONS_PUSH_SENDER`.

Un fournisseur dont `envoi_reel` vaut False n'atteint pas le téléphone : la notification
part alors aussi par email, pour qu'aucune information ne soit perdue.
"""

import logging

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class PushSender:
    envoi_reel = True

    def envoyer(self, jeton: str, titre: str, message: str, donnees: dict) -> bool:
        """Renvoie False si le jeton n'est plus valide (application désinstallée…)."""
        raise NotImplementedError


class JournalPushSender(PushSender):
    """Par défaut, tant que Firebase n'est pas configuré : écrit dans les logs seulement."""

    envoi_reel = False

    def envoyer(self, jeton: str, titre: str, message: str, donnees: dict) -> bool:
        logger.info("Push [%s…] %s : %s %s", jeton[:12], titre, message, donnees)
        return True


class FakePushSender(PushSender):
    """Utilisé en test : garde les notifications envoyées en mémoire."""

    envoyes: list[dict] = []
    jetons_invalides: set[str] = set()

    def envoyer(self, jeton: str, titre: str, message: str, donnees: dict) -> bool:
        if jeton in self.jetons_invalides:
            return False
        self.envoyes.append({"jeton": jeton, "titre": titre, "message": message})
        return True


def obtenir_push_sender() -> PushSender:
    return import_string(settings.NOTIFICATIONS_PUSH_SENDER)()
