"""Enveloppe commune à toutes les réponses : { statut, message, reponse }."""

from typing import Any

from rest_framework import status as http
from rest_framework.response import Response

SUCCES = "success"
ECHEC = "failed"


def enveloppe(statut: str, message: str, reponse: Any = None) -> dict:
    return {"statut": statut, "message": message, "reponse": reponse}


def enveloppe_echec(message: str, code: str, erreurs: Any = None) -> dict:
    return enveloppe(ECHEC, message, {"code": code, "erreurs": erreurs})


def succes(message: str, data: Any = None, status: int = http.HTTP_200_OK) -> Response:
    """Réponse de succès standard, à utiliser dans toutes les vues."""
    return Response(enveloppe(SUCCES, message, data), status=status)


def echec(
    message: str, code: str, erreurs: Any = None, status: int = http.HTTP_400_BAD_REQUEST
) -> Response:
    """Réponse d'échec. Préférer lever une `ErreurMetier` dans le service."""
    return Response(enveloppe_echec(message, code, erreurs), status=status)
