from celery import shared_task

from apps.accounts.services import reactiver_suspensions_expirees


@shared_task
def reactiver_suspensions() -> int:
    """Tâche planifiée : réactive les comptes dont la suspension est terminée."""
    return reactiver_suspensions_expirees()
