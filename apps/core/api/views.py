from django.conf import settings
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.core.api.reponses import succes


class SanteVue(APIView):
    """État de l'API et de ses composants (supervision, tests de fumée du mobile) : 503 si l'un
    d'eux est en panne."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["socle"],
        summary="État de l'API",
        responses=inline_serializer(
            "Sante",
            {
                "version": serializers.CharField(),
                "composants": serializers.DictField(child=serializers.BooleanField()),
            },
        ),
    )
    def get(self, request):
        from apps.core.supervision import etat

        composants = etat()
        donnees = {"version": settings.SPECTACULAR_SETTINGS["VERSION"], "composants": composants}
        if all(composants.values()):
            return succes("API Kovoit opérationnelle.", donnees)
        en_panne = ", ".join(nom for nom, ok in composants.items() if not ok)
        return succes(f"Service dégradé : {en_panne}.", donnees, status=503)
