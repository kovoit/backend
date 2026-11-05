"""F-073 · Réinitialiser son mot de passe par code e-mail (`auth/mot-de-passe/…`)."""

import pytest
from django.core import mail
from freezegun import freeze_time

from apps.accounts.models import OtpCode, User
from apps.accounts.tests.aides_auth import (
    AMA,
    MOT_DE_PASSE,
    NOUVEAU_MOT_DE_PASSE,
    OUBLIE,
    RAFRAICHIR,
    REINITIALISER,
    avec_mot_de_passe,
    code_de,
    connecter,
    dernier_code,
    inscrire,
    poster,
)
from apps.accounts.tests.factories import AdminFactory, UserFactory

pytestmark = pytest.mark.django_db
KOFI = "kofi.agbeko@exemple.tg"


@pytest.fixture
def kofi():
    return avec_mot_de_passe(UserFactory(email=KOFI, prenom="Kofi", nom="Agbeko"))


def demander(email: str = KOFI):
    return poster(OUBLIE, {"email": email})


def reinitialiser(code: str, mot_de_passe: str = NOUVEAU_MOT_DE_PASSE, email: str = KOFI):
    return poster(REINITIALISER, {"email": email, "code": code, "mot_de_passe": mot_de_passe})


def test_ca_073_1_meme_reponse_pour_compte_inconnu_admin_ou_desactive(kofi):
    avec_mot_de_passe(AdminFactory(email="admin@kovoit.tg"))
    UserFactory(email="desactive@exemple.tg", is_active=False)
    adresses = (KOFI, "inconnu@exemple.tg", "admin@kovoit.tg", "desactive@exemple.tg")

    reponses = {email: demander(email) for email in adresses}

    vues = {(r.status_code, r.json()["message"]) for r in reponses.values()}
    assert len(vues) == 1 and reponses[KOFI].status_code == 200
    assert reponses[KOFI].json()["reponse"] == {"email": KOFI, "delai_renvoi_s": 60}
    assert [m.to for m in mail.outbox] == [[KOFI]]
    assert list(OtpCode.objects.values_list("email", "objet")) == [(KOFI, "reinitialisation")]


def test_ca_073_1_delai_de_renvoi_pour_un_compte_eligible(kofi):
    with freeze_time("2026-10-30 10:00:00"):
        demander()
    with freeze_time("2026-10-30 10:00:30"):
        reponse = demander()

    assert reponse.status_code == 429 and code_de(reponse) == "TROP_DE_REQUETES"


def test_ca_073_2_nouveau_mot_de_passe_sessions_revoquees_code_unique(kofi):
    r1 = connecter(KOFI).json()["reponse"]["refresh"]
    demander()
    code = dernier_code()

    reponse = reinitialiser(code)

    assert reponse.status_code == 200
    assert reponse.json()["reponse"] is None
    assert connecter(KOFI).status_code == 401
    assert connecter(KOFI, NOUVEAU_MOT_DE_PASSE).status_code == 200
    rafraichi = poster(RAFRAICHIR, {"refresh": r1})
    assert rafraichi.status_code == 401 and code_de(rafraichi) == "SESSION_EXPIREE"
    rejoue = reinitialiser(code, "Encore-Kovoit-28")
    assert rejoue.status_code == 400 and code_de(rejoue) == "CODE_OTP_INVALIDE"


def test_ca_073_3_mot_de_passe_faible_avant_le_code_qui_reste_valable(kofi):
    demander()
    code = dernier_code()

    faible = reinitialiser(code, "12345678")

    assert faible.status_code == 400 and code_de(faible) == "MOT_DE_PASSE_FAIBLE"
    assert faible.json()["reponse"]["erreurs"]["mot_de_passe"]
    assert "12345678" not in faible.content.decode()  # T9 : jamais renvoyé
    kofi.refresh_from_db()
    assert kofi.check_password(MOT_DE_PASSE)
    assert OtpCode.objects.get().essais == 0
    assert reinitialiser(code).status_code == 200


def test_mot_de_passe_trop_proche_du_nom_du_compte(kofi):
    demander()

    assert code_de(reinitialiser(dernier_code(), "Agbeko2026")) == "MOT_DE_PASSE_FAIBLE"


def test_ca_073_5_compte_sans_mot_de_passe_fixe_son_premier_mot_de_passe():
    demo = UserFactory(email="demo@kovoit.tg")
    demo.set_unusable_password()
    demo.save()
    demander("demo@kovoit.tg")

    reponse = reinitialiser(dernier_code(), MOT_DE_PASSE, email="demo@kovoit.tg")

    assert reponse.status_code == 200
    assert connecter("demo@kovoit.tg").status_code == 200


def test_ca_073_6_reinitialisation_verifie_l_adresse():
    with freeze_time("2026-10-30 10:00:00"):
        inscrire()
    with freeze_time("2026-10-30 10:02:00"):
        demander(AMA)
        assert reinitialiser(dernier_code(), email=AMA).status_code == 200

    assert User.objects.get(email=AMA).email_verifie is True
    assert connecter(AMA, NOUVEAU_MOT_DE_PASSE).status_code == 200


@pytest.mark.parametrize("cas", ["inconnu", "admin", "desactive"])
def test_code_invalide_pour_compte_non_eligible(cas):
    email = f"{cas}@exemple.tg"
    if cas == "admin":
        AdminFactory(email=email)
    elif cas == "desactive":
        UserFactory(email=email, is_active=False)

    reponse = reinitialiser("123456", email=email)

    assert reponse.status_code == 400 and code_de(reponse) == "CODE_OTP_INVALIDE"
    # Mot de passe faible : même refus qu'un compte existant (contrôlé avant le code)
    assert code_de(reinitialiser("123456", "12345678", email=email)) == "MOT_DE_PASSE_FAIBLE"


def test_un_code_de_verification_ne_reinitialise_pas(kofi):
    from apps.accounts import services

    services.demander_otp(KOFI)  # code `verification_email` (ancienne route)

    assert code_de(reinitialiser(dernier_code())) == "CODE_OTP_INVALIDE"


def test_un_code_de_reinitialisation_n_ouvre_pas_de_session_par_l_otp(kofi):
    demander()

    reponse = poster("/api/v1/auth/otp/verifier/", {"email": KOFI, "code": dernier_code()})

    assert reponse.status_code == 400 and code_de(reponse) == "CODE_OTP_INVALIDE"


def test_reinitialisation_journalisee_sans_secret(kofi):
    from apps.audit.models import EvenementAudit

    demander()
    code = dernier_code()
    reinitialiser(code)

    actions = set(EvenementAudit.objects.values_list("action", flat=True))
    assert {"session.demander_reinitialisation", "session.reinitialiser_mot_de_passe"} <= actions
    # Détails seulement : un code à 6 chiffres peut apparaître par hasard dans un UUID ou une date
    details = str(list(EvenementAudit.objects.values_list("details", "changements")))
    assert code not in details
    assert NOUVEAU_MOT_DE_PASSE not in str(list(EvenementAudit.objects.values()))
