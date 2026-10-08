from drf_spectacular.utils import extend_schema
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.views import APIView

from apps.accounts.api.permissions import CONNECTE
from apps.core.api.reponses import succes
from apps.vehicules import services
from apps.vehicules.api.serializers import VehiculeSerializer

TAG = "véhicules"
PARSERS = [JSONParser, MultiPartParser, FormParser]


class VehiculeListeVue(APIView):
    permission_classes = CONNECTE
    parser_classes = PARSERS

    @extend_schema(tags=[TAG], summary="Mes véhicules", responses=VehiculeSerializer(many=True))
    def get(self, request):
        vehicules = services.mes_vehicules(request.user)
        return succes("Véhicules récupérés.", VehiculeSerializer(vehicules, many=True).data)

    @extend_schema(
        tags=[TAG],
        summary="Déclarer un véhicule",
        request=VehiculeSerializer,
        responses={201: VehiculeSerializer},
    )
    def post(self, request):
        entree = VehiculeSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        vehicule = services.declarer(request.user, **entree.validated_data)
        return succes("Véhicule déclaré.", VehiculeSerializer(vehicule).data, 201)


class VehiculeDetailVue(APIView):
    permission_classes = CONNECTE
    parser_classes = PARSERS

    @extend_schema(tags=[TAG], summary="Détail d'un de mes véhicules", responses=VehiculeSerializer)
    def get(self, request, pk):
        vehicule = services.get_vehicule(request.user, pk)
        return succes("Véhicule récupéré.", VehiculeSerializer(vehicule).data)

    @extend_schema(
        tags=[TAG],
        summary="Modifier un véhicule",
        request=VehiculeSerializer,
        responses=VehiculeSerializer,
    )
    def patch(self, request, pk):
        entree = VehiculeSerializer(data=request.data, partial=True)
        entree.is_valid(raise_exception=True)
        vehicule = services.modifier(request.user, pk, **entree.validated_data)
        return succes("Véhicule modifié.", VehiculeSerializer(vehicule).data)

    @extend_schema(tags=[TAG], summary="Supprimer un véhicule", responses={200: None})
    def delete(self, request, pk):
        services.supprimer(request.user, pk)
        return succes("Véhicule supprimé.")
