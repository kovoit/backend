"""Un passager déclaré absent : le conducteur peut le noter, pas l'inverse."""

from datetime import timedelta

import pytest
from freezegun import freeze_time

from apps.confiance import services
from apps.core.exceptions import Conflit
from apps.reservations import services as reservations

pytestmark = pytest.mark.django_db


@pytest.fixture
def reservation_absente(conducteur, reservation_acceptee):
    with freeze_time(reservation_acceptee.trajet.depart_le + timedelta(minutes=15)):
        return reservations.declarer_absent(conducteur, reservation_acceptee.id, 6.17, 1.17)


def test_le_conducteur_note_un_passager_absent(conducteur, passager, reservation_absente):
    note = services.noter(conducteur, reservation_absente.id, 1, "Absent au rendez-vous")

    assert (note.auteur_id, note.cible_id, note.note) == (conducteur.id, passager.id, 1)


def test_le_passager_absent_ne_note_pas_le_conducteur(passager, reservation_absente):
    with pytest.raises(Conflit) as exc:
        services.noter(passager, reservation_absente.id, 5)

    assert exc.value.code == "NOTE_PREMATUREE"
