"""F-070 · Créer son compte (`POST /auth/inscription/`) ; CGU à l'inscription (F-004)."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from freezegun import freeze_time

from apps.accounts import services
from apps.accounts.models import OtpCode, User
from apps.accounts.repository import user_repository
from apps.accounts.tests.aides_auth import (
    AMA,
    INSCRIPTION,
    MOT_DE_PASSE,
    champs_inscription,
    code_de,
    dernier_code,
    inscrire,
    poster,
)
from apps.accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_ca_070_1_compte_cree_non_verifie_et_code_envoye_sans_jeton():
    reponse = inscrire()

    assert reponse.status_code == 201
    corps = reponse.json()
    assert corps["statut"] == "success"
    assert corps["reponse"] == {"email": AMA, "delai_renvoi_s": 60}
    assert "access" not in reponse.content.decode() and "refresh" not in reponse.content.decode()
    compte = User.objects.get()
    assert compte.email == AMA and compte.email_verifie is False
    assert compte.telephone == "+22890112233"
    assert (compte.prenom, compte.nom) == ("Ama", "Mensah")
    assert compte.check_password(MOT_DE_PASSE)
    assert len(mail.outbox) == 1 and mail.outbox[0].to == [AMA]
    code = dernier_code()
    otp = OtpCode.objects.get()
    assert otp.objet == "verification_email" and otp.email == AMA
    assert all(code not in str(valeur) for valeur in vars(otp).values())


@pytest.mark.parametrize("verifie", [True, False])
def test_ca_070_2_adresse_deja_inscrite_409_sans_rien_changer(verifie):
    existant = UserFactory(email=AMA, email_verifie=verifie, telephone="+22890112233")
    avant = User.objects.values().get(pk=existant.pk)

    reponse = inscrire(email="AMA.MENSAH@exemple.tg")

    assert reponse.status_code == 409
    assert code_de(reponse) == "EMAIL_DEJA_UTILISE"
    assert reponse.json()["reponse"]["erreurs"]["email"]
    assert User.objects.count() == 1
    assert User.objects.values().get(pk=existant.pk) == avant
    assert mail.outbox == []
    # Même téléphone, autre adresse : le téléphone n'est pas unique (D-66)
    assert inscrire(email="ama.autre@exemple.tg").status_code == 201


def test_inscriptions_simultanees_de_la_meme_adresse_409_jamais_500(monkeypatch):
    """Les deux requêtes passent le contrôle d'existence ; la base refuse la seconde."""
    assert inscrire().status_code == 201
    monkeypatch.setattr(user_repository, "email_existe", lambda email: False)

    reponse = inscrire()

    assert reponse.status_code == 409
    assert code_de(reponse) == "EMAIL_DEJA_UTILISE"
    assert User.objects.count() == 1 and len(mail.outbox) == 1


@pytest.mark.parametrize("mot_de_passe", ["12345678", "password", "Lome26"])
def test_ca_070_3_mot_de_passe_faible(mot_de_passe):
    reponse = inscrire(mot_de_passe=mot_de_passe)

    assert reponse.status_code == 400
    assert code_de(reponse) == "MOT_DE_PASSE_FAIBLE"
    assert reponse.json()["reponse"]["erreurs"]["mot_de_passe"]
    assert not User.objects.exists() and mail.outbox == []


def test_ca_070_6_mot_de_passe_trop_proche_du_nom_absent_de_l_email():
    """Le nom « Mensah » n'est pas dans l'e-mail : seul le validateur sur `nom` refuse."""
    reponse = inscrire(email="ama.k@exemple.tg", mot_de_passe="Mensah1990")

    assert reponse.status_code == 400
    assert code_de(reponse) == "MOT_DE_PASSE_FAIBLE"
    assert reponse.json()["reponse"]["erreurs"]["mot_de_passe"]
    assert not User.objects.exists()
    assert inscrire(email="ama.k@exemple.tg").status_code == 201


