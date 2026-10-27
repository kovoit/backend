import secrets

from django.db import transaction

from apps.audit.services import journaliser
from apps.core.exceptions import Conflit, RessourceIntrouvable
from apps.partage.models import LienPartage
from apps.partage.repository import lien_repository
from apps.reservations.models import StatutReservation as S

# Création et lecture du lien : il cesse d'être valide dès l'arrivée (D-05)
STATUTS_PARTAGEABLES = {S.ACCEPTEE, S.EN_COURS}


def creer_lien(passager, reservation_id) -> LienPartage:
    from apps.reservations.services import get_reservation

    reservation = get_reservation(passager, reservation_id)
    if reservation.passager_id != passager.id:
        raise RessourceIntrouvable("Réservation introuvable.")
    if reservation.statut not in STATUTS_PARTAGEABLES:
        raise Conflit(
            "Le partage est possible une fois la réservation acceptée.", code="PARTAGE_IMPOSSIBLE"
        )
    lien = lien_repository.get_or_none(reservation=reservation)
    if lien:
        return lien
    with transaction.atomic():
        lien = lien_repository.create(reservation=reservation, jeton=secrets.token_urlsafe(32))
        # Le jeton du lien est un secret : seule la réservation est journalisée
        journaliser("partage.creer_lien", ressource=reservation, role="passager")
    return lien


def consulter(jeton: str) -> LienPartage:
    lien = lien_repository.get_par_jeton(jeton)
    if lien.reservation.statut not in STATUTS_PARTAGEABLES:
        raise RessourceIntrouvable("Lien de partage invalide ou expiré.")
    return lien
