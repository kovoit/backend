from celery import shared_task

from apps.portefeuille.services import verifier_paiements_en_attente
from apps.portefeuille.services.alertes import alerter_retraits_en_attente as _alerter


@shared_task
def verifier_paiements() -> int:
    """Tâche planifiée : confirme les recharges Mobile Money dont le callback s'est perdu."""
    return verifier_paiements_en_attente()


@shared_task
def alerter_retraits_en_attente() -> int:
    """Tâche quotidienne : prévient l'équipe Finance des retraits en attente depuis plus de 24 h."""
    return _alerter()
