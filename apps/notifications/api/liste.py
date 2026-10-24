"""Écran « Notifications » de l'app : liste, nombre de non lues, marquer comme lue(s)."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.views import APIView

from apps.accounts.api.permissions import CONNECTE
from apps.core.api.pagination import reponse_paginee
from apps.core.api.reponses import succes
from apps.notifications import services
from apps.notifications.models import Notification

TAG = "notifications"


class NotificationSerializer(serializers.ModelSerializer):
    donnees = serializers.DictField(
        child=serializers.CharField(),
        help_text="Écran à ouvrir : reservation_id, trajet_id, destinataire",
    )

    class Meta:
        model = Notification
        fields = ["id", "titre", "message", "donnees", "lue_le", "cree_le"]


class NonLuesSerializer(serializers.Serializer):
    nombre = serializers.IntegerField()


class NotificationListeVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Mes notifications (les plus récentes d'abord)",
        responses=NotificationSerializer(many=True),
    )
    def get(self, request):
        return reponse_paginee(
            request,
            services.mes_notifications(request.user),
            NotificationSerializer,
            "Notifications récupérées.",
            self,
        )


class NonLuesVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG], summary="Nombre de notifications non lues", responses=NonLuesSerializer
    )
    def get(self, request):
        return succes("Non lues.", {"nombre": services.nombre_non_lues(request.user)})


class MarquerLueVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG], summary="Marquer une notification comme lue", request=None,
        responses=NotificationSerializer,
    )  # fmt: skip
    def post(self, request, pk):
        notification = services.marquer_lue(request.user, pk)
        return succes("Notification lue.", NotificationSerializer(notification).data)


class ToutLireVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG], summary="Tout marquer comme lu", request=None, responses=NonLuesSerializer
    )
    def post(self, request):
        services.tout_marquer_lu(request.user)
        return succes("Tout est lu.", {"nombre": 0})
