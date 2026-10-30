"""Entrées et sorties des routes de connexion de l'application (`auth/…`, F-070 à F-073)."""

from rest_framework import serializers

AIDE_TELEPHONE = (
    "Mobile togolais : 8 chiffres commençant par 7 ou 9, +228 facultatif. "
    "Enregistré sous la forme +228XXXXXXXX (400 TELEPHONE_INVALIDE sinon)."
)


def _mot_de_passe(**options) -> serializers.CharField:
    return serializers.CharField(
        max_length=128, trim_whitespace=False, style={"input_type": "password"}, **options
    )


def _code() -> serializers.RegexField:
    return serializers.RegexField(r"^\d{6}$", error_messages={"invalid": "Code à 6 chiffres."})


class InscriptionSerializer(serializers.Serializer):
    prenom = serializers.CharField(max_length=100)
    nom = serializers.CharField(max_length=100)
    email = serializers.EmailField(max_length=254, help_text="Mis en minuscules par le serveur")
    # Lu et normalisé par le service (400 TELEPHONE_INVALIDE), pas rejeté ici
    telephone = serializers.CharField(help_text=AIDE_TELEPHONE)
    mot_de_passe = _mot_de_passe(
        help_text="Validateurs Django : 8 caractères minimum, pas trop courant, pas entièrement "
        "numérique, pas trop proche du prénom, du nom ou de l'e-mail (400 MOT_DE_PASSE_FAIBLE)"
    )
    cgu_acceptees = serializers.BooleanField(
        help_text="Doit valoir true : acceptation des CGU en vigueur"
    )

    def validate_cgu_acceptees(self, valeur: bool) -> bool:
        if valeur is not True:
            raise serializers.ValidationError("Acceptez les conditions d'utilisation.")
        return valeur


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)


class VerificationEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    code = _code()


class ConnexionApplicationSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    mot_de_passe = _mot_de_passe()


class ReinitialisationParCodeSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    code = _code()
    mot_de_passe = _mot_de_passe(help_text="Nouveau mot de passe (mêmes validateurs)")


class CodeEnvoyeSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    delai_renvoi_s = serializers.IntegerField(
        help_text="Secondes avant de pouvoir demander un nouveau code (otp_delai_renvoi_s)"
    )
