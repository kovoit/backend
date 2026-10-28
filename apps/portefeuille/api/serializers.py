from rest_framework import serializers

from apps.portefeuille.models import MoyenPaiement, Transaction


class SoldeSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    bloque = serializers.IntegerField()
    disponible = serializers.IntegerField()


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            "id",
            "type",
            "montant",
            "moyen_paiement",
            "reservation",
            "reference_externe",
            "statut",
            "telephone",
            "cree_le",
        ]


class OperationMobileMoneySerializer(serializers.Serializer):
    montant = serializers.IntegerField(min_value=1, help_text="Montant en F CFA")
    moyen = serializers.ChoiceField(choices=MoyenPaiement.choices, help_text="flooz ou mixx")
    # Lu par le service (apps/core/telephone.py) : 400 TELEPHONE_INVALIDE, pas rejeté ici
    telephone = serializers.CharField(
        required=False,
        default="",
        allow_blank=True,
        help_text="Numéro Mobile Money togolais : 8 chiffres commençant par 7 ou 9, "
        "+228 facultatif (par défaut : téléphone du profil)",
    )


class ResultatOperationSerializer(serializers.Serializer):
    """Statut `en_attente` : le client valide le paiement sur son téléphone ; l'app interroge
    ensuite GET portefeuille/transactions/{id}/ jusqu'à `validee` ou `echouee`."""

    transaction = TransactionSerializer()
    solde = SoldeSerializer()


class MoyenPaiementSerializer(serializers.Serializer):
    code = serializers.ChoiceField(choices=MoyenPaiement.choices)
    libelle = serializers.CharField()


class ApercuPaiementSerializer(serializers.Serializer):
    """Bloc « paiement » de l'écran Détails du trajet & Réservation."""

    montant_total = serializers.IntegerField(help_text="Prix + frais de service (F CFA)")
    solde_disponible = serializers.IntegerField()
    complement_a_payer = serializers.IntegerField(
        help_text="Manque sur le portefeuille pour réserver (0 si le solde suffit)"
    )
    recharge_suggeree = serializers.IntegerField(
        help_text="Montant de recharge à proposer : le complément, au moins recharge_min"
    )
    moyens_paiement = MoyenPaiementSerializer(many=True)
