"""Contexte de la requête en cours : identifiant de corrélation, acteur et canal vérifiés.

L'acteur vient de l'authentification faite par le serveur (DRF recopie `user` et `auth` sur
la requête Django). Le canal vient d'un claim signé du JWT (`canal`, posé à l'émission du
jeton), jamais d'un en-tête ou d'un champ envoyé par le client.
"""

import re
import uuid
from contextvars import ContextVar

from django.http import HttpRequest

from apps.audit.models import Canal

CLAIM_CANAL = "canal"
ENTETE_REQUETE = "X-Request-ID"
_FORMAT_REQUEST_ID = re.compile(r"^[0-9a-fA-F]{32}$")
_requete: ContextVar[HttpRequest | None] = ContextVar("requete_audit", default=None)


class ContexteAuditMiddleware:
    """Pose un identifiant de corrélation (repris du client s'il est bien formé) sur la
    requête, l'expose dans l'en-tête de réponse et rend la requête accessible aux services."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        recu = request.headers.get(ENTETE_REQUETE, "")
        request.request_id = recu.lower() if _FORMAT_REQUEST_ID.match(recu) else uuid.uuid4().hex
        jeton = _requete.set(request)
        try:
            reponse = self.get_response(request)
        finally:
            _requete.reset(jeton)
        reponse[ENTETE_REQUETE] = request.request_id
        return reponse


def requete_courante() -> HttpRequest | None:
    return _requete.get()


def request_id() -> str:
    requete = requete_courante()
    return getattr(requete, "request_id", "") if requete else ""


def utilisateur_courant():
    requete = requete_courante()
    utilisateur = getattr(requete, "user", None) if requete else None
    return utilisateur if utilisateur is not None and utilisateur.is_authenticated else None


def canal_courant() -> str:
    """Hors requête (Celery, commande) : système. Sinon le claim signé du jeton, ou à défaut
    l'espace de l'API appelée (connexion encore sans jeton)."""
    requete = requete_courante()
    if requete is None:
        return Canal.SYSTEME
    jeton = getattr(requete, "auth", None)
    valeur = jeton.get(CLAIM_CANAL) if hasattr(jeton, "get") else None
    if valeur in (Canal.WEB, Canal.MOBILE):
        return valeur
    if jeton is None and requete.path.startswith("/api/v1/auth/admin/"):
        return Canal.WEB
    if jeton is None and requete.path.startswith("/api/v1/auth/otp/"):
        return Canal.MOBILE
    return Canal.API


def route_courante() -> tuple[str, str, dict] | None:
    """(nom de route, méthode, paramètres d'URL) de la requête en cours."""
    requete = requete_courante()
    correspondance = getattr(requete, "resolver_match", None) if requete else None
    if correspondance is None:
        return None
    return correspondance.url_name or "", requete.method, correspondance.kwargs
