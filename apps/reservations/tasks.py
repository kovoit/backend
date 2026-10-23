from celery import shared_task

from apps.reservations.services import cloturer_automatiquement, expirer_reservations


@shared_task
def cloturer_reservations() -> int:
    """Tâche planifiée : clôture automatique après `delai_confirmation_auto_h`."""
    return cloturer_automatiquement()


@shared_task
def expirer_reservations_en_suspens() -> int:
    """Tâche planifiée : aucune somme ne reste bloquée après le départ (voir expiration.py)."""
    return expirer_reservations()
