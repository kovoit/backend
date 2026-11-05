#!/bin/sh
# Processus lancé par l'image, choisi par la variable PROCESSUS (une ressource Coolify par valeur) :
# web (défaut) = API gunicorn, worker = tâches Celery (e-mails, push), beat = planificateur Celery.
set -e
case "${PROCESSUS:-web}" in
  web) exec gunicorn kovoit.wsgi:application --bind 0.0.0.0:8000 --workers 3 ;;
  worker) exec celery -A kovoit worker -l info ;;
  beat) exec celery -A kovoit beat -l info --schedule /tmp/celerybeat-schedule ;;
  *) echo "PROCESSUS inconnu : $PROCESSUS (web, worker ou beat)" >&2; exit 1 ;;
esac
