"""Gestionnaire d'exceptions DRF : toute erreur est renvoyée dans l'enveloppe `failed`."""

import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.views import set_rollback
from rest_framework_simplejwt.exceptions import InvalidToken

from apps.core.api.reponses import enveloppe_echec
from apps.core.exceptions import ErreurMetier

logger = logging.getLogger(__name__)

MESSAGE_DONNEES_INVALIDES = "Les données envoyées sont invalides."
MESSAGE_ERREUR_INTERNE = "Une erreur interne est survenue. Réessayez plus tard."

# Messages remplacés car techniques ou non traduits par la bibliothèque d'origine
MESSAGES_FIXES = (
    (InvalidToken, "Session invalide ou expirée. Reconnectez-vous."),
    (exceptions.ParseError, "Le corps de la requête n'est pas un JSON valide."),
)

CODES_ERREUR = (
    (exceptions.ValidationError, "DONNEES_INVALIDES"),
    (exceptions.ParseError, "REQUETE_MALFORMEE"),
    (exceptions.NotAuthenticated, "NON_AUTHENTIFIE"),
    (exceptions.AuthenticationFailed, "AUTHENTIFICATION_ECHOUEE"),
    (exceptions.PermissionDenied, "ACCES_REFUSE"),
    (exceptions.NotFound, "RESSOURCE_INTROUVABLE"),
    (exceptions.MethodNotAllowed, "METHODE_NON_AUTORISEE"),
    (exceptions.NotAcceptable, "FORMAT_NON_ACCEPTABLE"),
    (exceptions.UnsupportedMediaType, "FORMAT_NON_SUPPORTE"),
    (exceptions.Throttled, "TROP_DE_REQUETES"),
)


def gestionnaire_exceptions(exc, context):
    if isinstance(exc, ErreurMetier):
        set_rollback()
        return Response(enveloppe_echec(exc.message, exc.code, exc.erreurs), status=exc.http_status)

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    reponse = drf_exception_handler(exc, context)
    if reponse is None:
        logger.exception("Erreur non gérée", exc_info=exc)
        set_rollback()
        return Response(
            enveloppe_echec(MESSAGE_ERREUR_INTERNE, "ERREUR_INTERNE"),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    reponse.data = enveloppe_echec(_message(exc), _code(exc), _erreurs(exc))
    return reponse


def _code(exc: exceptions.APIException) -> str:
    # Code personnalisé porté par une permission (attribut `code`), ex. KYC_PASSAGER_REQUIS
    codes = exc.get_codes()
    if isinstance(codes, str) and codes != exc.default_code:
        return codes.upper()
    for classe, code in CODES_ERREUR:
        if isinstance(exc, classe):
            return code
    return "ERREUR"


def _message(exc: exceptions.APIException) -> str:
    if isinstance(exc, exceptions.ValidationError):
        return MESSAGE_DONNEES_INVALIDES
    for classe, message in MESSAGES_FIXES:
        if isinstance(exc, classe):
            return message
    detail = exc.detail
    if isinstance(detail, dict):
        detail = detail.get("detail", MESSAGE_DONNEES_INVALIDES)
    if isinstance(detail, list):
        detail = detail[0] if detail else MESSAGE_DONNEES_INVALIDES
    return str(detail)


def _erreurs(exc: exceptions.APIException):
    if isinstance(exc, exceptions.ValidationError):
        return exc.detail
    return None
