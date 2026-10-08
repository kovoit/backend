from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.views import APIView

from apps.accounts import services
from apps.accounts.api.permissions import ADMIN
from apps.accounts.api.serializers import SuspensionSerializer, UtilisateurAdminSerializer
from apps.core.api.pagination import reponse_paginee
from apps.core.api.reponses import succes

TAG = "admin - utilisateurs"


class UtilisateurListeVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG],
        summary="Lister les utilisateurs",
        parameters=[
            OpenApiParameter("recherche", str, description="Email, nom, prénom, téléphone"),
            OpenApiParameter("statut", str, enum=["actif", "suspendu"]),
        ],
        responses=UtilisateurAdminSerializer(many=True),
    )
    def get(self, request):
        utilisateurs = services.lister_utilisateurs(
            request.query_params.get("recherche"), request.query_params.get("statut")
        )
        return reponse_paginee(
            request, utilisateurs, UtilisateurAdminSerializer, "Utilisateurs récupérés.", self
        )


class UtilisateurDetailVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG], summary="Détail d'un utilisateur", responses=UtilisateurAdminSerializer
    )
    def get(self, request, pk):
        utilisateur = services.get_utilisateur(pk)
        return succes("Utilisateur récupéré.", UtilisateurAdminSerializer(utilisateur).data)


class UtilisateurSuspendreVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG],
        summary="Suspendre un compte (annule ses engagements à venir)",
        request=SuspensionSerializer,
        responses=UtilisateurAdminSerializer,
    )
    def post(self, request, pk):
        entree = SuspensionSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        utilisateur = services.suspendre(
            services.get_utilisateur(pk), entree.validated_data.get("jours")
        )
        return succes("Compte suspendu.", UtilisateurAdminSerializer(utilisateur).data)


class UtilisateurReactiverVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG],
        summary="Réactiver un compte",
        request=None,
        responses=UtilisateurAdminSerializer,
    )
    def post(self, request, pk):
        utilisateur = services.reactiver(services.get_utilisateur(pk))
        return succes("Compte réactivé.", UtilisateurAdminSerializer(utilisateur).data)
