from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from apps.accounts.api.permissions import CONNECTE
from apps.accounts.services import get_utilisateur
from apps.confiance import services
from apps.confiance.api import serializers as s
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
