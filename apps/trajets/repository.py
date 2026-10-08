from datetime import datetime

from django.db.models import Count, Q

from apps.core.repository import BaseRepository
from apps.trajets.models import PointPriseEnCharge, StatutTrajet, Trajet


class TrajetRepository(BaseRepository[Trajet]):
    model = Trajet
    message_introuvable = "Trajet introuvable."

    def queryset(self):
        return (
            super().queryset().select_related("conducteur", "vehicule").prefetch_related("points")
        )

    def get_verrouille(self, trajet_id) -> Trajet:
        """Verrou sur la seule ligne du trajet. À appeler dans un `transaction.atomic()`."""
        return self._get(self.model.objects.select_for_update(), pk=trajet_id)

    def candidats_recherche(
        self,
        debut: datetime,
        fin: datetime,
        exclure_conducteur,
        lat_min: float,
        lat_max: float,
        lng_min: float,
        lng_max: float,
    ):
        """Pré-filtre en base (boîte autour de l'arrivée) ; le rayon exact est calculé ensuite."""
        return (
            self.queryset()
            .filter(
                statut=StatutTrajet.PUBLIE,
                places_restantes__gte=1,
                depart_le__gte=debut,
                depart_le__lte=fin,
                arrivee_lat__range=(lat_min, lat_max),
                arrivee_lng__range=(lng_min, lng_max),
            )
            .exclude(conducteur=exclure_conducteur)
        )

    def de_conducteur(self, conducteur):
        return (
            self.queryset()
            .filter(conducteur=conducteur)
            .annotate(nb_demandes=Count("reservations", filter=Q(reservations__statut="demandee")))
            .order_by("-depart_le")
        )

    def a_venir_de_conducteur(self, conducteur, maintenant: datetime):
        return self.filter(
            conducteur=conducteur,
            statut__in=[StatutTrajet.PUBLIE, StatutTrajet.COMPLET],
            depart_le__gt=maintenant,
        )

    def lister(self, statut: str | None = None):
        queryset = self.queryset().order_by("-depart_le")
        return queryset.filter(statut=statut) if statut else queryset

    def compter(self, **filtres) -> int:
        return self.model.objects.filter(**filtres).count()


class PointRepository(BaseRepository[PointPriseEnCharge]):
    model = PointPriseEnCharge
    message_introuvable = "Point de prise en charge introuvable."

    def creer_pour(self, trajet: Trajet, points: list[dict]) -> None:
        self.model.objects.bulk_create(
            [
                self.model(trajet=trajet, ordre=ordre, **point)
                for ordre, point in enumerate(points, 1)
            ]
        )

    def get_du_trajet(self, trajet: Trajet, point_id) -> PointPriseEnCharge:
        return self._get(self.queryset(), pk=point_id, trajet=trajet)


trajet_repository = TrajetRepository()
point_repository = PointRepository()
