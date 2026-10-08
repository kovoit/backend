from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.views import APIView

from apps.accounts.api.permissions import ADMIN, CONNECTE
from apps.core.api.reponses import succes
from apps.dashboard import services


class EconomieTrajetSerializer(serializers.Serializer):
    trajet_id = serializers.UUIDField()
    depart_le = serializers.DateTimeField()
    depart = serializers.CharField()
    arrivee = serializers.CharField()
    montant = serializers.IntegerField()


class EconomiesSerializer(serializers.Serializer):
    mois_en_cours = serializers.IntegerField()
    total = serializers.IntegerField()
    par_trajet = EconomieTrajetSerializer(many=True)


class IndicateursSerializer(serializers.Serializer):
    utilisateurs = serializers.IntegerField()
    passagers_verifies = serializers.IntegerField()
    conducteurs_verifies = serializers.IntegerField()
    trajets_publies = serializers.IntegerField()
    trajets_termines = serializers.IntegerField()
    passagers_transportes = serializers.IntegerField()
    economies_realisees = serializers.IntegerField()


class EconomiesVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=["profil"],
        summary="Mes économies de conducteur (par trajet et cumul du mois)",
        responses=EconomiesSerializer,
    )
    def get(self, request):
        economies = services.economies_conducteur(request.user)
        return succes("Économies calculées.", EconomiesSerializer(economies).data)


class IndicateursVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=["admin - indicateurs"], summary="Indicateurs clés", responses=IndicateursSerializer
    )
    def get(self, request):
        return succes("Indicateurs calculés.", IndicateursSerializer(services.indicateurs()).data)
