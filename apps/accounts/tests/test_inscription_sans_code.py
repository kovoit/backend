"""Démo sans e-mail (`INSCRIPTION_SANS_CODE`) : compte vérifié dès l'inscription, aucun code
envoyé, connexion directe ; un compte resté non vérifié est validé à sa connexion."""

import pytest
from django.core import mail

from apps.accounts.models import OtpCode, User
from apps.accounts.tests.aides_auth import AMA, connecter, inscrire
from apps.accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def sans_code(settings):
    settings.INSCRIPTION_SANS_CODE = True


def test_par_defaut_le_compte_attend_son_code():
    inscrire()

    assert User.objects.get().email_verifie is False
    assert len(mail.outbox) == 1
    assert connecter(AMA).status_code == 403


def test_inscription_sans_code_puis_connexion_directe(sans_code):
    reponse = inscrire()

    assert reponse.status_code == 201
    assert User.objects.get().email_verifie is True
    assert mail.outbox == [] and not OtpCode.objects.exists()
    connexion = connecter(AMA)
    assert connexion.status_code == 200
    assert connexion.json()["reponse"]["access"]


def test_compte_reste_non_verifie_valide_a_la_connexion(sans_code):
    compte = UserFactory(email="bloque@exemple.tg", email_verifie=False)
    compte.set_password("Kovoit-Demo-2026")
    compte.save()

    reponse = connecter("bloque@exemple.tg", "Kovoit-Demo-2026")

    assert reponse.status_code == 200
    compte.refresh_from_db()
    assert compte.email_verifie is True
    assert mail.outbox == []
