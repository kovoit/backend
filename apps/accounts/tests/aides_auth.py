"""Outils des tests de connexion de l'application (inscription, connexion, mot de passe)."""

import re

from django.core import mail
from rest_framework.test import APIClient

INSCRIPTION = "/api/v1/auth/inscription/"
VERIFIER = "/api/v1/auth/inscription/verifier/"
RENVOYER = "/api/v1/auth/inscription/renvoyer-code/"
CONNEXION = "/api/v1/auth/connexion/"
OUBLIE = "/api/v1/auth/mot-de-passe/oublie/"
REINITIALISER = "/api/v1/auth/mot-de-passe/reinitialiser/"
RAFRAICHIR = "/api/v1/auth/jeton/rafraichir/"
DECONNEXION = "/api/v1/auth/deconnexion/"
MOI = "/api/v1/moi/"

AMA = "ama.mensah@exemple.tg"
MOT_DE_PASSE = "Lome-Kovoit-26"
NOUVEAU_MOT_DE_PASSE = "Nouveau-Kovoit-27"


def champs_inscription(**valeurs) -> dict:
    return {
        "prenom": "Ama",
        "nom": "Mensah",
        "email": "Ama.Mensah@Exemple.tg",
        "telephone": "90 11 22 33",
        "mot_de_passe": MOT_DE_PASSE,
        "cgu_acceptees": True,
    } | valeurs


def poster(chemin: str, donnees: dict, client: APIClient | None = None):
    return (client or APIClient()).post(chemin, donnees, format="json")


def inscrire(**valeurs):
    return poster(INSCRIPTION, champs_inscription(**valeurs))


def dernier_code() -> str:
    return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)


def autre_code(code: str) -> str:
    return "000000" if code != "000000" else "111111"


def code_de(reponse) -> str:
    return reponse.json()["reponse"]["code"]


def connecter(email: str, mot_de_passe: str = MOT_DE_PASSE, ip: str = "10.0.0.1"):
    """Chaque test garde sous la limite de 5/min par IP, ou change d'IP (REMOTE_ADDR)."""
    return APIClient().post(
        CONNEXION, {"email": email, "mot_de_passe": mot_de_passe}, format="json", REMOTE_ADDR=ip
    )


def client_porteur(access: str) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


def avec_mot_de_passe(utilisateur, mot_de_passe: str = MOT_DE_PASSE):
    utilisateur.set_password(mot_de_passe)
    utilisateur.save()
    return utilisateur
