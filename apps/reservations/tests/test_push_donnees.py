"""Les push portent de quoi ouvrir le bon écran : réservation (passager) ou trajet (conducteur)."""

import pytest

from apps.notifications.push import FakePushSender
from apps.notifications.services import enregistrer_appareil

pytestmark = pytest.mark.django_db


def test_push_conducteur_ouvre_son_trajet(conducteur, passager, trajet):
    from conftest import demander

    enregistrer_appareil(conducteur, "jeton-conducteur", "android")
    reservation = demander(passager, trajet)

    envoi = next(e for e in FakePushSender.envoyes if e["jeton"] == "jeton-conducteur")
    assert (
        envoi["donnees"].items()
        >= {
            "reservation_id": str(reservation.id),
            "trajet_id": str(trajet.id),
            "destinataire": "conducteur",
        }.items()
    )
    assert envoi["donnees"]["notification_id"]


def test_push_passager_ouvre_sa_reservation(conducteur, passager, reservation):
    from apps.reservations import services

    enregistrer_appareil(passager, "jeton-passager", "android")
    services.accepter(conducteur, reservation.id)

    envoi = next(e for e in FakePushSender.envoyes if e["jeton"] == "jeton-passager")
    assert envoi["donnees"]["destinataire"] == "passager"
    assert envoi["donnees"]["reservation_id"] == str(reservation.id)