def test_mot_de_passe_trop_proche_du_prenom():
    reponse = inscrire(prenom="Kossiwavi", email="k@exemple.tg", mot_de_passe="Kossiwavi7")

    assert code_de(reponse) == "MOT_DE_PASSE_FAIBLE"


def test_ca_070_4_telephone_invalide():
    reponse = inscrire(telephone="12345")

    assert reponse.status_code == 400
    assert code_de(reponse) == "TELEPHONE_INVALIDE"
    assert reponse.json()["reponse"]["erreurs"]["telephone"]
    assert not User.objects.exists()


@pytest.mark.parametrize("champ", ["prenom", "nom", "telephone", "email", "mot_de_passe"])
def test_ca_070_4_champ_absent_ou_vide(champ):
    sans_champ = champs_inscription()
    sans_champ.pop(champ)
    for donnees in (sans_champ, champs_inscription(**{champ: ""})):
        reponse = poster(INSCRIPTION, donnees)
        assert reponse.status_code == 400
        assert code_de(reponse) == "DONNEES_INVALIDES"
        assert champ in reponse.json()["reponse"]["erreurs"]
    assert not User.objects.exists()


@pytest.mark.parametrize("email", ["ama.mensah", "ama@", "ama mensah@exemple.tg"])
def test_email_mal_forme(email):
    reponse = inscrire(email=email)

    assert reponse.status_code == 400
    assert code_de(reponse) == "DONNEES_INVALIDES"
    assert "email" in reponse.json()["reponse"]["erreurs"]


def test_donnees_invalides_avant_telephone_et_mot_de_passe():
    """Ordre du contrat : champs, puis téléphone, puis mot de passe, puis adresse libre."""
    UserFactory(email=AMA)

    assert code_de(inscrire(nom="", telephone="12345", mot_de_passe="1")) == "DONNEES_INVALIDES"
    assert code_de(inscrire(telephone="12345", mot_de_passe="12345678")) == "TELEPHONE_INVALIDE"
    assert code_de(inscrire(mot_de_passe="12345678")) == "MOT_DE_PASSE_FAIBLE"


@pytest.mark.parametrize("cgu", [False, "absent"])
def test_ca_004_2_sans_acceptation_des_cgu(cgu):
    champs = champs_inscription(cgu_acceptees=cgu)
    if cgu == "absent":
        champs.pop("cgu_acceptees")

    reponse = poster(INSCRIPTION, champs)

    assert reponse.status_code == 400
    assert code_de(reponse) == "DONNEES_INVALIDES"
    assert "cgu_acceptees" in reponse.json()["reponse"]["erreurs"]
    assert not User.objects.exists() and mail.outbox == []


def test_ca_004_3_version_et_date_des_cgu_enregistrees(monkeypatch, client_de):
    with freeze_time("2026-10-30 10:00:00"):
        inscrire()
    compte = User.objects.get()

    assert compte.cgu_version == "2026-10-24"
    assert compte.cgu_acceptees_le == datetime(2026, 10, 30, 10, tzinfo=ZoneInfo("Africa/Lome"))
    compte.email_verifie = True  # vérification : voir test_inscription_verification.py
    compte.save()
    assert client_de(compte).get("/api/v1/moi/").json()["reponse"]["cgu_acceptees"] is True
    monkeypatch.setattr("apps.accounts.cgu.CGU_VERSION", "2026-12-01")
    assert client_de(compte).get("/api/v1/moi/").json()["reponse"]["cgu_acceptees"] is False


def test_service_inscrire_journalise_la_creation():
    from apps.audit.models import EvenementAudit

    services.inscrire(
        prenom="Ama", nom="Mensah", email=AMA, telephone="90112233", mot_de_passe=MOT_DE_PASSE
    )

    assert EvenementAudit.objects.filter(action="compte.creer").count() == 1
