from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.views import APIView

from apps.accounts.api.permissions import ADMIN, CONNECTE
from apps.accounts.services import get_utilisateur
from apps.confiance import services
from apps.confiance.api import serializers as s
from apps.core.api.pagination import reponse_paginee
from apps.core.api.reponses import succes


class ProfilPublicVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=["profil"],
        summary="Profil public : vérification, note moyenne, fiabilité",
        responses=s.PersonneSerializer,
    )
    def get(self, request, pk):
        return succes("Profil récupéré.", s.PersonneSerializer(get_utilisateur(pk)).data)


class NoteVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=["réservations"],
        summary="Noter l'autre partie après le trajet (1 à 5)",
        request=s.NoteEntreeSerializer,
        responses={201: s.NoteSerializer},
    )
    def post(self, request, pk):
        entree = s.NoteEntreeSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        note = services.noter(request.user, pk, **entree.validated_data)
        return succes("Merci pour votre note.", s.NoteSerializer(note).data, 201)


class SignalementVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=["réservations"],
        summary="Signaler un problème (pendant ou après le trajet)",
        request=s.SignalementEntreeSerializer,
        responses={201: s.SignalementSerializer},
    )
    def post(self, request, pk):
        entree = s.SignalementEntreeSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        signalement = services.signaler(request.user, pk, entree.validated_data["motif"])
        return succes(
            "Signalement transmis à l'équipe Kovoit.",
            s.SignalementSerializer(signalement).data,
            201,
        )


class SignalementAdminListeVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=["admin - signalements"],
        summary="Lister les signalements et litiges",
        parameters=[OpenApiParameter("statut", str, enum=["ouvert", "traite"])],
        responses=s.SignalementSerializer(many=True),
    )
    def get(self, request):
        signalements = services.lister_signalements(request.query_params.get("statut"))
        return reponse_paginee(
            request, signalements, s.SignalementSerializer, "Signalements récupérés.", self
        )


class SignalementTraiterVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=["admin - signalements"],
        summary="Traiter un signalement (trancher un litige)",
        request=s.TraitementSerializer,
        responses=s.SignalementSerializer,
    )
    def post(self, request, pk):
        entree = s.TraitementSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        signalement = services.traiter_signalement(request.user, pk, **entree.validated_data)
        return succes("Signalement traité.", s.SignalementSerializer(signalement).data)
