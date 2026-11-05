import re

import pytest
from django.core import mail

pytestmark = pytest.mark.django_db


def test_parcours_complet_de_connexion(api_client):
    reponse = api_client.post("/api/v1/auth/otp/demander/", {"email": "yao@exemple.tg"})
    assert reponse.status_code == 200
    code = re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)

    reponse = api_client.post(
        "/api/v1/auth/otp/verifier/", {"email": "yao@exemple.tg", "code": code}
    )
    corps = reponse.json()
    assert reponse.status_code == 200
    assert corps["statut"] == "success"
    assert corps["reponse"]["nouveau_compte"] is True
    assert corps["reponse"]["utilisateur"]["profil_complet"] is False

    jetons = corps["reponse"]
    reponse = api_client.post("/api/v1/auth/jeton/rafraichir/", {"refresh": jetons["refresh"]})
    assert reponse.status_code == 200
    assert reponse.json()["reponse"]["access"]

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {jetons['access']}")
    reponse = api_client.get("/api/v1/moi/")
    assert reponse.json()["reponse"]["email"] == "yao@exemple.tg"


def _alertes(reponse) -> set[str]:
    return {alerte["code"] for alerte in reponse.json()["reponse"]["etat"]["alertes"]}


def test_ca003_1_profil_incomplet_apres_otp_puis_complete(api_client):
    api_client.post("/api/v1/auth/otp/demander/", {"email": "akossiwa@exemple.tg"})
    code = re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)
    connexion = api_client.post(
        "/api/v1/auth/otp/verifier/", {"email": "akossiwa@exemple.tg", "code": code}
    ).json()["reponse"]
    assert connexion["nouveau_compte"] is True
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {connexion['access']}")

    avant = api_client.get("/api/v1/moi/")
    assert avant.status_code == 200
    assert avant.json()["reponse"]["profil_complet"] is False
    assert "PROFIL_INCOMPLET" in _alertes(avant)

    complet = {"nom": "Mensah", "prenom": "Akossiwa", "telephone": "90 11 22 33"}
    assert api_client.patch("/api/v1/moi/", complet, format="json").status_code == 200

    apres = api_client.get("/api/v1/moi/")
    assert apres.json()["reponse"]["profil_complet"] is True
    assert apres.json()["reponse"]["telephone"] == "+22890112233"
    assert "PROFIL_INCOMPLET" not in _alertes(apres)


def test_code_mal_forme_refuse(api_client):
    reponse = api_client.post("/api/v1/auth/otp/verifier/", {"email": "a@b.tg", "code": "12"})

    assert reponse.status_code == 400
    assert "code" in reponse.json()["reponse"]["erreurs"]


def test_code_invalide(api_client):
    reponse = api_client.post("/api/v1/auth/otp/verifier/", {"email": "a@b.tg", "code": "123456"})

    assert reponse.status_code == 400
    assert reponse.json()["reponse"]["code"] == "CODE_OTP_INVALIDE"


def test_modifier_mon_profil(client_utilisateur):
    reponse = client_utilisateur.patch(
        "/api/v1/moi/", {"telephone": "+22890112233", "prenom": "Edem"}, format="json"
    )

    assert reponse.status_code == 200
    assert reponse.json()["reponse"]["telephone"] == "+22890112233"
    assert reponse.json()["reponse"]["prenom"] == "Edem"


def test_mode_conducteur_refuse_sans_kyc(client_utilisateur):
    reponse = client_utilisateur.patch(
        "/api/v1/moi/mode/", {"mode_actif": "conducteur"}, format="json"
    )

    assert reponse.status_code == 403
    assert reponse.json()["reponse"]["code"] == "KYC_CONDUCTEUR_REQUIS"


def test_mode_conducteur_accepte(client_de, conducteur):
    reponse = client_de(conducteur).patch(
        "/api/v1/moi/mode/", {"mode_actif": "conducteur"}, format="json"
    )

    assert reponse.status_code == 200
    assert reponse.json()["reponse"]["mode_actif"] == "conducteur"
    assert reponse.json()["reponse"]["etat"]["acces"]["peut_publier"] is True


def test_deconnexion(client_utilisateur, utilisateur):
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = str(RefreshToken.for_user(utilisateur))
    reponse = client_utilisateur.post("/api/v1/auth/deconnexion/", {"refresh": refresh})

    assert reponse.status_code == 200
    reponse = client_utilisateur.post("/api/v1/auth/jeton/rafraichir/", {"refresh": refresh})
    assert reponse.status_code == 401


def test_admin_liste_et_recherche_les_utilisateurs(client_admin, utilisateur):
    reponse = client_admin.get("/api/v1/admin/utilisateurs/", {"recherche": utilisateur.email})

    assert reponse.status_code == 200
    assert reponse.json()["reponse"]["count"] == 1


def test_utilisateur_suspendu_ne_peut_pas_reserver(client_de, passager, trajet):
    from apps.accounts.services import suspendre

    suspendre(passager, 7)
    reponse = client_de(passager).post(
        "/api/v1/reservations/",
        {
            "trajet_id": str(trajet.id),
            "point_id": str(trajet.points.first().id),
            "arrivee_lat": 6.13,
            "arrivee_lng": 1.222,
        },
        format="json",
    )

    assert reponse.status_code == 403
    assert reponse.json()["reponse"]["code"] == "COMPTE_SUSPENDU"


def test_reactivation_automatique_des_suspensions_expirees(passager):
    from freezegun import freeze_time

    from apps.accounts.services import suspendre
    from apps.accounts.tasks import reactiver_suspensions

    with freeze_time("2026-10-01"):
        suspendre(passager, 7)
    with freeze_time("2026-10-09"):
        assert reactiver_suspensions() == 1
    passager.refresh_from_db()
    assert passager.statut_compte == "actif"
