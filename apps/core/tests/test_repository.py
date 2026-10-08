"""Tests du BaseRepository, via le repository concret des utilisateurs."""

import uuid

import pytest
from freezegun import freeze_time

from apps.accounts.repository import user_repository
from apps.accounts.tests.factories import UserFactory
from apps.core.exceptions import RessourceIntrouvable

pytestmark = pytest.mark.django_db


def test_get_by_id_renvoie_l_instance(utilisateur):
    assert user_repository.get_by_id(utilisateur.id) == utilisateur


@pytest.mark.parametrize("identifiant", [uuid.uuid4(), "pas-un-uuid"])
def test_get_by_id_introuvable_leve_ressource_introuvable(identifiant):
    with pytest.raises(RessourceIntrouvable) as exc:
        user_repository.get_by_id(identifiant)

    assert exc.value.message == "Utilisateur introuvable."
    assert exc.value.http_status == 404


def test_get_or_none_et_exists(utilisateur):
    assert user_repository.get_or_none(email=utilisateur.email) == utilisateur
    assert user_repository.get_or_none(email="absent@exemple.tg") is None
    assert user_repository.exists(email=utilisateur.email)
    assert not user_repository.exists(email="absent@exemple.tg")


def test_update_modifie_les_champs_et_l_horodatage():
    with freeze_time("2026-10-01 08:00"):
        utilisateur = UserFactory()
    with freeze_time("2026-10-01 09:00"):
        user_repository.update(utilisateur, nom="Mensah")

    utilisateur.refresh_from_db()
    assert utilisateur.nom == "Mensah"
    assert utilisateur.modifie_le.hour - utilisateur.cree_le.hour == 1


def test_filter_renvoie_un_queryset(utilisateur):
    assert list(user_repository.filter(nom=utilisateur.nom)) == [utilisateur]
