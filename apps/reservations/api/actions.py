"""Actions métier sur une réservation : un endpoint POST par transition."""

from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from apps.accounts.api.permissions import CONNECTE
from apps.core.api.reponses import succes
from apps.reservations import services
from apps.reservations.api import serializers as s

TAG = "réservations"


class AccepterVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Accepter une demande (conducteur)",
        request=None,
        responses=s.ReservationConducteurSerializer,
    )
    def post(self, request, pk):
        reservation = services.accepter(request.user, pk)
        return succes("Réservation acceptée.", s.ReservationConducteurSerializer(reservation).data)


class RefuserVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Refuser une demande (conducteur)",
        request=None,
        responses=s.ReservationConducteurSerializer,
    )
    def post(self, request, pk):
        reservation = services.refuser(request.user, pk)
        return succes("Réservation refusée.", s.ReservationConducteurSerializer(reservation).data)


class AnnulerVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Annuler (passager ou conducteur, avant le départ)",
        request=None,
        responses=s.ReservationConducteurSerializer,
    )
    def post(self, request, pk):
        reservation = services.annuler(request.user, pk)
        message = "Réservation annulée."
        if reservation.annulation_tardive:
            message += " Annulation tardive : elle compte dans votre taux de fiabilité."
        return succes(message, s.serialiser_pour(request.user, reservation))


class CodeDepartVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Saisir le code de départ donné par le passager (conducteur)",
        request=s.CodeDepartSerializer,
        responses=s.ReservationConducteurSerializer,
    )
    def post(self, request, pk):
        entree = s.CodeDepartSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        reservation = services.saisir_code(request.user, pk, entree.validated_data["code"])
        return succes(
            "Passager à bord : trajet en cours.",
            s.ReservationConducteurSerializer(reservation).data,
        )


class AbsentVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Déclarer le passager absent (position GPS du conducteur)",
        request=s.AbsenceSerializer,
        responses=s.ReservationConducteurSerializer,
    )
    def post(self, request, pk):
        entree = s.AbsenceSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        reservation = services.declarer_absent(request.user, pk, **entree.validated_data)
        return succes("Absence enregistrée.", s.ReservationConducteurSerializer(reservation).data)


class ConfirmerArriveeVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Confirmer l'arrivée (passager)",
        request=None,
        responses=s.ReservationPassagerSerializer,
    )
    def post(self, request, pk):
        reservation = services.confirmer_arrivee(request.user, pk)
        return succes(
            "Arrivée confirmée. Merci d'avoir voyagé avec Kovoit !",
            s.ReservationPassagerSerializer(reservation).data,
        )
