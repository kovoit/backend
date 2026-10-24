"""Référentiel des lieux dans le Django admin : coordonnées bornées à Lomé, vérification."""

import pytest

from apps.lieux.admin import LieuForm
from apps.lieux.models import Lieu

pytestmark = pytest.mark.django_db


def donnees(**changes):
    return {"libelle": "Carrefour test", "quartier": "Bè", "type": "carrefour", "lat": 6.14,
            "lng": 1.24, "actif": True, **changes}  # fmt: skip


def test_coordonnees_de_lome_acceptees():
    assert LieuForm(data=donnees()).is_valid()


@pytest.mark.parametrize(("champ", "valeur"), [("lat", 1.24), ("lng", 6.14), ("lng", 0.20)])
def test_coordonnees_hors_de_lome_refusees(champ, valeur):
    form = LieuForm(data=donnees(**{champ: valeur}))

    assert not form.is_valid()
    assert "Hors de Lomé" in form.errors[champ][0]


def test_action_marquer_verifie(admin_client_django):
    lieu = Lieu.objects.first()
    reponse = admin_client_django.post(
        "/django-admin/lieux/lieu/",
        {"action": "marquer_verifie", "_selected_action": [lieu.pk]},
        follow=True,
    )

    assert reponse.status_code == 200
    lieu.refresh_from_db()
    assert lieu.verifie_le is not None
    assert "Voir sur la carte" in reponse.content.decode()


@pytest.fixture
def admin_client_django(client, admin):
    admin.is_superuser = True
    admin.save()
    client.force_login(admin)
    return client
