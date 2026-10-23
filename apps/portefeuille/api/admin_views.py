from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.views import APIView

from apps.accounts.api.permissions import ADMIN
from apps.core.api.pagination import reponse_paginee
from apps.core.api.reponses import succes
from apps.portefeuille import services
from apps.portefeuille.api.admin_serializers import (
    FiltresTransactionsSerializer,
    RefusRetraitSerializer,
    TransactionAdminSerializer,
    VersementSerializer,
)

TAG = "admin - transactions"


class TransactionAdminListeVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG],
        summary="Journal des transactions (retraits en attente : les plus anciens d'abord)",
        parameters=[
            FiltresTransactionsSerializer,
            OpenApiParameter("page", int),
            OpenApiParameter("taille", int),
        ],
        responses=TransactionAdminSerializer(many=True),
    )
    def get(self, request):
        filtres = FiltresTransactionsSerializer(data=request.query_params)
        filtres.is_valid(raise_exception=True)
        donnees = dict(filtres.validated_data)
        donnees["type_"] = donnees.pop("type", None)
        transactions = services.lister_transactions(**donnees)
        return reponse_paginee(
            request, transactions, TransactionAdminSerializer, "Transactions récupérées.", self
        )


class RetraitVerserVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG],
        summary="Retrait versé sur Flooz / Mixx (référence du transfert obligatoire)",
        request=VersementSerializer,
        responses=TransactionAdminSerializer,
    )
    def post(self, request, pk):
        entree = VersementSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        services.traiter_retrait(request.user, pk, verse=True, **entree.validated_data)
        ligne = services.get_transaction(pk)
        return succes("Retrait marqué comme versé.", TransactionAdminSerializer(ligne).data)


class RetraitRefuserVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG],
        summary="Refuser un retrait (motif obligatoire ; le montant redevient disponible)",
        request=RefusRetraitSerializer,
        responses=TransactionAdminSerializer,
    )
    def post(self, request, pk):
        entree = RefusRetraitSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        services.traiter_retrait(request.user, pk, verse=False, **entree.validated_data)
        ligne = services.get_transaction(pk)
        return succes("Retrait refusé.", TransactionAdminSerializer(ligne).data)
