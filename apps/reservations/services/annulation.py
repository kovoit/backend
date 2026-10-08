"""Annulations (PRD §8) : par le passager, par le conducteur, ou suite à une suspension."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import Conflit
from apps.parametres.services import get_param
from apps.portefeuille import services as portefeuille
from apps.reservations.models import Reservation, StatutReservation
from apps.reservations.repository import reservation_repository
from apps.reservations.services.commun import (
    libelle_trajet,
    notifier_conducteur,
    notifier_passager,
    transitionner,
    verrouiller_pour_participant,
)
from apps.trajets.repository import trajet_repository
from apps.trajets.services import rendre_place

ANNULABLES = {StatutReservation.DEMANDEE, StatutReservation.ACCEPTEE}


def _est_tardive(reservation: Reservation) -> bool:
    """Seule une place déjà acceptée peut compter comme annulation tardive."""
    delai = timedelta(minutes=get_param("delai_annulation_min"))
    return (
        reservation.statut == StatutReservation.ACCEPTEE
        and reservation.trajet.depart_le - timezone.now() < delai
    )


def _annuler(reservation: Reservation, auteur, compter_incident: bool = True) -> bool:
    """Réservation verrouillée. Rend la place, débloque l'argent. Renvoie True si tardive."""
    tardive = compter_incident and _est_tardive(reservation)
    etait_acceptee = reservation.statut == StatutReservation.ACCEPTEE
    transitionner(
        reservation, StatutReservation.ANNULEE, annulee_par=auteur, annulation_tardive=tardive
    )
    if etait_acceptee:
        rendre_place(trajet_repository.get_verrouille(reservation.trajet_id))
    portefeuille.debloquer(reservation)
    return tardive


def annuler(utilisateur, reservation_id) -> Reservation:
    from apps.confiance.services import enregistrer_incident

    with transaction.atomic():
        reservation = verrouiller_pour_participant(utilisateur, reservation_id)
        if reservation.statut not in ANNULABLES:
            raise Conflit("Cette réservation ne peut plus être annulée.", code="NON_ANNULABLE")
        if reservation.trajet.depart_le <= timezone.now():
            raise Conflit("Le départ a eu lieu : annulation impossible.", code="NON_ANNULABLE")
        tardive = _annuler(reservation, utilisateur)

    message = f"La réservation pour {libelle_trajet(reservation)} a été annulée."
    if utilisateur.id == reservation.passager_id:
        notifier_conducteur(reservation, "Réservation annulée par le passager", message)
    else:
        notifier_passager(reservation, "Réservation annulée par le conducteur", message)
    if tardive:
        enregistrer_incident(utilisateur)
    return reservation_repository.get_by_id(reservation.id)


def annuler_reservations_du_trajet(trajet, conducteur) -> None:
    """Le conducteur annule son trajet (trajet déjà verrouillé et passé à « annulé »)."""
    from apps.confiance.services import enregistrer_incident

    tardive = False
    for reservation in reservation_repository.du_trajet(trajet, list(ANNULABLES)):
        reservation = reservation_repository.get_verrouillee(reservation.id)
        tardive = _annuler(reservation, conducteur) or tardive
        notifier_passager(
            reservation,
            "Trajet annulé",
            f"Le conducteur a annulé le trajet {libelle_trajet(reservation)}. "
            "Le montant bloqué vous a été rendu.",
        )
    if tardive:
        transaction.on_commit(lambda: enregistrer_incident(conducteur))


def annuler_engagements_a_venir(utilisateur) -> None:
    """Compte suspendu : ses réservations et trajets à venir sont annulés (sans incident)."""
    from apps.trajets.services import annuler_trajets_a_venir

    for reservation in reservation_repository.a_venir_de_passager(utilisateur, timezone.now()):
        reservation = reservation_repository.get_verrouillee(reservation.id)
        _annuler(reservation, utilisateur, compter_incident=False)
        notifier_conducteur(
            reservation,
            "Réservation annulée",
            f"Une réservation pour {libelle_trajet(reservation)} a été annulée.",
        )
    annuler_trajets_a_venir(utilisateur)
