from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.views import APIView

from apps.accounts.api.permissions import ADMIN
from apps.core.api.pagination import reponse_paginee
from apps.core.api.reponses import succes
from apps.trajets import services
from apps.trajets.api.admin_serializers import TrajetAdminDetailSerializer, TrajetAdminSerializer
from apps.trajets.models import StatutTrajet

TAG = "admin - trajets"


class FiltresTrajetsSerializer(serializers.Serializer):
    statut = serializers.ChoiceField(choices=StatutTrajet.choices, required=False)
    recherche = serializers.CharField(required=False, help_text="Conducteur (nom, téléphone), lieu")
    date = serializers.DateField(required=False, help_text="Jour de départ (heure de Lomé)")


class TrajetAdminListeVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG],
        summary="Lister les trajets (départs les plus récents d'abord)",
        parameters=[FiltresTrajetsSerializer, OpenApiParameter("page", int)],
        responses=TrajetAdminSerializer(many=True),
    )
    def get(self, request):
        filtres = FiltresTrajetsSerializer(data=request.query_params)
        filtres.is_valid(raise_exception=True)
        donnees = filtres.validated_data
        trajets = services.lister_trajets(
            donnees.get("statut"), donnees.get("recherche"), donnees.get("date")
        )
        return reponse_paginee(request, trajets, TrajetAdminSerializer, "Trajets récupérés.", self)


class TrajetAdminDetailVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG],
        summary="Détail d'un trajet (véhicule, points de prise en charge, réservations)",
        responses=TrajetAdminDetailSerializer,
    )
    def get(self, request, pk):
        trajet = services.get_trajet(pk)
        return succes("Trajet récupéré.", TrajetAdminDetailSerializer(trajet).data)
