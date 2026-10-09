from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import ModeActif, User, valider_telephone
from apps.accounts.services import etat_profil
from apps.kyc.services import statuts_kyc


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


class StatutsKycSerializer(serializers.Serializer):
    passager = serializers.CharField()
    conducteur = serializers.CharField()


class AlerteSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    action_requise = serializers.BooleanField()


class AccesSerializer(serializers.Serializer):
    peut_rechercher = serializers.BooleanField()
    peut_reserver = serializers.BooleanField()
    peut_publier = serializers.BooleanField()


class ModeConducteurSerializer(serializers.Serializer):
    disponible = serializers.BooleanField()
    kyc_conducteur_verifie = serializers.BooleanField()
    vehicule_declare = serializers.BooleanField()


class EtatProfilSerializer(serializers.Serializer):
    badge_kyc = serializers.BooleanField(help_text="Afficher le macaron orange sur le profil")
    acces = AccesSerializer()
    mode_conducteur = ModeConducteurSerializer()
    alertes = AlerteSerializer(many=True)


class ProfilSerializer(serializers.ModelSerializer):
    kyc = serializers.SerializerMethodField()
    etat = serializers.SerializerMethodField()

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
            "etat",
        ]
        read_only_fields = fields

    @extend_schema_field(StatutsKycSerializer)
    def get_kyc(self, utilisateur: User) -> dict:
        return statuts_kyc(utilisateur)

    @extend_schema_field(EtatProfilSerializer)
    def get_etat(self, utilisateur: User) -> dict:
        return etat_profil(utilisateur)


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


class SuspensionSerializer(serializers.Serializer):
    jours = serializers.IntegerField(
        min_value=1, required=False, help_text="Durée en jours. Vide : sans limite."
    )
