"""F-071 · Vérifier son adresse e-mail par code (`auth/inscription/verifier/`, `renvoyer-code/`)."""

import pytest
from django.core import mail
from freezegun import freeze_time

from apps.accounts.models import OtpCode, User
from apps.accounts.tests.aides_auth import (
    AMA,
    NOUVEAU_MOT_DE_PASSE,
    OUBLIE,
    REINITIALISER,
    RENVOYER,
    VERIFIER,
    autre_code,
    client_porteur,
    code_de,
    dernier_code,
    inscrire,
    poster,
)
from apps.accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def verifier(code: str, email: str = AMA):
    return poster(VERIFIER, {"email": email, "code": code})


def email_verifie() -> bool:
    return User.objects.get(email=AMA).email_verifie


def test_ca_071_1_bon_code_session_ouverte_puis_code_use():
    with freeze_time("2026-10-30 10:00:00"):
        inscrire()
        code = dernier_code()
    with freeze_time("2026-10-30 10:05:00"):
        reponse = verifier(code)
        moi = client_porteur(reponse.json()["reponse"]["access"]).get("/api/v1/moi/")
        rejoue = verifier(code)

    assert reponse.status_code == 200
    session = reponse.json()["reponse"]
    assert session["access"] and session["refresh"] and session["nouveau_compte"] is True
    assert session["utilisateur"]["email"] == AMA
    profil = moi.json()["reponse"]
    assert profil["email_verifie"] is True and profil["etat"]["acces"]["peut_rechercher"] is True
    # CA-003-4 et CA-004-2 : profil complet, CGU acceptées dès l'inscription
    assert "PROFIL_INCOMPLET" not in {a["code"] for a in profil["etat"]["alertes"]}
    assert profil["profil_complet"] is True and profil["cgu_acceptees"] is True
    assert rejoue.status_code == 400 and code_de(rejoue) == "CODE_OTP_INVALIDE"
    assert rejoue.json()["message"] == "Code invalide ou expiré."


def test_ca_071_2_cinq_codes_faux_epuisent_le_code_puis_nouveau_code():
    with freeze_time("2026-10-30 10:00:00"):
        inscrire()
        bon = dernier_code()
        for _ in range(5):
            assert code_de(verifier(autre_code(bon))) == "CODE_OTP_INVALIDE"
        assert code_de(verifier(bon)) == "CODE_OTP_INVALIDE"
    assert email_verifie() is False
    with freeze_time("2026-10-30 10:01:01"):
        assert poster(RENVOYER, {"email": AMA}).status_code == 200
        assert verifier(dernier_code()).status_code == 200


@pytest.mark.parametrize(("instant", "attendu"), [("10:09:59", 200), ("10:10:01", 400)])
def test_ca_071_3_code_valable_dix_minutes(instant, attendu):
    with freeze_time("2026-10-30 10:00:00"):
        inscrire()
    with freeze_time(f"2026-10-30 {instant}"):
        reponse = verifier(dernier_code())

    assert reponse.status_code == attendu
    assert email_verifie() is (attendu == 200)


def test_ca_071_4_delai_de_renvoi_puis_plafond_horaire(monkeypatch):
    codes = iter([111111, 222222, 333333, 444444, 555555])
    monkeypatch.setattr(
        "apps.accounts.services.codes_email.secrets.randbelow", lambda _: next(codes)
    )
    with freeze_time("2026-10-30 10:00:00"):
        inscrire()
        ancien = dernier_code()
    with freeze_time("2026-10-30 10:00:30"):
        trop_tot = poster(RENVOYER, {"email": AMA})
    assert trop_tot.status_code == 429 and code_de(trop_tot) == "TROP_DE_REQUETES"
    with freeze_time("2026-10-30 10:01:01"):
        assert poster(RENVOYER, {"email": AMA}).status_code == 200
        assert (ancien, dernier_code()) == ("111111", "222222")
        assert code_de(verifier(ancien)) == "CODE_OTP_INVALIDE"
        assert OtpCode.objects.filter(email=AMA, utilise=False).count() == 1
    # 3e, 4e (réinitialisation) et 5e envois : le plafond compte tous les objets
    with freeze_time("2026-10-30 10:02:02"):
        assert poster(RENVOYER, {"email": AMA}).status_code == 200
    with freeze_time("2026-10-30 10:03:03"):
        assert poster(OUBLIE, {"email": AMA}).status_code == 200
    with freeze_time("2026-10-30 10:04:04"):
        assert poster(RENVOYER, {"email": AMA}).status_code == 200
    with freeze_time("2026-10-30 10:05:05"):
        sixieme = poster(RENVOYER, {"email": AMA})
    assert sixieme.status_code == 429 and code_de(sixieme) == "TROP_DE_REQUETES"
    assert len(mail.outbox) == 5


