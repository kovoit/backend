"""Suivi des erreurs (Sentry), actif seulement si SENTRY_DSN est renseigné (importé par settings).

Aucune donnée personnelle ni secret n'est envoyé : send_default_pii=False (ni IP, ni cookies),
pas de variables locales, champs sensibles masqués (corps, extras, fils d'Ariane) et arguments
des tâches Celery retirés, journal « Task … received » ignoré (kovoit/filtres_sentry.py).
Traces de performance désactivées par défaut.
"""

import environ

env = environ.Env()

SENTRY_DSN = env("SENTRY_DSN", default="")

if SENTRY_DSN:  # pragma: no cover — dépend de l'environnement du serveur
    from kovoit.filtres_sentry import initialiser_sentry

    initialiser_sentry(
        SENTRY_DSN,
        environnement=env("SENTRY_ENVIRONNEMENT", default="production"),
        taux_traces=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),
    )
