from rest_framework import serializers

from apps.accounts.api.serializers import UtilisateurResumeSerializer
from apps.portefeuille.models import MoyenPaiement, StatutTransaction, Transaction, TypeTransaction


class TransactionAdminSerializer(serializers.ModelSerializer):
    utilisateur = UtilisateurResumeSerializer()
    reservation_id = serializers.UUIDField(allow_null=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "cree_le",
            "type",
            "statut",
            "montant",
            "moyen_paiement",
            "telephone",
            "reference_externe",
            "reference_operateur",
            "reservation_id",
            "utilisateur",
        ]


class FiltresTransactionsSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=TypeTransaction.choices, required=False)
    statut = serializers.ChoiceField(choices=StatutTransaction.choices, required=False)
    moyen = serializers.ChoiceField(choices=MoyenPaiement.choices, required=False)
    recherche = serializers.CharField(required=False, max_length=100)
    du = serializers.DateField(required=False)
    au = serializers.DateField(required=False)


class VersementSerializer(serializers.Serializer):
    reference = serializers.CharField(
        min_length=3, max_length=64, help_text="Référence du transfert Flooz / Mixx effectué"
    )


class RefusRetraitSerializer(serializers.Serializer):
    motif = serializers.CharField(min_length=3, max_length=255)
