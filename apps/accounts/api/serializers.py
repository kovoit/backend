from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import ModeActif, User, valider_telephone
from apps.kyc.services import peut_publier, statuts_kyc


class DemandeOtpSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerificationOtpSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.RegexField(r"^\d{6}$", error_messages={"invalid": "Code à 6 chiffres."})


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class JetonsSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class UtilisateurResumeSerializer(serializers.Serializer):
    """Identité courte avec coordonnées : réservé aux vues du back-office."""

    id = serializers.UUIDField()
    email = serializers.EmailField()
    nom = serializers.CharField()
    prenom = serializers.CharField()
    telephone = serializers.CharField()


class AdminResumeSerializer(serializers.Serializer):
    """Administrateur ayant traité un dossier, un signalement ou modifié un paramètre."""

    id = serializers.UUIDField()
    nom = serializers.CharField()
    prenom = serializers.CharField()


class StatutsKycSerializer(serializers.Serializer):
    passager = serializers.CharField()
    conducteur = serializers.CharField()


class ProfilSerializer(serializers.ModelSerializer):
    kyc = serializers.SerializerMethodField()
    peut_publier = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "telephone",
            "nom",
            "prenom",
            "photo",
            "email_verifie",
            "mode_actif",
            "statut_compte",
            "suspendu_jusqu_au",
            "profil_complet",
            "kyc",
            "peut_publier",
        ]
        read_only_fields = fields

    @extend_schema_field(StatutsKycSerializer)
    def get_kyc(self, utilisateur: User) -> dict:
        return statuts_kyc(utilisateur)

    def get_peut_publier(self, utilisateur: User) -> bool:
        return peut_publier(utilisateur)


class ConnexionSerializer(serializers.Serializer):
    utilisateur = ProfilSerializer()
    nouveau_compte = serializers.BooleanField()
    access = serializers.CharField()
    refresh = serializers.CharField()


class ModificationProfilSerializer(serializers.Serializer):
    nom = serializers.CharField(max_length=100, required=False)
    prenom = serializers.CharField(max_length=100, required=False)
    telephone = serializers.CharField(max_length=16, required=False, validators=[valider_telephone])
    photo = serializers.ImageField(required=False)


class ModeSerializer(serializers.Serializer):
    mode_actif = serializers.ChoiceField(choices=ModeActif.choices)


class UtilisateurAdminSerializer(ProfilSerializer):
    class Meta(ProfilSerializer.Meta):
        fields = [*ProfilSerializer.Meta.fields, "is_staff", "cree_le", "last_login"]
        read_only_fields = fields
