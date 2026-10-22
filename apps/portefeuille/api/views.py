from django.conf import settings
from django.utils.crypto import constant_time_compare
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.accounts.api.permissions import CONNECTE
from apps.core.api.pagination import reponse_paginee
from apps.core.api.reponses import succes
from apps.portefeuille import services
from apps.portefeuille.api.serializers import (
    MoyenPaiementSerializer,
    OperationMobileMoneySerializer,
    ResultatOperationSerializer,
    SoldeSerializer,
    TransactionSerializer,
)

TAG = "portefeuille"
MESSAGES = {
    "validee": "Opération effectuée.",
    "en_attente": "Validez le paiement sur votre téléphone pour terminer l'opération.",
    "echouee": "Le paiement n'a pas abouti.",
}
MESSAGE_RETRAIT_EN_ATTENTE = (
    "Retrait enregistré : Kovoit effectue le versement sur votre compte Mobile Money."
)


def _resultat(request, ligne):
    """201 : opération validée ; 202 : en attente de confirmation Mobile Money."""
    donnees = {"transaction": ligne, "solde": services.solde(request.user)}
    statut = 201 if ligne.statut == "validee" else 202
    message = MESSAGES[ligne.statut]
    if ligne.type == "retrait" and ligne.statut == "en_attente":
        message = MESSAGE_RETRAIT_EN_ATTENTE
    return succes(message, ResultatOperationSerializer(donnees).data, status=statut)


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
        summary="Recharger par Flooz ou Mixx (PayGate, ou simulation sans jeton marchand)",
        request=OperationMobileMoneySerializer,
        responses={201: ResultatOperationSerializer, 202: ResultatOperationSerializer},
    )
    def post(self, request):
        entree = OperationMobileMoneySerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        return _resultat(request, services.recharger(request.user, **entree.validated_data))


class RetirerVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Retirer ses gains vers Flooz ou Mixx (versé manuellement avec PayGate)",
        request=OperationMobileMoneySerializer,
        responses={201: ResultatOperationSerializer, 202: ResultatOperationSerializer},
    )
    def post(self, request):
        entree = OperationMobileMoneySerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        return _resultat(request, services.retirer(request.user, **entree.validated_data))


class TransactionDetailVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="État d'une opération (une recharge en attente est revérifiée auprès de PayGate)",
        responses=TransactionSerializer,
    )
    def get(self, request, pk):
        ligne = services.verifier_paiement(request.user, pk)
        return succes(MESSAGES[ligne.statut], TransactionSerializer(ligne).data)


class CallbackPayGateVue(APIView):
    """Appelé par PayGate (sans compte Kovoit). Le contenu n'est pas cru : seule la référence
    sert à retrouver la recharge, dont le statut est revérifié auprès de PayGate."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(tags=[TAG], summary="Callback de confirmation PayGate", request=None,
                   responses={200: None})  # fmt: skip
    def post(self, request):
        secret = settings.PAYGATE_CALLBACK_SECRET
        if not secret or not constant_time_compare(request.query_params.get("cle", ""), secret):
            return succes("Notification ignorée.")
        identifiant = str(request.data.get("identifier", ""))
        if identifiant:
            services.confirmer_par_callback(identifiant)
        return succes("Notification reçue.")
