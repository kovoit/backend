from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.api.serializers import AdminResumeSerializer
from apps.kyc.models import KycDossier, KycPiece, TypeDossier, TypePiece
from apps.kyc.services import pieces_manquantes
from apps.vehicules.api.serializers import VehiculeResumeSerializer
from apps.vehicules.services import mes_vehicules


class PieceSerializer(serializers.ModelSerializer):
    class Meta:
        model = KycPiece
        fields = ["id", "type_piece", "cree_le"]


class DossierSerializer(serializers.ModelSerializer):
    pieces = PieceSerializer(many=True, read_only=True)
    pieces_manquantes = serializers.SerializerMethodField()

    class Meta:
        model = KycDossier
        fields = [
            "id",
            "type",
            "statut",
            "motif_rejet",
            "soumis_le",
            "traite_le",
            "pieces",
            "pieces_manquantes",
        ]

    def get_pieces_manquantes(self, dossier: KycDossier) -> list[str]:
        return pieces_manquantes(dossier)


class AjoutPieceSerializer(serializers.Serializer):
    type_piece = serializers.ChoiceField(choices=TypePiece.choices)
    fichier = serializers.FileField()


class DemandeurSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    nom = serializers.CharField()
    prenom = serializers.CharField()
    telephone = serializers.CharField()


class DossierAdminSerializer(DossierSerializer):
    utilisateur = DemandeurSerializer(read_only=True)
    traite_par = AdminResumeSerializer(read_only=True, allow_null=True)
    vehicule = serializers.SerializerMethodField(
        help_text="Véhicule déclaré : dossier conducteur uniquement, sinon null."
    )

    class Meta(DossierSerializer.Meta):
        fields = ["utilisateur", *DossierSerializer.Meta.fields, "traite_par", "vehicule"]

    @extend_schema_field(VehiculeResumeSerializer(allow_null=True))
    def get_vehicule(self, dossier: KycDossier) -> dict | None:
        if dossier.type != TypeDossier.CONDUCTEUR:
            return None
        vehicule = mes_vehicules(dossier.utilisateur).first()
        return VehiculeResumeSerializer(vehicule).data if vehicule else None


class RejetSerializer(serializers.Serializer):
    motif = serializers.CharField(
        min_length=10, max_length=500, help_text="Communiqué au demandeur."
    )
