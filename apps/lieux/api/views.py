from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.views import APIView

from apps.accounts.api.permissions import CONNECTE
from apps.core.api.reponses import succes
from apps.lieux.models import Lieu
from apps.lieux.services import rechercher_lieux


class LieuConnuSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lieu
        fields = ["id", "libelle", "quartier", "type", "lat", "lng"]


class LieuxVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=["trajets"],
        summary="Lieux connus de Lomé (saisie du départ et de l'arrivée), 20 au plus",
        parameters=[
            OpenApiParameter("q", str, description="Recherche (2 caractères min., sans accents)")
        ],
        responses=LieuConnuSerializer(many=True),
    )
    def get(self, request):
        lieux = rechercher_lieux(request.query_params.get("q", ""))
        return succes("Lieux récupérés.", LieuConnuSerializer(lieux, many=True).data)
