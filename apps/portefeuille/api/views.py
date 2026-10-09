from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from apps.accounts.api.permissions import CONNECTE
from apps.core.api.pagination import reponse_paginee
from apps.core.api.reponses import succes
from apps.portefeuille import services
from apps.portefeuille.api.serializers import (
    MoyenPaiementSerializer,
    OperationMobileMoneySerializer,
    SoldeSerializer,
    TransactionSerializer,
)

TAG = "portefeuille (simulé)"


class PortefeuilleVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(tags=[TAG], summary="Solde du portefeuille", responses=SoldeSerializer)
    def get(self, request):
        return succes("Solde récupéré.", SoldeSerializer(services.solde(request.user)).data)


class MoyensPaiementVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Moyens de paiement Mobile Money (Flooz, Mixx)",
        responses=MoyenPaiementSerializer(many=True),
    )
    def get(self, request):
        moyens = MoyenPaiementSerializer(services.moyens_paiement(), many=True).data
        return succes("Moyens de paiement disponibles.", moyens)


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
        summary="Recharger par Flooz ou Mixx (simulé)",
        request=OperationMobileMoneySerializer,
        responses=SoldeSerializer,
    )
    def post(self, request):
        entree = OperationMobileMoneySerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        solde = services.recharger(request.user, **entree.validated_data)
        return succes("Recharge effectuée (simulation).", SoldeSerializer(solde).data)


class RetirerVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Retirer ses gains vers Flooz ou Mixx (simulé)",
        request=OperationMobileMoneySerializer,
        responses=SoldeSerializer,
    )
    def post(self, request):
        entree = OperationMobileMoneySerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        solde = services.retirer(request.user, **entree.validated_data)
        return succes("Retrait effectué (simulation).", SoldeSerializer(solde).data)
