"""Seule table de vérité des changements de statut d'une réservation (PRD §6)."""

from apps.core.exceptions import TransitionInvalide
from apps.reservations.models import StatutReservation as S

TRANSITIONS: dict[str, set[str]] = {
    S.DEMANDEE: {S.ACCEPTEE, S.REFUSEE, S.ANNULEE},
    S.ACCEPTEE: {S.EN_COURS, S.ANNULEE, S.ABSENT},
    S.EN_COURS: {S.TERMINEE},
    S.TERMINEE: {S.CLOTUREE, S.LITIGE},
    S.LITIGE: {S.CLOTUREE},
}

# Champ horodaté à chaque arrivée dans un statut
HORODATAGES: dict[str, str] = {
    S.ACCEPTEE: "acceptee_le",
    S.REFUSEE: "refusee_le",
    S.ANNULEE: "annulee_le",
    S.ABSENT: "absent_le",
    S.EN_COURS: "en_cours_le",
    S.TERMINEE: "terminee_le",
    S.LITIGE: "litige_le",
    S.CLOTUREE: "cloturee_le",
}


def verifier_transition(actuel: str, cible: str) -> None:
    if cible not in TRANSITIONS.get(actuel, set()):
        raise TransitionInvalide(
            f"Impossible de passer de « {S(actuel).label} » à « {S(cible).label} »."
        )
