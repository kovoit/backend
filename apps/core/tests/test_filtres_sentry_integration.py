"""Réglage réel de Sentry (initialiser_sentry) avec un transport factice : ni réseau ni DSN réel."""

import json
import logging

import pytest
import sentry_sdk
from sentry_sdk.transport import Transport

from kovoit.filtres_sentry import initialiser_sentry

ARGS = "('ama@exemple.tg', 'Code', 'Votre code : 123456')"
KWARGS = "{'lien': '/reinitialiser/MQ/jeton-secret/'}"
SECRETS = ("ama@exemple.tg", "123456", "jeton-secret")


class TransportFactice(Transport):
    evenements: list[dict] = []

    def capture_envelope(self, envelope) -> None:
        for element in envelope.items:
            if element.type == "event":
                self.evenements.append(element.payload.json)


@pytest.fixture
def sentry_actif():
    TransportFactice.evenements = []
    sentry_sdk.get_isolation_scope().clear_breadcrumbs()
    client = initialiser_sentry(
        "https://cle@o0.ingest.sentry.io/1", "test", 0.0, transport=TransportFactice
    )
    journaux = [logging.getLogger(n) for n in ("celery.worker.strategy", "celery.worker.autre")]
    niveaux = [j.level for j in journaux]
    for journal in journaux:
        journal.setLevel(logging.INFO)
    yield TransportFactice.evenements
    for journal, niveau in zip(journaux, niveaux, strict=True):
        journal.setLevel(niveau)
    client.close()
    sentry_sdk.get_global_scope().set_client(None)
    sentry_sdk.get_isolation_scope().clear_breadcrumbs()


def _recu(nom_journal: str) -> None:
    contexte = {"id": "x", "name": "envoyer_email_tache", "args": ARGS, "kwargs": KWARGS}
    logging.getLogger(nom_journal).info(
        "Task %(name)s[%(id)s] received", contexte, extra={"data": contexte}
    )


def test_evenement_reel_sans_email_ni_code(sentry_actif):
    _recu("celery.worker.strategy")  # ignoré
    _recu("celery.worker.autre")  # enregistré puis masqué par NOMS_MASQUES
    logging.getLogger("celery.worker.autre").error("consumer: Cannot connect to redis")
    sentry_sdk.flush()

    assert len(sentry_actif) == 1
    evenement = sentry_actif[0]
    fils = evenement["breadcrumbs"]["values"]
    assert [f["category"] for f in fils] == ["celery.worker.autre"]
    assert fils[0]["data"]["data"]["args"] == "[Filtered]"
    contenu = json.dumps(evenement, default=str)
    for secret in SECRETS:
        assert secret not in contenu, secret
    assert sentry_sdk.get_client().is_active()


def test_client_global_inactif_hors_fixture():
    assert not sentry_sdk.get_client().is_active()
