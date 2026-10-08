from rest_framework import serializers

from apps.kyc.models import KycDossier, KycPiece, TypePiece
from apps.kyc.services import pieces_manquantes


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

    class Meta(DossierSerializer.Meta):
        fields = ["utilisateur", *DossierSerializer.Meta.fields]


class RejetSerializer(serializers.Serializer):
    motif = serializers.CharField()
