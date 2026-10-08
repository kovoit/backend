from drf_spectacular.utils import extend_schema
from rest_framework.parsers import MultiPartParser
from rest_framework.views import APIView

from apps.accounts.api.permissions import CONNECTE
from apps.core.api.reponses import succes
from apps.kyc import services
from apps.kyc.api.serializers import AjoutPieceSerializer, DossierSerializer

TAG = "kyc"


class MesDossiersVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Mes dossiers KYC (passager et conducteur)",
        responses=DossierSerializer(many=True),
    )
    def get(self, request):
        dossiers = services.mes_dossiers(request.user)
        return succes("Dossiers récupérés.", DossierSerializer(dossiers, many=True).data)


class PieceVue(APIView):
    permission_classes = CONNECTE
    parser_classes = [MultiPartParser]

    @extend_schema(
        tags=[TAG],
        summary="Envoyer une pièce (multipart : type_piece + fichier)",
        request={"multipart/form-data": AjoutPieceSerializer},
        responses={201: DossierSerializer},
    )
    def post(self, request, type_dossier: str):
        entree = AjoutPieceSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        dossier = services.ajouter_piece(request.user, type_dossier, **entree.validated_data)
        return succes("Pièce enregistrée.", DossierSerializer(dossier).data, 201)


class SoumettreVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Soumettre le dossier à vérification",
        request=None,
        responses=DossierSerializer,
    )
    def post(self, request, type_dossier: str):
        dossier = services.soumettre(request.user, type_dossier)
        return succes(
            "Dossier soumis : il sera vérifié par notre équipe.", DossierSerializer(dossier).data
        )
