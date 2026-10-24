"""Suivi des erreurs (Sentry), actif seulement si SENTRY_DSN est renseigné (importé par settings).

Aucune donnée personnelle n'est envoyée : send_default_pii=False (ni email, ni IP, ni cookies,
ni corps de requête). Les traces de performance sont désactivées par défaut.
"""

import environ

env = environ.Env()

SENTRY_DSN = env("SENTRY_DSN", default="")

if SENTRY_DSN:  # pragma: no cover — dépend de l'environnement du serveur
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=env("SENTRY_ENVIRONNEMENT", default="production"),
        integrations=[DjangoIntegration(), CeleryIntegration()],
        send_default_pii=False,
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),
    )
