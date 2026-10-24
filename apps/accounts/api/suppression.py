"""Suppression du compte depuis l'application (Profil → Supprimer mon compte)."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.views import APIView

from apps.accounts import services
from apps.accounts.api.permissions import CONNECTE
from apps.core.api.reponses import succes


class SuppressionSerializer(serializers.Serializer):
    confirmation = serializers.CharField(max_length=20, help_text="Saisir SUPPRIMER")


class SupprimerCompteVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=["profil"],
        summary="Supprimer mon compte (anonymisé ; 409 SUPPRESSION_IMPOSSIBLE si engagement ou "
        "argent en cours)",
        request=SuppressionSerializer,
        responses={200: None},
    )
    def post(self, request):
        entree = SuppressionSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        services.supprimer_compte(request.user, entree.validated_data["confirmation"])
        return succes("Votre compte a été supprimé.")
