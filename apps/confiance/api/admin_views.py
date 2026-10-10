from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.views import APIView

from apps.accounts.api.permissions import ADMIN
from apps.confiance import services
from apps.confiance.api.admin_serializers import (
    SignalementAdminDetailSerializer,
    SignalementAdminSerializer,
    TraitementAdminSerializer,
)
from apps.core.api.pagination import reponse_paginee
from apps.core.api.reponses import succes

TAG = "admin - signalements"


class SignalementAdminListeVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG],
        summary="Lister les signalements et litiges (les plus anciens d'abord)",
        parameters=[OpenApiParameter("statut", str, enum=["ouvert", "traite"])],
        responses=SignalementAdminSerializer(many=True),
    )
    def get(self, request):
        signalements = services.lister_signalements(request.query_params.get("statut"))
        return reponse_paginee(
            request, signalements, SignalementAdminSerializer, "Signalements récupérés.", self
        )


class SignalementAdminDetailVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG],
        summary="Détail d'un signalement (réservation, résolution)",
        responses=SignalementAdminDetailSerializer,
    )
    def get(self, request, pk):
        signalement = services.get_signalement(pk)
        return succes("Signalement récupéré.", SignalementAdminDetailSerializer(signalement).data)


class SignalementTraiterVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG],
        summary="Traiter un signalement ; trancher le litige si la réservation est en litige",
        request=TraitementAdminSerializer,
        responses=SignalementAdminDetailSerializer,
    )
    def post(self, request, pk):
        entree = TraitementAdminSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        signalement = services.traiter_signalement(request.user, pk, **entree.validated_data)
        return succes("Signalement traité.", SignalementAdminDetailSerializer(signalement).data)
