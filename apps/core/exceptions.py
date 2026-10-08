"""Erreurs métier levées par les services et converties en réponse `failed` par l'API."""

from rest_framework import status


class ErreurMetier(Exception):
    """Erreur métier de base. Chaque sous-classe fixe son code, son message et son statut HTTP."""

    code = "ERREUR_METIER"
    message = "La demande ne peut pas être traitée."
    http_status = status.HTTP_400_BAD_REQUEST

    def __init__(self, message=None, *, code=None, http_status=None, erreurs=None):
        self.message = message or self.message
        self.code = code or self.code
        self.http_status = http_status or self.http_status
        self.erreurs = erreurs
        super().__init__(self.message)


class DonneesInvalides(ErreurMetier):
    code = "DONNEES_INVALIDES"
    message = "Les données envoyées sont invalides."


class RessourceIntrouvable(ErreurMetier):
    code = "RESSOURCE_INTROUVABLE"
    message = "La ressource demandée est introuvable."
    http_status = status.HTTP_404_NOT_FOUND


class ActionInterdite(ErreurMetier):
    code = "ACTION_INTERDITE"
    message = "Vous n'êtes pas autorisé à effectuer cette action."
    http_status = status.HTTP_403_FORBIDDEN


class Conflit(ErreurMetier):
    code = "CONFLIT"
    message = "L'action est impossible dans l'état actuel."
    http_status = status.HTTP_409_CONFLICT


class TropDeRequetes(ErreurMetier):
    code = "TROP_DE_REQUETES"
    message = "Trop de demandes. Réessayez plus tard."
    http_status = status.HTTP_429_TOO_MANY_REQUESTS


class TransitionInvalide(Conflit):
    code = "TRANSITION_INVALIDE"
    message = "Ce changement de statut n'est pas autorisé."
