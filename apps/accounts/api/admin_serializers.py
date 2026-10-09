"""Utilisateurs vus par le back-office : liste (avec fiabilité) et fiche complète."""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.api.serializers import StatutsKycSerializer, UtilisateurAdminSerializer
from apps.accounts.models import User
from apps.confiance.services import dernieres_notes, detail_fiabilite, resume_confiance
from apps.kyc.services import dossiers_soumis, statuts_kyc
from apps.vehicules.api.serializers import VehiculeResumeSerializer
from apps.vehicules.services import mes_vehicules


class FiabiliteSerializer(serializers.Serializer):
    pct = serializers.IntegerField(allow_null=True, help_text="Null : aucune réservation.")
    periode_j = serializers.IntegerField()
    reservations = serializers.IntegerField()
    annulations_tardives = serializers.IntegerField()
    absences = serializers.IntegerField()


class DossierResumeSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    type = serializers.CharField()
    statut = serializers.CharField()
    soumis_le = serializers.DateTimeField(allow_null=True)
    traite_le = serializers.DateTimeField(allow_null=True)
    motif_rejet = serializers.CharField()


class AuteurSerializer(serializers.Serializer):
    prenom = serializers.CharField()
    nom = serializers.CharField()


class NoteRecueSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    note = serializers.IntegerField()
    commentaire = serializers.CharField()
    auteur = AuteurSerializer()
    cree_le = serializers.DateTimeField()


class UtilisateurAdminListeSerializer(serializers.ModelSerializer):
    kyc = serializers.SerializerMethodField()
    fiabilite_pct = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "telephone",
            "nom",
            "prenom",
            "statut_compte",
            "kyc",
            "fiabilite_pct",
            "cree_le",
        ]
        read_only_fields = fields

    @extend_schema_field(StatutsKycSerializer)
    def get_kyc(self, utilisateur: User) -> dict:
        return statuts_kyc(utilisateur)

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_fiabilite_pct(self, utilisateur: User) -> int | None:
        return detail_fiabilite(utilisateur)["pct"]


class UtilisateurAdminDetailSerializer(UtilisateurAdminSerializer):
    fiabilite = serializers.SerializerMethodField()
    note_moyenne = serializers.SerializerMethodField()
    nombre_notes = serializers.SerializerMethodField()
    dossiers_kyc = serializers.SerializerMethodField()
    notes_recues = serializers.SerializerMethodField()
    vehicule = serializers.SerializerMethodField()

    class Meta(UtilisateurAdminSerializer.Meta):
        fields = [
            *UtilisateurAdminSerializer.Meta.fields,
            "motif_suspension",
            "fiabilite",
            "note_moyenne",
            "nombre_notes",
            "dossiers_kyc",
            "notes_recues",
            "vehicule",
        ]
        read_only_fields = fields

    @extend_schema_field(FiabiliteSerializer)
    def get_fiabilite(self, utilisateur: User) -> dict:
        return detail_fiabilite(utilisateur)

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_note_moyenne(self, utilisateur: User) -> float | None:
        return resume_confiance(utilisateur)["note_moyenne"]

    def get_nombre_notes(self, utilisateur: User) -> int:
        return resume_confiance(utilisateur)["nombre_notes"]

    @extend_schema_field(DossierResumeSerializer(many=True))
    def get_dossiers_kyc(self, utilisateur: User) -> list:
        return DossierResumeSerializer(dossiers_soumis(utilisateur), many=True).data

    @extend_schema_field(NoteRecueSerializer(many=True))
    def get_notes_recues(self, utilisateur: User) -> list:
        return NoteRecueSerializer(dernieres_notes(utilisateur), many=True).data

    @extend_schema_field(VehiculeResumeSerializer(allow_null=True))
    def get_vehicule(self, utilisateur: User) -> dict | None:
        vehicule = mes_vehicules(utilisateur).first()
        return VehiculeResumeSerializer(vehicule).data if vehicule else None


class SuspensionAdminSerializer(serializers.Serializer):
    motif = serializers.CharField(min_length=10, max_length=500)
    jours = serializers.IntegerField(
        min_value=1, required=False, allow_null=True, help_text="Vide : jusqu'à réactivation."
    )


class ResultatSuspensionSerializer(serializers.Serializer):
    utilisateur = UtilisateurAdminDetailSerializer()
    reservations_annulees = serializers.IntegerField()
