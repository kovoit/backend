from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.views import APIView

from apps.accounts.api.permissions import ADMIN
from apps.core.api.pagination import reponse_paginee
from apps.core.api.reponses import succes
from apps.reservations import services
from apps.reservations.api.admin_serializers import (
    ReservationAdminDetailSerializer,
    ReservationAdminSerializer,
)
from apps.reservations.models import StatutReservation

TAG = "admin - réservations"


class FiltresReservationsSerializer(serializers.Serializer):
    statut = serializers.ChoiceField(choices=StatutReservation.choices, required=False)
    recherche = serializers.CharField(
        required=False, help_text="Passager ou conducteur : nom, prénom, téléphone, email"
    )
    trajet = serializers.UUIDField(required=False)


class ReservationAdminListeVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG],
        summary="Lister les réservations (les plus récentes d'abord)",
        parameters=[FiltresReservationsSerializer, OpenApiParameter("page", int)],
        responses=ReservationAdminSerializer(many=True),
    )
    def get(self, request):
        filtres = FiltresReservationsSerializer(data=request.query_params)
        filtres.is_valid(raise_exception=True)
        donnees = filtres.validated_data
        reservations = services.lister_reservations(
            donnees.get("statut"), donnees.get("recherche"), donnees.get("trajet")
        )
        return reponse_paginee(
            request, reservations, ReservationAdminSerializer, "Réservations récupérées.", self
        )


class ReservationAdminDetailVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG],
        summary="Détail d'une réservation (historique des statuts, signalements)",
        responses=ReservationAdminDetailSerializer,
    )
    def get(self, request, pk):
        reservation = services.get_reservation_admin(pk)
        return succes("Réservation récupérée.", ReservationAdminDetailSerializer(reservation).data)
