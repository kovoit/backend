from drf_spectacular.utils import OpenApiParameter, PolymorphicProxySerializer, extend_schema
from rest_framework.views import APIView

from apps.accounts.api.permissions import CONNECTE, CompteActif
from apps.core.api.pagination import reponse_paginee
from apps.core.api.reponses import succes
from apps.kyc.api.permissions import KycPassagerVerifie
from apps.reservations import services
from apps.reservations.api import serializers as s

TAG = "réservations"
FILTRE_STATUT = OpenApiParameter("statut", str, description="Filtrer par statut")
VUE_SELON_ROLE = PolymorphicProxySerializer(
    component_name="ReservationSelonRole",
    serializers=[s.ReservationPassagerSerializer, s.ReservationConducteurSerializer],
    resource_type_field_name=None,
)


class ReservationListeVue(APIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [p() for p in [*CONNECTE, CompteActif, KycPassagerVerifie]]
        return [p() for p in CONNECTE]

    @extend_schema(
        tags=[TAG],
        summary="Mes réservations (passager)",
        parameters=[FILTRE_STATUT],
        responses=s.ReservationPassagerSerializer(many=True),
    )
    def get(self, request):
        reservations = services.mes_reservations(request.user, request.query_params.get("statut"))
        return reponse_paginee(
            request, reservations, s.ReservationPassagerSerializer, "Réservations récupérées.", self
        )

    @extend_schema(
        tags=[TAG],
        summary="Demander une place (le montant est bloqué sur le portefeuille)",
        request=s.DemandeSerializer,
        responses={201: s.ReservationPassagerSerializer},
    )
    def post(self, request):
        entree = s.DemandeSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        reservation = services.demander_place(request.user, **entree.validated_data)
        return succes(
            "Demande envoyée au conducteur.",
            s.ReservationPassagerSerializer(reservation).data,
            201,
        )


class ReservationDetailVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Détail d'une réservation (le code de départ n'est visible que du passager)",
        responses=VUE_SELON_ROLE,
    )
    def get(self, request, pk):
        reservation = services.get_reservation(request.user, pk)
        return succes("Réservation récupérée.", s.serialiser_pour(request.user, reservation))


class TrajetReservationsVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=["trajets"],
        summary="Demandes et réservations reçues sur mon trajet (conducteur)",
        parameters=[FILTRE_STATUT],
        responses=s.ReservationConducteurSerializer(many=True),
    )
    def get(self, request, pk):
        reservations = services.reservations_du_trajet(
            request.user, pk, request.query_params.get("statut")
        )
        return reponse_paginee(
            request,
            reservations,
            s.ReservationConducteurSerializer,
            "Réservations récupérées.",
            self,
        )
