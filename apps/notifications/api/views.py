from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.views import APIView

from apps.accounts.api.permissions import CONNECTE
from apps.core.api.reponses import succes
from apps.notifications import services
from apps.notifications.models import AppareilNotification

TAG = "notifications"


class AppareilSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppareilNotification
        fields = ["id", "jeton", "plateforme", "cree_le"]
        read_only_fields = ["id", "cree_le"]


class AppareilListeVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Enregistrer le jeton push (FCM) du téléphone",
        request=AppareilSerializer,
        responses={201: AppareilSerializer},
    )
    def post(self, request):
        entree = AppareilSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        appareil = services.enregistrer_appareil(request.user, **entree.validated_data)
        return succes(
            "Appareil enregistré.", AppareilSerializer(appareil).data, status.HTTP_201_CREATED
        )


class AppareilDetailVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(tags=[TAG], summary="Retirer un appareil", responses={200: None})
    def delete(self, request, jeton: str):
        services.retirer_appareil(request.user, jeton)
        return succes("Appareil retiré.")
