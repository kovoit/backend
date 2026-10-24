from celery import shared_task
from django.core.mail import send_mail

from apps.notifications.push import obtenir_push_sender
from apps.notifications.repository import appareil_repository


@shared_task
def envoyer_email_tache(destinataire: str, sujet: str, message: str) -> None:
    send_mail(sujet, message, None, [destinataire])


@shared_task
def envoyer_push_tache(
    jetons: list[str], titre: str, message: str, donnees: dict, email_secours: str
) -> int:
    """Envoie le push à chaque appareil, oublie les jetons périmés et se rabat sur l'email
    si aucun téléphone n'a pu être joint. Renvoie le nombre d'appareils atteints."""
    sender = obtenir_push_sender()
    atteints = 0
    for jeton in jetons:
        if sender.envoyer(jeton, titre, message, donnees):
            atteints += 1
        else:
            appareil_repository.supprimer_jeton(jeton)
    if atteints == 0:
        send_mail(f"Kovoit — {titre}", message, None, [email_secours])
    return atteints


@shared_task
def purger_notifications_anciennes() -> int:
    """Tâche quotidienne : supprime les notifications plus vieilles que la durée de conservation."""
    from datetime import timedelta

    from django.utils import timezone

    from apps.notifications.repository import notification_repository
    from apps.parametres.services import get_param

    limite = timezone.now() - timedelta(days=get_param("conservation_notifications_j"))
    return notification_repository.supprimer_anterieures(limite)
