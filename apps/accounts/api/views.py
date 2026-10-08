from drf_spectacular.utils import extend_schema
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from apps.accounts import services
from apps.accounts.api import serializers as s
from apps.accounts.api.permissions import CONNECTE
from apps.core.api.reponses import succes
from apps.core.exceptions import ErreurMetier

TAG_AUTH = "authentification"
TAG_PROFIL = "profil"


class OtpDemandeVue(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=[TAG_AUTH],
        summary="Recevoir un code OTP par email",
        request=s.DemandeOtpSerializer,
        responses={200: None},
    )
    def post(self, request):
        entree = s.DemandeOtpSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        services.demander_otp(entree.validated_data["email"])
        return succes("Un code de connexion a été envoyé à votre adresse email.")


class OtpVerificationVue(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=[TAG_AUTH],
        summary="Vérifier le code OTP et se connecter (crée le compte si nouveau)",
        request=s.VerificationOtpSerializer,
        responses=s.ConnexionSerializer,
    )
    def post(self, request):
        entree = s.VerificationOtpSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        connexion = services.verifier_otp(**entree.validated_data)
        return succes("Connexion réussie.", s.ConnexionSerializer(connexion).data)


class JetonRafraichirVue(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=[TAG_AUTH],
        summary="Obtenir un nouveau jeton d'accès",
        request=s.RefreshSerializer,
        responses=s.JetonsSerializer,
    )
    def post(self, request):
        entree = TokenRefreshSerializer(data=request.data)
        try:
            entree.is_valid(raise_exception=True)
        except (TokenError, InvalidToken) as exc:  # expiré, invalide ou révoqué (déconnexion)
            raise ErreurMetier(
                "Session invalide ou expirée. Reconnectez-vous.",
                code="SESSION_EXPIREE",
                http_status=401,
            ) from exc
        return succes("Jeton renouvelé.", entree.validated_data)


class DeconnexionVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG_AUTH],
        summary="Se déconnecter",
        request=s.RefreshSerializer,
        responses={200: None},
    )
    def post(self, request):
        entree = s.RefreshSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        services.deconnecter(entree.validated_data["refresh"])
        return succes("Déconnexion effectuée.")


class MoiVue(APIView):
    permission_classes = CONNECTE
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @extend_schema(tags=[TAG_PROFIL], summary="Mon profil", responses=s.ProfilSerializer)
    def get(self, request):
        return succes("Profil récupéré.", s.ProfilSerializer(request.user).data)

    @extend_schema(
        tags=[TAG_PROFIL],
        summary="Modifier mon profil",
        request=s.ModificationProfilSerializer,
        responses=s.ProfilSerializer,
    )
    def patch(self, request):
        entree = s.ModificationProfilSerializer(data=request.data, partial=True)
        entree.is_valid(raise_exception=True)
        utilisateur = services.modifier_profil(request.user, **entree.validated_data)
        return succes("Profil mis à jour.", s.ProfilSerializer(utilisateur).data)


class MoiModeVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG_PROFIL],
        summary="Basculer entre mode passager et conducteur",
        request=s.ModeSerializer,
        responses=s.ProfilSerializer,
    )
    def patch(self, request):
        entree = s.ModeSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        utilisateur = services.changer_mode(request.user, entree.validated_data["mode_actif"])
        return succes("Mode mis à jour.", s.ProfilSerializer(utilisateur).data)
