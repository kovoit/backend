from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.views import APIView

from apps.accounts import services
from apps.accounts.api.admin_serializers import (
    ResultatSuspensionSerializer,
    SuspensionAdminSerializer,
    UtilisateurAdminDetailSerializer,
    UtilisateurAdminListeSerializer,
)
from apps.accounts.api.permissions import ADMIN
from apps.core.api.pagination import reponse_paginee
from apps.core.api.reponses import succes

TAG = "admin - utilisateurs"


class UtilisateurListeVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG],
        summary="Lister les utilisateurs (les plus récents d'abord)",
        parameters=[
            OpenApiParameter("recherche", str, description="Email, nom, prénom, téléphone"),
            OpenApiParameter("statut", str, enum=["actif", "suspendu"]),
        ],
        responses=UtilisateurAdminListeSerializer(many=True),
    )
    def get(self, request):
        utilisateurs = services.lister_utilisateurs(
            request.query_params.get("recherche"), request.query_params.get("statut")
        )
        return reponse_paginee(
            request, utilisateurs, UtilisateurAdminListeSerializer, "Utilisateurs récupérés.", self
        )


class UtilisateurDetailVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG],
        summary="Fiche d'un utilisateur (fiabilité, KYC, notes, véhicule)",
        responses=UtilisateurAdminDetailSerializer,
    )
    def get(self, request, pk):
        utilisateur = services.get_utilisateur(pk)
        return succes("Utilisateur récupéré.", UtilisateurAdminDetailSerializer(utilisateur).data)


class UtilisateurSuspendreVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG],
        summary="Suspendre un compte (motif obligatoire ; annule ses engagements à venir)",
        request=SuspensionAdminSerializer,
        responses=ResultatSuspensionSerializer,
    )
    def post(self, request, pk):
        entree = SuspensionAdminSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        resultat = services.suspendre_par_admin(
            services.get_utilisateur(pk),
            entree.validated_data["motif"],
            entree.validated_data.get("jours"),
        )
        return succes("Compte suspendu.", ResultatSuspensionSerializer(resultat).data)


class UtilisateurReactiverVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG],
        summary="Réactiver un compte",
        request=None,
        responses=UtilisateurAdminDetailSerializer,
    )
    def post(self, request, pk):
        utilisateur = services.reactiver(services.get_utilisateur(pk))
        return succes("Compte réactivé.", UtilisateurAdminDetailSerializer(utilisateur).data)
