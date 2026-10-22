"""Outils de test : vraies connexions (OTP mobile, back-office) et lecture du journal."""

import re

from django.core import mail
from django.db.models import Q
from rest_framework.test import APIClient

from apps.audit.models import EvenementAudit
from apps.audit.repository import evenement_repository


def client_mobile(api_client: APIClient, email: str) -> tuple[APIClient, str]:
    """Connexion par code OTP comme l'app mobile : renvoie le client authentifié et son jeton."""
    api_client.post("/api/v1/auth/otp/demander/", {"email": email}, format="json")
    code = re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)
    reponse = api_client.post(
        "/api/v1/auth/otp/verifier/", {"email": email, "code": code}, format="json"
    )
    access = reponse.json()["reponse"]["access"]
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client, access


def client_web_admin(admin, mot_de_passe: str = "MotDePasse-Solide-2026") -> tuple[APIClient, str]:
    """Connexion au back-office (email + mot de passe) comme l'admin React."""
    admin.set_password(mot_de_passe)
    admin.save()
    reponse = APIClient().post(
        "/api/v1/auth/admin/connexion/",
        {"email": admin.email, "mot_de_passe": mot_de_passe},
        format="json",
    )
    access = reponse.json()["reponse"]["access"]
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client, access


def vider_journal() -> None:
    """Les fixtures (recharge, KYC…) écrivent déjà au journal : on repart de zéro."""
    evenement_repository.purger(Q())


def evenements(action: str | None = None, **filtres):
    queryset = EvenementAudit.objects.order_by("enregistre_le")
    if action:
        queryset = queryset.filter(action=action)
    return list(queryset.filter(**filtres))


def un_evenement(action: str, **filtres) -> EvenementAudit:
    trouves = evenements(action, **filtres)
    assert len(trouves) == 1, f"{action} : {len(trouves)} événement(s)"
    return trouves[0]
