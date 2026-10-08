import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kovoit.settings")

app = Celery("kovoit")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Tâches planifiées (celery beat)
app.conf.beat_schedule = {
    "cloture-automatique-des-reservations": {
        "task": "apps.reservations.tasks.cloturer_reservations",
        "schedule": 15 * 60,
    },
    "fin-des-suspensions": {
        "task": "apps.accounts.tasks.reactiver_suspensions",
        "schedule": 60 * 60,
    },
}
