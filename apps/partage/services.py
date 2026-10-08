import secrets

from apps.core.exceptions import Conflit, RessourceIntrouvable
from apps.partage.models import LienPartage
from apps.partage.repository import lien_repository
from apps.reservations.models import StatutReservation as S

STATUTS_PARTAGEABLES = {S.ACCEPTEE, S.EN_COURS}
# Le lien reste lisible jusqu'à la clôture
STATUTS_VISIBLES = {S.ACCEPTEE, S.EN_COURS, S.TERMINEE, S.LITIGE}


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
    return lien or lien_repository.create(reservation=reservation, jeton=secrets.token_urlsafe(32))


def consulter(jeton: str) -> LienPartage:
    lien = lien_repository.get_par_jeton(jeton)
    if lien.reservation.statut not in STATUTS_VISIBLES:
        raise RessourceIntrouvable("Lien de partage invalide ou expiré.")
    return lien
