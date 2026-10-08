"""Erreurs 404 / 500 hors DRF (URL inconnue, crash) renvoyées aussi dans l'enveloppe."""

from django.http import JsonResponse

from apps.core.api.exceptions import MESSAGE_ERREUR_INTERNE
from apps.core.api.reponses import enveloppe_echec


def page_introuvable(request, exception=None):
    return JsonResponse(
        enveloppe_echec("La ressource demandée est introuvable.", "RESSOURCE_INTROUVABLE"),
        status=404,
    )


def erreur_serveur(request):
    return JsonResponse(enveloppe_echec(MESSAGE_ERREUR_INTERNE, "ERREUR_INTERNE"), status=500)
