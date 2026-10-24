import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kovoit.settings")

app = Celery("kovoit")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Tâches planifiées (celery beat)
app.conf.beat_schedule = {
    "battement-de-supervision": {
        "task": "apps.core.tasks.battement_supervision",
        "schedule": 5 * 60,
    },
    "alerte-retraits-en-attente": {
        "task": "apps.portefeuille.tasks.alerter_retraits_en_attente",
        "schedule": 24 * 60 * 60,
    },
    "cloture-automatique-des-reservations": {
        "task": "apps.reservations.tasks.cloturer_reservations",
        "schedule": 15 * 60,
    },
    "expiration-des-reservations-en-suspens": {
        "task": "apps.reservations.tasks.expirer_reservations_en_suspens",
        "schedule": 15 * 60,
    },
    "fin-des-suspensions": {
        "task": "apps.accounts.tasks.reactiver_suspensions",
        "schedule": 60 * 60,
    },
    "verification-des-paiements-mobile-money": {
        "task": "apps.portefeuille.tasks.verifier_paiements",
        "schedule": 2 * 60,
    },
    "retention-du-journal-d-audit": {
        "task": "apps.audit.tasks.purger_journal_expire",
        "schedule": 24 * 60 * 60,
    },
}
