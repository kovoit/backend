"""Signalements et litiges vus par le back-office."""

from rest_framework import serializers

from apps.accounts.api.serializers import AdminResumeSerializer, UtilisateurResumeSerializer
from apps.confiance.models import DecisionLitige, Signalement
from apps.reservations.api.admin_serializers import ReservationAdminSerializer


class ReservationCourteSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    statut = serializers.CharField()
    trajet_id = serializers.UUIDField()


class SignalementAdminSerializer(serializers.ModelSerializer):
    reservation = ReservationCourteSerializer(read_only=True)
    auteur = UtilisateurResumeSerializer(read_only=True)
    cible = UtilisateurResumeSerializer(read_only=True)

    class Meta:
        model = Signalement
        fields = ["id", "reservation", "auteur", "cible", "motif", "statut", "cree_le"]
        read_only_fields = fields


class SignalementAdminDetailSerializer(SignalementAdminSerializer):
    reservation = ReservationAdminSerializer(read_only=True)
    traite_par = AdminResumeSerializer(read_only=True, allow_null=True)

    class Meta(SignalementAdminSerializer.Meta):
        fields = [
            *SignalementAdminSerializer.Meta.fields,
            "resolution",
            "decision",
            "traite_le",
            "traite_par",
        ]
        read_only_fields = fields


class TraitementAdminSerializer(serializers.Serializer):
    resolution = serializers.CharField(min_length=10, max_length=1000)
    decision = serializers.ChoiceField(
        choices=DecisionLitige.choices,
        required=False,
        allow_blank=True,
        default="",
        help_text="Obligatoire si la réservation est en litige.",
    )
