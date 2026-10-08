from django.conf import settings
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.core.api.reponses import succes


class SanteVue(APIView):
    """Vérifie que l'API répond (supervision, tests de fumée du mobile)."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["socle"],
        summary="État de l'API",
        responses=inline_serializer("Sante", {"version": serializers.CharField()}),
    )
    def get(self, request):
        version = settings.SPECTACULAR_SETTINGS["VERSION"]
        return succes("API Kovoit opérationnelle.", {"version": version})
