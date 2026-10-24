"""Mot de passe oublié du back-office : demande de lien, puis nouveau mot de passe."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts import services
from apps.core.api.reponses import succes

TAG = "admin - authentification"
MESSAGE_ENVOI = (
    "Si cette adresse correspond à un compte administrateur, un lien de réinitialisation "
    "vient d'y être envoyé."
)


class DemandeReinitialisationSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ReinitialisationSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=64)
    jeton = serializers.CharField(max_length=128)
    mot_de_passe = serializers.CharField(trim_whitespace=False, max_length=128)


class _Public(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "connexion_admin"  # 5/min, comme la connexion


class MotDePasseOublieVue(_Public):
    @extend_schema(
        tags=[TAG],
        summary="Mot de passe oublié : envoie un lien (même réponse que le compte existe ou non)",
        request=DemandeReinitialisationSerializer,
        responses={200: None},
    )
    def post(self, request):
        entree = DemandeReinitialisationSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        services.demander_reinitialisation(entree.validated_data["email"])
        return succes(MESSAGE_ENVOI)


class ReinitialiserMotDePasseVue(_Public):
    @extend_schema(
        tags=[TAG],
        summary="Choisir un nouveau mot de passe avec le lien reçu (400 LIEN_INVALIDE)",
        request=ReinitialisationSerializer,
        responses={200: None},
    )
    def post(self, request):
        entree = ReinitialisationSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        services.reinitialiser(**entree.validated_data)
        return succes("Mot de passe modifié. Connectez-vous avec votre nouveau mot de passe.")
