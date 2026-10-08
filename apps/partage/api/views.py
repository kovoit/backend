from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.accounts.api.permissions import CONNECTE
from apps.core.api.reponses import succes
from apps.partage import services

TAG = "partage de trajet"


class LienSerializer(serializers.Serializer):
    jeton = serializers.CharField()
    chemin = serializers.SerializerMethodField()

    def get_chemin(self, lien) -> str:
        return f"/api/v1/partage/{lien.jeton}/"


class TrajetPartageSerializer(serializers.Serializer):
    """Le strict minimum pour un proche : ni email, ni téléphone, ni pièce."""

    statut = serializers.CharField(source="reservation.statut")
    conducteur_prenom = serializers.CharField(source="reservation.trajet.conducteur.prenom")
    vehicule = serializers.SerializerMethodField()
    depart = serializers.CharField(source="reservation.trajet.depart_libelle")
    arrivee = serializers.CharField(source="reservation.trajet.arrivee_libelle")
    depart_le = serializers.DateTimeField(source="reservation.trajet.depart_le")
    position_lat = serializers.FloatField(source="reservation.trajet.position_lat")
    position_lng = serializers.FloatField(source="reservation.trajet.position_lng")
    position_le = serializers.DateTimeField(source="reservation.trajet.position_le")

    def get_vehicule(self, lien) -> str:
        v = lien.reservation.trajet.vehicule
        return f"{v.marque} {v.modele} {v.couleur} — {v.immatriculation}"


class CreerLienVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Créer le lien « Partager mon trajet » (passager)",
        request=None,
        responses={201: LienSerializer},
    )
    def post(self, request, pk):
        lien = services.creer_lien(request.user, pk)
        return succes("Lien de partage prêt.", LienSerializer(lien).data, 201)


class ConsulterLienVue(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=[TAG], summary="Suivre un trajet partagé (public)", responses=TrajetPartageSerializer
    )
    def get(self, request, jeton: str):
        lien = services.consulter(jeton)
        return succes("Trajet partagé.", TrajetPartageSerializer(lien).data)
