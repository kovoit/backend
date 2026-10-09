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
            "cree_le",
        ]


class OperationMobileMoneySerializer(serializers.Serializer):
    montant = serializers.IntegerField(min_value=1, help_text="Montant en F CFA")
    moyen = serializers.ChoiceField(choices=MoyenPaiement.choices, help_text="flooz ou mixx")


class MoyenPaiementSerializer(serializers.Serializer):
    code = serializers.ChoiceField(choices=MoyenPaiement.choices)
    libelle = serializers.CharField()


class ApercuPaiementSerializer(serializers.Serializer):
    """Bloc « paiement » de l'écran Détails du trajet & Réservation."""

    montant_total = serializers.IntegerField(help_text="Prix + frais de service (F CFA)")
    solde_disponible = serializers.IntegerField()
    complement_a_payer = serializers.IntegerField(
        help_text="À payer par Flooz ou Mixx à la réservation (0 si le solde suffit)"
    )
    moyens_paiement = MoyenPaiementSerializer(many=True)
