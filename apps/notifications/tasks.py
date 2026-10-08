from celery import shared_task
from django.core.mail import send_mail

from apps.notifications.push import obtenir_push_sender


@shared_task
def envoyer_email_tache(destinataire: str, sujet: str, message: str) -> None:
    send_mail(sujet, message, None, [destinataire])


@shared_task
def envoyer_push_tache(jetons: list[str], titre: str, message: str, donnees: dict) -> None:
    sender = obtenir_push_sender()
    for jeton in jetons:
        sender.envoyer(jeton, titre, message, donnees)
