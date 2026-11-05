"""F-074 · Se déconnecter de l'application (`POST /auth/deconnexion/`, D-76)."""

import pytest
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.tests.aides_auth import (
    DECONNEXION,
    RAFRAICHIR,
    avec_mot_de_passe,
    client_porteur,
    code_de,
    connecter,
    poster,
)
from apps.accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def session(email: str) -> dict:
    avec_mot_de_passe(UserFactory(email=email))
    return connecter(email).json()["reponse"]


def test_ca_074_3_refresh_d_un_autre_compte_refuse_et_non_revoque():
    kofi = session("kofi.agbeko@exemple.tg")
    ama = session("ama.mensah@exemple.tg")
    client_ama = client_porteur(ama["access"])

    refus = client_ama.post(DECONNEXION, {"refresh": kofi["refresh"]}, format="json")

    assert refus.status_code == 403 and code_de(refus) == "JETON_AUTRE_COMPTE"
    jti_kofi = RefreshToken(kofi["refresh"])["jti"]
    assert not BlacklistedToken.objects.filter(token__jti=jti_kofi).exists()
    assert poster(RAFRAICHIR, {"refresh": kofi["refresh"]}).status_code == 200

    reussite = client_ama.post(DECONNEXION, {"refresh": ama["refresh"]}, format="json")
    assert reussite.status_code == 200 and reussite.json()["reponse"] is None
    rafraichi = poster(RAFRAICHIR, {"refresh": ama["refresh"]})
    assert rafraichi.status_code == 401 and code_de(rafraichi) == "SESSION_EXPIREE"


def test_ca_074_1_refresh_revoque_ou_invalide_jeton_invalide():
    ama = session("ama.mensah@exemple.tg")
    client = client_porteur(ama["access"])
    assert client.post(DECONNEXION, {"refresh": ama["refresh"]}, format="json").status_code == 200

    for refresh in (ama["refresh"], "pas.un.jeton"):
        reponse = client.post(DECONNEXION, {"refresh": refresh}, format="json")
        assert reponse.status_code == 400 and code_de(reponse) == "JETON_INVALIDE"


def test_refus_journalise_en_securite():
    from apps.audit.models import EvenementAudit

    kofi = session("kofi.agbeko@exemple.tg")
    ama = session("ama.mensah@exemple.tg")

    client_porteur(ama["access"]).post(DECONNEXION, {"refresh": kofi["refresh"]}, format="json")

    refus = EvenementAudit.objects.get(action="session.deconnecter", resultat="refus")
    assert refus.code_motif == "JETON_AUTRE_COMPTE" and refus.categorie == "securite"
