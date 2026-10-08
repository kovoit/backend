from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.views import APIView

from apps.accounts.api.permissions import CONNECTE
from apps.core.api.pagination import reponse_paginee
from apps.core.api.reponses import succes
from apps.portefeuille import services
from apps.portefeuille.models import Transaction

TAG = "portefeuille (simulé)"


class SoldeSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    bloque = serializers.IntegerField()
    disponible = serializers.IntegerField()


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ["id", "type", "montant", "reservation", "reference_externe", "statut", "cree_le"]


class MontantSerializer(serializers.Serializer):
    montant = serializers.IntegerField(min_value=1, help_text="Montant en F CFA")


class PortefeuilleVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(tags=[TAG], summary="Solde du portefeuille", responses=SoldeSerializer)
    def get(self, request):
        return succes("Solde récupéré.", SoldeSerializer(services.solde(request.user)).data)


class TransactionsVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG], summary="Historique des mouvements", responses=TransactionSerializer(many=True)
    )
    def get(self, request):
        return reponse_paginee(
            request,
            services.historique(request.user),
            TransactionSerializer,
            "Historique récupéré.",
            self,
        )


class RechargerVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Recharger (Mobile Money simulé)",
        request=MontantSerializer,
        responses=SoldeSerializer,
    )
    def post(self, request):
        entree = MontantSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        solde = services.recharger(request.user, entree.validated_data["montant"])
        return succes("Recharge effectuée (simulation).", SoldeSerializer(solde).data)


class RetirerVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Retirer ses gains (simulé)",
        request=MontantSerializer,
        responses=SoldeSerializer,
    )
    def post(self, request):
        entree = MontantSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        solde = services.retirer(request.user, entree.validated_data["montant"])
        return succes("Retrait effectué (simulation).", SoldeSerializer(solde).data)
