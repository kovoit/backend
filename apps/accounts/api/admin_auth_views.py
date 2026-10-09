"""Authentification du back-office (admin React) : email + mot de passe.

Le refresh token n'est jamais renvoyé dans le corps : il est posé dans un cookie httpOnly,
limité aux URL /api/v1/auth/admin/, illisible par le JavaScript de la page.
"""

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts import services
from apps.accounts.api.permissions import ADMIN
from apps.accounts.api.serializers import UtilisateurAdminSerializer
from apps.core.api.reponses import succes

TAG = "admin - authentification"


class ConnexionAdminSerializer(serializers.Serializer):
    email = serializers.EmailField()
    mot_de_passe = serializers.CharField(trim_whitespace=False)


class SessionAdminSerializer(serializers.Serializer):
    access = serializers.CharField()
    utilisateur = UtilisateurAdminSerializer()


class AccesSerializer(serializers.Serializer):
    access = serializers.CharField()


def _poser_cookie(reponse, refresh: str):
    reponse.set_cookie(
        settings.ADMIN_REFRESH_COOKIE,
        refresh,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path=settings.ADMIN_REFRESH_COOKIE_PATH,
        secure=settings.ADMIN_REFRESH_COOKIE_SECURE,
        httponly=True,
        samesite="Lax",
    )
    return reponse


def _cookie(request) -> str | None:
    return request.COOKIES.get(settings.ADMIN_REFRESH_COOKIE)


class ConnexionAdminVue(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "connexion_admin"

    @extend_schema(
        tags=[TAG],
        summary="Se connecter au back-office (refresh posé en cookie httpOnly)",
        request=ConnexionAdminSerializer,
        responses=SessionAdminSerializer,
    )
    def post(self, request):
        entree = ConnexionAdminSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        session = services.connecter_admin(**entree.validated_data)
        donnees = {
            "access": session["access"],
            "utilisateur": UtilisateurAdminSerializer(session["utilisateur"]).data,
        }
        return _poser_cookie(succes("Connexion réussie.", donnees), session["refresh"])


class RafraichirAdminVue(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=[TAG],
        summary="Nouveau jeton d'accès à partir du cookie de session",
        request=None,
        responses=AccesSerializer,
    )
    def post(self, request):
        jetons = services.rafraichir_admin(_cookie(request))
        reponse = succes("Jeton renouvelé.", {"access": jetons["access"]})
        return _poser_cookie(reponse, jetons["refresh"])


class DeconnexionAdminVue(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=[TAG], summary="Se déconnecter du back-office", request=None, responses={200: None}
    )
    def post(self, request):
        services.deconnecter_admin(_cookie(request))
        reponse = succes("Déconnexion effectuée.")
        reponse.delete_cookie(
            settings.ADMIN_REFRESH_COOKIE, path=settings.ADMIN_REFRESH_COOKIE_PATH, samesite="Lax"
        )
        return reponse


class MoiAdminVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=[TAG], summary="Administrateur connecté", responses=UtilisateurAdminSerializer
    )
    def get(self, request):
        return succes("Profil récupéré.", UtilisateurAdminSerializer(request.user).data)
