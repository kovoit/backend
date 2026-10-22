from celery import shared_task

from apps.portefeuille.services import verifier_paiements_en_attente


@shared_task
def verifier_paiements() -> int:
    """Tâche planifiée : confirme les recharges Mobile Money dont le callback s'est perdu."""
    return verifier_paiements_en_attente()
