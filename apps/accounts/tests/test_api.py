import re

import pytest
from django.core import mail
from rest_framework import status

from apps.reservations.models import StatutReservation

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


def test_telephone_invalide(client_utilisateur):
    reponse = client_utilisateur.patch("/api/v1/moi/", {"telephone": "abc"}, format="json")

    assert reponse.status_code == 400


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


def test_admin_suspend_puis_reactive(client_admin, passager, reservation):
    url = f"/api/v1/admin/utilisateurs/{passager.id}/"

    reponse = client_admin.post(url + "suspendre/", {"jours": 7}, format="json")
    assert reponse.status_code == 200
    assert reponse.json()["reponse"]["statut_compte"] == "suspendu"
    reservation.refresh_from_db()
    assert reservation.statut == StatutReservation.ANNULEE

    reponse = client_admin.post(url + "reactiver/")
    assert reponse.json()["reponse"]["statut_compte"] == "actif"
    assert client_admin.get(url).status_code == status.HTTP_200_OK


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
