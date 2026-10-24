from celery import shared_task

from apps.core.supervision import battre


@shared_task
def battement_supervision() -> None:
    """Battement de cœur : /api/v1/sante/ signale un planificateur arrêté."""
    battre()