def test_ca_071_6_un_code_de_verification_n_annule_pas_la_reinitialisation():
    with freeze_time("2026-10-30 09:58:00"):
        inscrire()
    with freeze_time("2026-10-30 10:00:00"):
        poster(OUBLIE, {"email": AMA})
        code_reinit = dernier_code()
    with freeze_time("2026-10-30 10:02:00"):
        assert poster(RENVOYER, {"email": AMA}).status_code == 200
    assert mail.outbox[-1].subject != mail.outbox[-2].subject
    assert OtpCode.objects.filter(objet="reinitialisation", utilise=False).count() == 1
    with freeze_time("2026-10-30 10:03:00"):
        reinit = poster(
            REINITIALISER,
            {"email": AMA, "code": code_reinit, "mot_de_passe": NOUVEAU_MOT_DE_PASSE},
        )
    assert reinit.status_code == 200


def test_ca_071_6_une_demande_de_reinitialisation_n_annule_pas_la_verification():
    with freeze_time("2026-10-30 10:00:00"):
        inscrire()
        code_verif = dernier_code()
    with freeze_time("2026-10-30 10:02:00"):
        assert poster(OUBLIE, {"email": AMA}).status_code == 200
    with freeze_time("2026-10-30 10:03:00"):
        assert verifier(code_verif).status_code == 200


def test_ca_071_6_plafond_commun_trois_verifications_deux_reinitialisations():
    with freeze_time("2026-10-30 10:00:00"):
        inscrire()  # 1re vérification
    for minute, route in [(2, OUBLIE), (4, RENVOYER), (6, OUBLIE), (8, RENVOYER)]:
        with freeze_time(f"2026-10-30 10:{minute:02d}:00"):
            assert poster(route, {"email": AMA}).status_code == 200
    for route in (OUBLIE, RENVOYER):
        with freeze_time("2026-10-30 10:10:00"):
            assert poster(route, {"email": AMA}).status_code == 429
    assert OtpCode.objects.filter(objet="verification_email").count() == 3
    assert OtpCode.objects.filter(objet="reinitialisation").count() == 2


def test_ca_071_7_meme_reponse_pour_adresse_inconnue_verifiee_ou_desactivee():
    with freeze_time("2026-10-30 10:00:00"):
        inscrire()
    UserFactory(email="verifie@exemple.tg")
    UserFactory(email="desactive@exemple.tg", email_verifie=False, is_active=False)
    mail.outbox.clear()
    with freeze_time("2026-10-30 10:01:01"):
        reponses = {
            email: poster(RENVOYER, {"email": email})
            for email in (AMA, "inconnu@exemple.tg", "verifie@exemple.tg", "desactive@exemple.tg")
        }

    corps = {email: (r.status_code, r.json()["message"]) for email, r in reponses.items()}
    assert len(set(corps.values())) == 1 and corps[AMA][0] == 200
    assert reponses["inconnu@exemple.tg"].json()["reponse"] == {
        "email": "inconnu@exemple.tg",
        "delai_renvoi_s": 60,
    }
    assert [m.to for m in mail.outbox] == [[AMA]]
    assert not User.objects.filter(email="inconnu@exemple.tg").exists()


@pytest.mark.parametrize("cas", ["inconnu", "verifie", "desactive"])
def test_code_refuse_pour_compte_inconnu_verifie_ou_desactive(cas):
    """Un code `verification_email` existe (ancienne route OTP) mais le compte n'est pas à
    vérifier : même 400 CODE_OTP_INVALIDE."""
    from apps.accounts import services

    email = f"{cas}@exemple.tg"
    if cas != "inconnu":
        UserFactory(email=email, email_verifie=cas == "verifie", is_active=cas == "verifie")
    services.demander_otp(email)

    reponse = verifier(dernier_code(), email=email)

    assert reponse.status_code == 400 and code_de(reponse) == "CODE_OTP_INVALIDE"


def test_code_mal_forme_donnees_invalides():
    reponse = verifier("12ab")

    assert reponse.status_code == 400 and code_de(reponse) == "DONNEES_INVALIDES"
    assert "code" in reponse.json()["reponse"]["erreurs"]
