from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.confiance.models import Note, Signalement
from apps.confiance.services import resume_confiance


class ConfianceSerializer(serializers.Serializer):
    note_moyenne = serializers.FloatField(allow_null=True)
    nombre_notes = serializers.IntegerField()
    fiabilite_pct = serializers.IntegerField()
    passager_verifie = serializers.BooleanField()
    conducteur_verifie = serializers.BooleanField()


class PersonneSerializer(serializers.Serializer):
    """Profil public : jamais d'email ni de téléphone."""

    id = serializers.UUIDField()
    prenom = serializers.CharField()
    nom = serializers.CharField()
    photo = serializers.ImageField()
    confiance = serializers.SerializerMethodField()

    @extend_schema_field(ConfianceSerializer)
    def get_confiance(self, utilisateur) -> dict:
        return resume_confiance(utilisateur)


class NoteEntreeSerializer(serializers.Serializer):
    note = serializers.IntegerField(min_value=1, max_value=5)
    commentaire = serializers.CharField(required=False, allow_blank=True, default="")


class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ["id", "reservation", "cible", "note", "commentaire", "cree_le"]


class SignalementEntreeSerializer(serializers.Serializer):
    motif = serializers.CharField()


class SignalementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Signalement
        fields = [
            "id",
            "reservation",
            "auteur",
            "cible",
            "motif",
            "statut",
            "resolution",
            "decision",
            "traite_le",
            "cree_le",
        ]
