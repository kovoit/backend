"""Trajets vus par le back-office : coordonnées du conducteur, lieux groupés, réservations."""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.api.serializers import UtilisateurResumeSerializer
from apps.reservations.api.admin_serializers import ReservationAdminSerializer
from apps.reservations.services import reservations_du_trajet_admin
from apps.trajets.api.serializers import PointSerializer
from apps.trajets.models import Trajet
from apps.vehicules.api.serializers import VehiculeResumeSerializer


class LieuSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    libelle = serializers.CharField()


def _lieu(trajet: Trajet, prefixe: str) -> dict:
    return {
        "lat": getattr(trajet, f"{prefixe}_lat"),
        "lng": getattr(trajet, f"{prefixe}_lng"),
        "libelle": getattr(trajet, f"{prefixe}_libelle"),
    }


class TrajetAdminSerializer(serializers.ModelSerializer):
    conducteur = UtilisateurResumeSerializer(read_only=True)
    depart = serializers.SerializerMethodField()
    arrivee = serializers.SerializerMethodField()
    distance_km = serializers.FloatField(
        read_only=True, allow_null=True, help_text="Par la route ; null si le routage a échoué."
    )

    class Meta:
        model = Trajet
        fields = [
            "id",
            "conducteur",
            "depart",
            "arrivee",
            "depart_le",
            "places_total",
            "places_restantes",
            "distance_km",
            "prix_place",
            "statut",
        ]
        read_only_fields = fields

    @extend_schema_field(LieuSerializer)
    def get_depart(self, trajet: Trajet) -> dict:
        return _lieu(trajet, "depart")

    @extend_schema_field(LieuSerializer)
    def get_arrivee(self, trajet: Trajet) -> dict:
        return _lieu(trajet, "arrivee")


class TrajetAdminDetailSerializer(TrajetAdminSerializer):
    vehicule = VehiculeResumeSerializer(read_only=True)
    points = PointSerializer(many=True, read_only=True)
    reservations = serializers.SerializerMethodField()

    class Meta(TrajetAdminSerializer.Meta):
        fields = [*TrajetAdminSerializer.Meta.fields, "vehicule", "points", "reservations"]
        read_only_fields = fields

    @extend_schema_field(ReservationAdminSerializer(many=True))
    def get_reservations(self, trajet: Trajet) -> list:
        return ReservationAdminSerializer(reservations_du_trajet_admin(trajet), many=True).data
