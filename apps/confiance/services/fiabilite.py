"""Fiabilité (PRD §8) et suspension automatique au-delà du seuil d'incidents."""

from datetime import timedelta

from django.utils import timezone

from apps.accounts.services import est_suspendu, suspendre
from apps.confiance.repository import note_repository
from apps.kyc.models import TypeDossier
from apps.kyc.services import est_verifie
from apps.parametres.services import get_param
from apps.reservations.repository import reservation_repository


def _depuis():
    return timezone.now() - timedelta(days=get_param("periode_incidents_j"))


def fiabilite_pct(utilisateur) -> int:
    """1 − (annulations tardives + absences) / réservations de la période, en pourcentage."""
    total = reservation_repository.compter_impliquant(utilisateur, _depuis())
    if total == 0:
        return 100
    incidents = reservation_repository.compter_incidents(utilisateur, _depuis())
    return max(0, round(100 * (1 - incidents / total)))


def detail_fiabilite(utilisateur) -> dict:
    """Compteurs de la période ; `pct` vaut None sans aucune réservation (rien à mesurer)."""
    depuis = _depuis()
    reservations = reservation_repository.compter_impliquant(utilisateur, depuis)
    tardives = reservation_repository.compter_annulations_tardives(utilisateur, depuis)
    absences = reservation_repository.compter_absences(utilisateur, depuis)
    pct = None
    if reservations:
        pct = max(0, round(100 * (1 - (tardives + absences) / reservations)))
    return {
        "pct": pct,
        "periode_j": get_param("periode_incidents_j"),
        "reservations": reservations,
        "annulations_tardives": tardives,
        "absences": absences,
    }


def resume_confiance(utilisateur) -> dict:
    moyenne, nombre = note_repository.moyenne_de(utilisateur)
    return {
        "note_moyenne": round(moyenne, 1) if moyenne is not None else None,
        "nombre_notes": nombre,
        "fiabilite_pct": fiabilite_pct(utilisateur),
        "passager_verifie": est_verifie(utilisateur, TypeDossier.PASSAGER),
        "conducteur_verifie": est_verifie(utilisateur, TypeDossier.CONDUCTEUR),
    }


def enregistrer_incident(utilisateur) -> bool:
    """À appeler après une annulation tardive ou une absence. Renvoie True si suspendu."""
    if est_suspendu(utilisateur):
        return False
    incidents = reservation_repository.compter_incidents(utilisateur, _depuis())
    if incidents < get_param("seuil_incidents"):
        return False
    motif = (
        f"Suspension automatique : {incidents} incidents (annulations tardives ou absences) "
        f"en {get_param('periode_incidents_j')} jours."
    )
    suspendre(utilisateur, get_param("duree_suspension_j"), motif)
    return True
