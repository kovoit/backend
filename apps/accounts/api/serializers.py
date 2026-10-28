from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import ModeActif, User
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
    cgu_acceptees = serializers.SerializerMethodField(
        help_text="Faux : l'app demande d'accepter les CGU en vigueur avant tout autre écran"
    )
    cgu_url = serializers.SerializerMethodField()

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
            "cgu_acceptees",
            "cgu_url",
            "kyc",
            "etat",
        ]
        read_only_fields = fields

    def get_cgu_acceptees(self, utilisateur) -> bool:
        from apps.accounts.cgu import CGU_VERSION

        return utilisateur.cgu_version == CGU_VERSION

    def get_cgu_url(self, utilisateur) -> str:
        from apps.accounts.cgu import CGU_URL

        return CGU_URL

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
    # Lu et normalisé par le service (400 TELEPHONE_INVALIDE), pas rejeté ici
    telephone = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Mobile togolais : 8 chiffres commençant par 7 ou 9 ; espaces, tirets, points, "
        "parenthèses et +228 / 00228 / 228 facultatifs. "
        "Enregistré sous la forme +228XXXXXXXX.",
    )
    photo = serializers.ImageField(required=False)
    accepter_cgu = serializers.BooleanField(
        required=False, default=False, help_text="Vrai : accepte les CGU en vigueur"
    )


class ModeSerializer(serializers.Serializer):
    mode_actif = serializers.ChoiceField(choices=ModeActif.choices)


class UtilisateurAdminSerializer(ProfilSerializer):
    roles = serializers.SerializerMethodField(
        help_text="Rôles effectifs : moderation, finance, audit, parametres. Liste vide pour un "
        "admin sans rôle ; les quatre pour un superutilisateur."
    )

    class Meta(ProfilSerializer.Meta):
        fields = [*ProfilSerializer.Meta.fields, "is_staff", "roles", "cree_le", "last_login"]
        read_only_fields = fields

    def get_roles(self, utilisateur) -> list[str]:
        from apps.accounts.roles import roles_de

        return sorted(roles_de(utilisateur))
