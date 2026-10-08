from celery import shared_task

from apps.reservations.services import cloturer_automatiquement


@shared_task
def cloturer_reservations() -> int:
    """Tâche planifiée : clôture automatique après `delai_confirmation_auto_h`."""
    return cloturer_automatiquement()
