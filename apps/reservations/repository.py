from datetime import datetime

from django.db.models import Q

from apps.core.repository import BaseRepository
from apps.reservations.models import STATUTS_ACTIFS, Reservation, StatutReservation
from apps.reservations.transitions import HORODATAGES

STATUTS_TRANSPORTES = [
    StatutReservation.TERMINEE,
    StatutReservation.LITIGE,
    StatutReservation.CLOTUREE,
]


class ReservationRepository(BaseRepository[Reservation]):
    model = Reservation
    message_introuvable = "Réservation introuvable."

    def queryset(self):
        return (
            super()
            .queryset()
            .select_related("trajet", "trajet__conducteur", "trajet__vehicule", "passager", "point")
        )

    def get_verrouillee(self, reservation_id) -> Reservation:
        """Verrou sur la seule ligne de la réservation. À appeler dans un `transaction.atomic()`."""
        return self._get(self.model.objects.select_for_update(), pk=reservation_id)

    def changer_statut(self, reservation: Reservation, statut: str, maintenant, **champs):
        champs[HORODATAGES[statut]] = maintenant
        return self.update(reservation, statut=statut, **champs)

    def active_existe(self, trajet, passager) -> bool:
        return self.exists(trajet=trajet, passager=passager, statut__in=STATUTS_ACTIFS)

    def de_passager(self, passager):
        return self.queryset().filter(passager=passager).order_by("-cree_le")

    def du_trajet(self, trajet, statuts: list[str] | None = None):
        queryset = self.queryset().filter(trajet=trajet).order_by("cree_le")
        return queryset.filter(statut__in=statuts) if statuts else queryset

    def a_venir_de_passager(self, passager, maintenant: datetime):
        return self.filter(
            passager=passager,
            statut__in=[StatutReservation.DEMANDEE, StatutReservation.ACCEPTEE],
            trajet__depart_le__gt=maintenant,
        )

    def a_cloturer(self, limite: datetime):
        return self.filter(statut=StatutReservation.TERMINEE, terminee_le__lte=limite)

    def lister(self, statut: str | None = None):
        queryset = self.queryset().order_by("-cree_le")
        return queryset.filter(statut=statut) if statut else queryset

    # --- Fiabilité (PRD §8) ---

    def compter_impliquant(self, utilisateur, depuis: datetime) -> int:
        return self.filter(
            Q(passager=utilisateur) | Q(trajet__conducteur=utilisateur), cree_le__gte=depuis
        ).count()

    def compter_incidents(self, utilisateur, depuis: datetime) -> int:
        tardives = Q(annulee_par=utilisateur, annulation_tardive=True, annulee_le__gte=depuis)
        absences = Q(passager=utilisateur, statut=StatutReservation.ABSENT, absent_le__gte=depuis)
        return self.filter(tardives | absences).count()

    # --- Indicateurs ---

    def compter_transportes(self) -> int:
        return self.filter(statut__in=STATUTS_TRANSPORTES).count()


reservation_repository = ReservationRepository()
