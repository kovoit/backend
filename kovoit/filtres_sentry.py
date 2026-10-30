"""Masquage des secrets avant tout envoi à Sentry (utilisé par reglages_supervision).

Le filtre par défaut du SDK ne reconnaît que des noms exacts anglais (`password`, `token`…) :
on y ajoute les noms français de l'API. Il s'applique au corps de la requête, aux extras,
aux fils d'Ariane et aux variables locales des cadres (désactivées par ailleurs). Les arguments
des tâches Celery (e-mail, code, lien de réinitialisation) sont positionnels : `args`/`kwargs`
sont masqués partout (fils d'Ariane `data.data.args` du journal « Task … received » compris),
ce journal est ignoré et `extra["celery-job"]` est vidé entièrement.
"""

from typing import Any

import sentry_sdk
from sentry_sdk.integrations.logging import ignore_logger
from sentry_sdk.scrubber import DEFAULT_DENYLIST, EventScrubber

# Journal « Task … received » du worker principal : porte args/kwargs en clair (Celery 5.5).
JOURNAUX_IGNORES = ("celery.worker.strategy",)

NOMS_MASQUES = [
    "mot_de_passe",
    "nouveau_mot_de_passe",
    "ancien_mot_de_passe",
    "password",
    "code",
    "otp",
    "refresh",
    "access",
    "token",
    "jeton",
    "jetons",
    "telephone",
    "email",
    "args",
    "kwargs",
]

ARGUMENTS_RETIRES = "[retiré]"


def creer_masqueur() -> EventScrubber:
    """Récursif : les secrets imbriqués (dict dans une variable locale, liste…) sont masqués."""
    return EventScrubber(denylist=DEFAULT_DENYLIST + NOMS_MASQUES, recursive=True)


def avant_envoi(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    tache = (event.get("extra") or {}).get("celery-job")
    if isinstance(tache, dict):
        for cle in ("args", "kwargs"):
            if cle in tache:
                tache[cle] = ARGUMENTS_RETIRES
    return event


def initialiser_sentry(
    dsn: str, environnement: str, taux_traces: float, **options: Any
) -> sentry_sdk.Client:
    """Réglage réel de reglages_supervision ; `options` sert aux tests (transport factice)."""
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    for nom in JOURNAUX_IGNORES:
        ignore_logger(nom)
    sentry_sdk.init(
        dsn=dsn,
        environment=environnement,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        send_default_pii=False,
        include_local_variables=False,
        event_scrubber=creer_masqueur(),
        before_send=avant_envoi,
        traces_sample_rate=taux_traces,
        **options,
    )
    return sentry_sdk.get_client()
