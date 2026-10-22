from celery import shared_task

from apps.audit.services import purger_expires


@shared_task
def purger_journal_expire() -> int:
    """Tâche planifiée : rétention du journal d'audit (`audit_retention_jours`)."""
    return purger_expires()
