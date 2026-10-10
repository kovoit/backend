"""Réservations vues par le back-office. Le code de départ n'y figure JAMAIS."""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.api.serializers import UtilisateurResumeSerializer
from apps.confiance.services import signalements_de_reservation
from apps.reservations.models import Reservation, StatutReservation
from apps.reservations.transitions import HORODATAGES
from apps.trajets.api.serializers import PointSerializer


class ReservationAdminSerializer(serializers.ModelSerializer):
    trajet_id = serializers.UUIDField(read_only=True)
    passager = UtilisateurResumeSerializer(read_only=True)
    conducteur = UtilisateurResumeSerializer(source="trajet.conducteur", read_only=True)
    point_libelle = serializers.CharField(source="point.libelle", read_only=True)
    depart_le = serializers.DateTimeField(source="trajet.depart_le", read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id",
            "trajet_id",
            "passager",
            "conducteur",
            "point_libelle",
            "arrivee_libelle",
            "depart_le",
            "prix",
            "frais_service",
            "statut",
            "cree_le",
        ]
        read_only_fields = fields


class LieuArriveeSerializer(serializers.Serializer):
    lat = serializers.FloatField(source="arrivee_lat")
    lng = serializers.FloatField(source="arrivee_lng")
    libelle = serializers.CharField(source="arrivee_libelle")


class EtapeSerializer(serializers.Serializer):
    statut = serializers.ChoiceField(choices=StatutReservation.choices)
    le = serializers.DateTimeField()


class SignalementResumeSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    motif = serializers.CharField()
    statut = serializers.CharField()
    cree_le = serializers.DateTimeField()


def historique(reservation: Reservation) -> list[dict]:
    """Statuts atteints, du plus ancien au plus récent (demandée = date de création)."""
    etapes = [{"statut": StatutReservation.DEMANDEE, "le": reservation.cree_le}]
    for statut, champ in HORODATAGES.items():
        if date := getattr(reservation, champ):
            etapes.append({"statut": statut, "le": date})
    return sorted(etapes, key=lambda etape: etape["le"])


class ReservationAdminDetailSerializer(ReservationAdminSerializer):
    point = PointSerializer(read_only=True)
    arrivee = LieuArriveeSerializer(source="*", read_only=True)
    distance_km = serializers.FloatField(read_only=True, allow_null=True)
    historique = serializers.SerializerMethodField()
    signalements = serializers.SerializerMethodField()

    class Meta(ReservationAdminSerializer.Meta):
        fields = [
            *ReservationAdminSerializer.Meta.fields,
            "point",
            "arrivee",
            "distance_km",
            "annulation_tardive",
            "historique",
            "signalements",
        ]
        read_only_fields = fields

    @extend_schema_field(EtapeSerializer(many=True))
    def get_historique(self, reservation: Reservation) -> list:
        return EtapeSerializer(historique(reservation), many=True).data

    @extend_schema_field(SignalementResumeSerializer(many=True))
    def get_signalements(self, reservation: Reservation) -> list:
        signalements = signalements_de_reservation(reservation)
        return SignalementResumeSerializer(signalements, many=True).data
