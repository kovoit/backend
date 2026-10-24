"""Notes après trajet, signalements et traitement des litiges par l'administrateur."""

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services import journaliser
from apps.confiance.models import Note, Signalement, StatutSignalement
from apps.confiance.repository import note_repository, signalement_repository
from apps.core.exceptions import Conflit, DonneesInvalides
from apps.reservations.models import StatutReservation as S

STATUTS_NOTABLES = {S.TERMINEE, S.LITIGE, S.CLOTUREE}
STATUTS_SIGNALABLES = {S.EN_COURS, S.TERMINEE, S.LITIGE, S.CLOTUREE, S.ABSENT}


def _autre_partie(reservation, utilisateur):
    conducteur = reservation.trajet.conducteur
    return conducteur if utilisateur.id == reservation.passager_id else reservation.passager


def noter(auteur, reservation_id, note: int, commentaire: str = "") -> Note:
    from apps.reservations.services import get_reservation

    reservation = get_reservation(auteur, reservation_id)
    # Passager absent : seul le conducteur, qui l'a attendu, peut le noter
    absent_note_par_conducteur = (
        reservation.statut == S.ABSENT and auteur.id == reservation.trajet.conducteur_id
    )
    if reservation.statut not in STATUTS_NOTABLES and not absent_note_par_conducteur:
        raise Conflit("La note est possible après le trajet.", code="NOTE_PREMATUREE")
    try:
        with transaction.atomic():
            avis = note_repository.create(
                reservation=reservation,
                auteur=auteur,
                cible=_autre_partie(reservation, auteur),
                note=note,
                commentaire=commentaire,
            )
            journaliser("avis.noter", ressource=reservation, details={"note": note})
            return avis
    except IntegrityError as exc:
        raise Conflit("Vous avez déjà noté ce trajet.", code="DEJA_NOTE") from exc


def signaler(auteur, reservation_id, motif: str) -> Signalement:
    """Pendant ou après le trajet. Sur un trajet terminé, la réservation passe en litige."""
    from apps.reservations.repository import reservation_repository
    from apps.reservations.services import get_reservation, passer_en_litige

    reservation = get_reservation(auteur, reservation_id)
    if reservation.statut not in STATUTS_SIGNALABLES:
        raise Conflit(
            "Signalement possible pendant ou après le trajet.", code="SIGNALEMENT_IMPOSSIBLE"
        )
    with transaction.atomic():
        reservation = reservation_repository.get_verrouillee(reservation.id)
        litige = reservation.statut == S.TERMINEE
        if litige:
            passer_en_litige(reservation)
        signalement = signalement_repository.create(
            reservation=reservation,
            auteur=auteur,
            cible=_autre_partie(reservation, auteur),
            motif=motif,
        )
        journaliser(
            "signalement.creer",
            ressource=reservation,
            details={"signalement_id": signalement.id, "litige": litige},
        )
        return signalement


def dernieres_notes(utilisateur, nombre: int = 5):
    return note_repository.dernieres_recues(utilisateur, nombre)


def signalements_de_reservation(reservation):
    return signalement_repository.de_reservation(reservation)


def lister_signalements(statut: str | None = None):
    return signalement_repository.lister(statut)


def get_signalement(signalement_id) -> Signalement:
    return signalement_repository.get_by_id(signalement_id)


def traiter_signalement(admin, signalement_id, resolution: str, decision: str = "") -> Signalement:
    """Un litige exige une décision : payer le conducteur ou rembourser le passager."""
    from apps.reservations.services import trancher_litige

    with transaction.atomic():
        signalement = signalement_repository.get_for_update(signalement_id)
        if signalement.statut == StatutSignalement.TRAITE:
            raise Conflit("Ce signalement est déjà traité.", code="DEJA_TRAITE")
        reservation = signalement.reservation
        if reservation.statut == S.LITIGE:
            if not decision:
                raise DonneesInvalides(
                    "Ce signalement porte sur un litige : une décision est requise.",
                    code="DECISION_REQUISE",
                )
            trancher_litige(reservation.id, decision)
        signalement_repository.update(
            signalement,
            statut=StatutSignalement.TRAITE,
            resolution=resolution,
            decision=decision,
            traite_le=timezone.now(),
            traite_par=admin,
        )
        journaliser(
            "signalement.traiter",
            ressource=signalement,
            acteur=admin,
            changements={"statut": [StatutSignalement.OUVERT, StatutSignalement.TRAITE]},
            details={"reservation_id": reservation.id, "decision": decision},
        )
    return signalement_repository.get_by_id(signalement.id)
