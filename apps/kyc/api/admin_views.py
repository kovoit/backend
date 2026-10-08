from django.http import FileResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.views import APIView

from apps.accounts.api.permissions import ADMIN
from apps.core.api.pagination import reponse_paginee
from apps.core.api.reponses import succes
from apps.kyc import services
from apps.kyc.api.serializers import DossierAdminSerializer, RejetSerializer

TAG = "admin - kyc"


class DossierListeVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG],
        summary="Lister les dossiers KYC",
        parameters=[
            OpenApiParameter(
                "statut", str, enum=["non_verifie", "en_attente", "verifie", "rejete"]
            ),
            OpenApiParameter("type", str, enum=["passager", "conducteur"]),
        ],
        responses=DossierAdminSerializer(many=True),
    )
    def get(self, request):
        dossiers = services.lister_dossiers(
            request.query_params.get("statut"), request.query_params.get("type")
        )
        return reponse_paginee(
            request, dossiers, DossierAdminSerializer, "Dossiers récupérés.", self
        )


class DossierDetailVue(APIView):
    permission_classes = ADMIN

    @extend_schema(tags=[TAG], summary="Détail d'un dossier", responses=DossierAdminSerializer)
    def get(self, request, pk):
        dossier = services.get_dossier(pk)
        return succes("Dossier récupéré.", DossierAdminSerializer(dossier).data)


class DossierValiderVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG], summary="Valider un dossier", request=None, responses=DossierAdminSerializer
    )
    def post(self, request, pk):
        dossier = services.valider(pk, request.user)
        return succes("Dossier validé.", DossierAdminSerializer(dossier).data)


class DossierRejeterVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG],
        summary="Rejeter un dossier (motif obligatoire)",
        request=RejetSerializer,
        responses=DossierAdminSerializer,
    )
    def post(self, request, pk):
        entree = RejetSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        dossier = services.rejeter(pk, request.user, entree.validated_data["motif"])
        return succes("Dossier rejeté.", DossierAdminSerializer(dossier).data)


class PieceFichierVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG],
        summary="Télécharger une pièce (consultation journalisée)",
        responses={(200, "application/octet-stream"): OpenApiTypes.BINARY},
    )
    def get(self, request, pk):
        piece = services.consulter_piece(pk, request.user)
        return FileResponse(piece.fichier.open("rb"), as_attachment=False)
