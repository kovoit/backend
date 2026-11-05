"""F-072 · Se connecter à l'application par e-mail et mot de passe (`POST /auth/connexion/`)."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from django.conf import settings
from django.core import mail
from freezegun import freeze_time
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.accounts.models import OtpCode
from apps.accounts.tests.aides_auth import (
    AMA,
    MOT_DE_PASSE,
    avec_mot_de_passe,
    client_porteur,
    code_de,
    connecter,
    inscrire,
)
from apps.accounts.tests.factories import AdminFactory, UserFactory

pytestmark = pytest.mark.django_db
KOFI = "kofi.agbeko@exemple.tg"


@pytest.fixture
def kofi():
    return avec_mot_de_passe(UserFactory(email=KOFI, prenom="Kofi", nom="Agbeko"))


def refus(reponse) -> tuple[int, dict]:
    return reponse.status_code, reponse.json()


def test_ca_072_1_casse_de_l_email_ignoree_et_401_identiques(kofi):
    reponse = connecter("Kofi.Agbeko@exemple.tg")
    mauvais = connecter(KOFI, "lome-kovoit-26")
    inconnu = connecter("inconnu@exemple.tg")

    assert reponse.status_code == 200
    session = reponse.json()["reponse"]
    assert session["access"] and session["refresh"] and session["nouveau_compte"] is False
    assert session["utilisateur"]["email"] == KOFI
    assert refus(mauvais) == refus(inconnu)
    assert mauvais.status_code == 401 and code_de(mauvais) == "IDENTIFIANTS_INVALIDES"
    assert mauvais.json()["message"] == "Email ou mot de passe incorrect."


def test_ca_072_2_email_non_verifie_403_et_code_hors_delai_seulement():
    with freeze_time("2026-10-30 10:00:00"):
        inscrire()
    with freeze_time("2026-10-30 10:05:00"):
        premiere = connecter(AMA)
    with freeze_time("2026-10-30 10:05:30"):
        seconde = connecter(AMA)
        mauvais = connecter(AMA, "Mauvais-Mot-26")
        inconnu = connecter("inconnu@exemple.tg")

    assert premiere.status_code == 403 and code_de(premiere) == "EMAIL_NON_VERIFIE"
    assert "access" not in premiere.content.decode()
    assert refus(seconde) == refus(premiere)
    assert len(mail.outbox) == 2  # inscription, puis connexion de 10 h 05 seulement
    assert mail.outbox[1].to == [AMA]
    dernier = OtpCode.objects.order_by("-cree_le").first()
    assert (dernier.objet, dernier.email) == ("verification_email", AMA)
    assert dernier.cree_le == datetime(2026, 10, 30, 10, 5, tzinfo=ZoneInfo("UTC"))
    assert refus(mauvais) == refus(inconnu) and mauvais.status_code == 401


def test_email_non_verifie_sans_envoi_au_plafond_horaire():
    from apps.parametres.services import modifier_param

    modifier_param("otp_max_par_heure", 1)
    with freeze_time("2026-10-30 10:00:00"):
        inscrire()
    with freeze_time("2026-10-30 10:05:00"):
        reponse = connecter(AMA)

    assert code_de(reponse) == "EMAIL_NON_VERIFIE" and len(mail.outbox) == 1


def test_ca_072_3_compte_suspendu_connecte_mais_bloque(kofi):
    from apps.accounts.services import suspendre

    with freeze_time("2026-10-30 10:00:00"):
        suspendre(kofi, 3)  # jusqu'au 2026-11-02
        reponse = connecter(KOFI)
        moi = client_porteur(reponse.json()["reponse"]["access"]).get("/api/v1/moi/")

    assert reponse.status_code == 200
    etat = moi.json()["reponse"]["etat"]
    assert etat["acces"]["peut_reserver"] is False and etat["acces"]["peut_publier"] is False
    assert "COMPTE_SUSPENDU" in {alerte["code"] for alerte in etat["alertes"]}


def test_ca_072_5_aucune_route_google():
    from drf_spectacular.generators import SchemaGenerator

    chemins = list(SchemaGenerator().get_schema(request=None, public=True)["paths"])

    assert "/api/v1/auth/connexion/" in chemins
    assert not any("google" in chemin.lower() for chemin in chemins)


@pytest.mark.parametrize("cas", ["desactive", "sans_mot_de_passe"])
def test_ca_072_6_compte_desactive_ou_sans_mot_de_passe_401_identique(kofi, cas):
    if cas == "desactive":
        kofi.is_active = False
    else:
        kofi.set_unusable_password()
    kofi.save()

    reponse = connecter(KOFI)

    assert reponse.status_code == 401
    assert refus(reponse) == refus(connecter("inconnu@exemple.tg"))


def test_ca_072_7_sixieme_tentative_par_ip_429():
    limite = int(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["connexion"].split("/")[0])

    reponses = [connecter(f"personne{n}@exemple.tg") for n in range(limite + 1)]

    assert {r.status_code for r in reponses[:limite]} == {401}
    assert reponses[limite].status_code == 429
    assert code_de(reponses[limite]) == "TROP_DE_REQUETES"
    # Autre adresse IP : non concernée
    assert connecter("personne@exemple.tg", ip="10.0.0.2").status_code == 401


def test_ca_072_8_admin_connecte_en_canal_mobile_refuse_sur_l_admin():
    admin = avec_mot_de_passe(AdminFactory(roles=["audit"], email="admin@kovoit.tg"))

    reponse = connecter(admin.email)

    assert reponse.status_code == 200
    session = reponse.json()["reponse"]
    assert AccessToken(session["access"])["canal"] == "mobile"
    assert RefreshToken(session["refresh"])["canal"] == "mobile"
    client = client_porteur(session["access"])
    assert client.get("/api/v1/moi/").status_code == 200
    admin_refus = client.get("/api/v1/admin/audit/evenements/")
    assert admin_refus.status_code == 403 and code_de(admin_refus) == "CANAL_WEB_REQUIS"


def test_connexion_journalisee_et_last_login(kofi):
    from apps.audit.models import EvenementAudit

    connecter(KOFI)

    kofi.refresh_from_db()
    assert kofi.last_login is not None
    evenement = EvenementAudit.objects.get(action="session.connecter")
    assert evenement.canal == "mobile"


@pytest.mark.parametrize("donnees", [{}, {"email": "kofi"}, {"email": KOFI}])
def test_champs_absents_ou_mal_formes(donnees):
    from rest_framework.test import APIClient

    reponse = APIClient().post("/api/v1/auth/connexion/", donnees, format="json")

    assert reponse.status_code == 400 and code_de(reponse) == "DONNEES_INVALIDES"


def test_mot_de_passe_jamais_dans_la_reponse(kofi):
    assert MOT_DE_PASSE not in connecter(KOFI).content.decode()
