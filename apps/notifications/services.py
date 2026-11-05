"""Notifications : push (FCM) vers les appareils enregistrés, email (Gmail SMTP) en secours."""

import logging

from django.db import transaction
from django.utils import timezone
from kombu.exceptions import OperationalError

from apps.core.exceptions import RessourceIntrouvable
from apps.notifications.models import AppareilNotification
from apps.notifications.push import obtenir_push_sender
from apps.notifications.repository import appareil_repository, notification_repository
from apps.notifications.tasks import envoyer_email_tache, envoyer_push_tache

logger = logging.getLogger(__name__)


def _lancer(tache, *args) -> None:
    """Envoie la tâche à Celery ; sans broker joignable (dev sans Redis), l'exécute sur place.
    Seule l'indisponibilité du broker déclenche ce repli : l'échec d'une tâche exécutée
    en mode eager (SMTP en panne…) remonte, sans second essai."""
    try:
        tache.delay(*args)
    except OperationalError:
        logger.warning("Broker Celery indisponible : %s exécutée directement.", tache.name)
        tache(*args)


def envoyer_email(destinataire: str, sujet: str, message: str) -> None:
    """Envoi immédiat.
    À appeler hors transaction ; dans une transaction, passer par `notifier()`."""
    _lancer(envoyer_email_tache, destinataire, sujet, message)


def notifier(utilisateur, titre: str, message: str, donnees: dict | None = None) -> None:
    """Push vers les téléphones de l'utilisateur ; email si aucun téléphone n'est enregistré
    ou si le push n'est pas réellement envoyé (Firebase non configuré).
    La ligne est écrite dans la transaction de l'appelant (et disparaît avec elle) ;
    push et email ne partent qu'après sa validation (aussitôt hors transaction).
    Un envoi qui échoue après validation est journalisé, sans faire échouer la requête."""
    notification = notification_repository.create(
        utilisateur=utilisateur, titre=titre, message=message, donnees=donnees or {}
    )
    donnees = {**(donnees or {}), "notification_id": str(notification.id)}

    # Fonction nommée (pas de functools.partial) : robust=True journalise func.__qualname__.
    def diffuser() -> None:
        jetons = appareil_repository.jetons_de(utilisateur)
        if jetons:
            _lancer(envoyer_push_tache, jetons, titre, message, donnees, utilisateur.email)
        if not jetons or not obtenir_push_sender().envoi_reel:
            envoyer_email(utilisateur.email, f"Kovoit — {titre}", message)

    transaction.on_commit(diffuser, robust=True)


def mes_notifications(utilisateur):
    return notification_repository.de(utilisateur)


def nombre_non_lues(utilisateur) -> int:
    return notification_repository.compter_non_lues(utilisateur)


def marquer_lue(utilisateur, notification_id):
    notification = notification_repository.get_de(utilisateur, notification_id)
    if notification.lue_le is None:
        notification = notification_repository.update(notification, lue_le=timezone.now())
    return notification


def tout_marquer_lu(utilisateur) -> int:
    return notification_repository.marquer_toutes_lues(utilisateur, timezone.now())


def enregistrer_appareil(utilisateur, jeton: str, plateforme: str) -> AppareilNotification:
    return appareil_repository.enregistrer(utilisateur, jeton, plateforme)


def retirer_appareil(utilisateur, jeton: str) -> None:
    appareil = appareil_repository.get_or_none(utilisateur=utilisateur, jeton=jeton)
    if appareil is None:
        raise RessourceIntrouvable("Appareil introuvable.")
    appareil_repository.delete(appareil)
