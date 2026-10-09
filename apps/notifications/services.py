"""Notifications : push (FCM) vers les appareils enregistrés, email (Gmail SMTP) en secours."""

import logging

from apps.core.exceptions import RessourceIntrouvable
from apps.notifications.models import AppareilNotification
from apps.notifications.push import obtenir_push_sender
from apps.notifications.repository import appareil_repository
from apps.notifications.tasks import envoyer_email_tache, envoyer_push_tache

logger = logging.getLogger(__name__)


def _lancer(tache, *args) -> None:
    """Envoie la tâche à Celery ; sans broker joignable (dev sans Redis), l'exécute sur place."""
    try:
        tache.delay(*args)
    except Exception:  # noqa: BLE001 — broker indisponible
        logger.warning("Broker Celery indisponible : %s exécutée directement.", tache.name)
        tache(*args)


def envoyer_email(destinataire: str, sujet: str, message: str) -> None:
    _lancer(envoyer_email_tache, destinataire, sujet, message)


def notifier(utilisateur, titre: str, message: str, donnees: dict | None = None) -> None:
    """Push vers les téléphones de l'utilisateur ; email si aucun téléphone n'est enregistré
    ou si le push n'est pas réellement envoyé (Firebase non configuré)."""
    jetons = appareil_repository.jetons_de(utilisateur)
    if jetons:
        _lancer(envoyer_push_tache, jetons, titre, message, donnees or {}, utilisateur.email)
    if not jetons or not obtenir_push_sender().envoi_reel:
        envoyer_email(utilisateur.email, f"Kovoit — {titre}", message)


def enregistrer_appareil(utilisateur, jeton: str, plateforme: str) -> AppareilNotification:
    return appareil_repository.enregistrer(utilisateur, jeton, plateforme)


def retirer_appareil(utilisateur, jeton: str) -> None:
    appareil = appareil_repository.get_or_none(utilisateur=utilisateur, jeton=jeton)
    if appareil is None:
        raise RessourceIntrouvable("Appareil introuvable.")
    appareil_repository.delete(appareil)
