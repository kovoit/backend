"""Une adresse de plus de 254 caractères (taille de la colonne) est refusée en 400, pas en 500."""

import pytest

from apps.accounts.models import User
from apps.accounts.tests.aides_auth import (
    CONNEXION,
    INSCRIPTION,
    MOT_DE_PASSE,
    OUBLIE,
    REINITIALISER,
    RENVOYER,
    VERIFIER,
    champs_inscription,
    code_de,
    poster,
)

pytestmark = pytest.mark.django_db

EMAIL_TROP_LONG = "a" * 64 + "@" + ".".join(["b" * 60] * 3) + ".exemple.tg"
OTP_DEMANDER = "/api/v1/auth/otp/demander/"


def _refuse(reponse) -> None:
    assert reponse.status_code == 400
    assert code_de(reponse) == "DONNEES_INVALIDES"
    assert "email" in reponse.json()["reponse"]["erreurs"]


def test_inscription_email_de_255_caracteres_ou_plus_400():
    assert len(EMAIL_TROP_LONG) >= 255

    _refuse(poster(INSCRIPTION, champs_inscription(email=EMAIL_TROP_LONG)))
    assert not User.objects.exists()


def test_otp_demander_email_trop_long_400():
    _refuse(poster(OTP_DEMANDER, {"email": EMAIL_TROP_LONG}))


@pytest.mark.parametrize(
    ("chemin", "autres"),
    [
        (VERIFIER, {"code": "123456"}),
        (RENVOYER, {}),
        (CONNEXION, {"mot_de_passe": MOT_DE_PASSE}),
        (OUBLIE, {}),
        (REINITIALISER, {"code": "123456", "mot_de_passe": MOT_DE_PASSE}),
    ],
)
def test_autres_routes_auth_email_trop_long_400(chemin, autres):
    _refuse(poster(chemin, {"email": EMAIL_TROP_LONG} | autres))
