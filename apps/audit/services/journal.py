"""Écriture du journal d'audit, appelée par les services métier.

Règle de fiabilité : un succès métier est journalisé DANS la transaction de l'opération. Si
l'écriture échoue, toute l'opération est annulée : pas de succès sans trace. Les refus et
incidents (gestionnaire d'exceptions) sont écrits hors transaction métier et ne bloquent
jamais la réponse : une panne du journal est alors seulement consignée dans les logs.
"""

import logging

from django.db import transaction
from django.utils import timezone

from apps.audit import contexte
from apps.audit.catalogue import ACTIONS
from apps.audit.models import Canal, Gravite, Resultat, Role
from apps.audit.repository import evenement_repository
from apps.audit.securite import nettoyer

logger = logging.getLogger(__name__)
_COURANT = object()


def role_de(utilisateur) -> str:
    if utilisateur is None:
        return Role.ANONYME
    if utilisateur.is_staff:
        return Role.ADMIN
    return getattr(utilisateur, "mode_actif", "") or Role.PASSAGER


def _gravite(categorie: str, resultat: str) -> str:
    if resultat == Resultat.ECHEC:
        return Gravite.CRITIQUE
    if resultat == Resultat.REFUS and categorie == "securite":
        return Gravite.AVERTISSEMENT
    return Gravite.INFO


def journaliser(
    action: str,
    *,
    ressource=None,
    ressource_id=None,
    acteur=_COURANT,
    role: str | None = None,
    resultat: str = Resultat.SUCCES,
    code_motif: str = "",
    details: dict | None = None,
    changements: dict | None = None,
    systeme: bool = False,
    categorie: str | None = None,
    gravite: str | None = None,
):
    """Enregistre un événement. `acteur` : utilisateur authentifié de la requête par défaut ;
    `systeme=True` pour une décision automatique (tâche planifiée, règle de suspension)."""
    definition = ACTIONS[action]  # KeyError : action absente du catalogue
    if systeme:
        acteur, role = None, Role.SYSTEME
    elif acteur is _COURANT:
        acteur = contexte.utilisateur_courant()
    if ressource is not None and ressource_id is None:
        ressource_id = ressource.pk
    categorie = categorie or definition.categorie
    maintenant = timezone.now()
    return evenement_repository.create(
        survenu_le=maintenant,
        enregistre_le=maintenant,
        categorie=categorie,
        action=action,
        resultat=resultat,
        gravite=gravite or _gravite(categorie, resultat),
        canal=Canal.SYSTEME if systeme else contexte.canal_courant(),
        acteur_id=acteur.pk if acteur is not None else None,
        acteur_role=role or role_de(acteur),
        ressource_type=definition.ressource if ressource_id is not None else "",
        ressource_id=str(ressource_id) if ressource_id is not None else "",
        code_motif=code_motif[:64],
        request_id=contexte.request_id(),
        details=nettoyer(details),
        changements=nettoyer(changements),
    )


def journaliser_sans_bloquer(action: str, **options) -> None:
    """Pour les refus et incidents : jamais d'exception vers l'appelant."""
    try:
        with transaction.atomic():
            journaliser(action, **options)
    except Exception:  # noqa: BLE001 - le journal ne doit pas casser la réponse d'erreur
        logger.exception("Échec d'écriture du journal d'audit (%s)", action)
