from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from apps.accounts.api.permissions import CONNECTE, CompteActif
from apps.core.api.pagination import reponse_paginee
from apps.core.api.reponses import succes
from apps.kyc.api.permissions import PeutPublier
from apps.trajets import services
from apps.trajets.api import serializers as s

TAG = "trajets"


class PublierVue(APIView):
    permission_classes = [*CONNECTE, CompteActif, PeutPublier]

    @extend_schema(
        tags=[TAG],
        summary="Publier un trajet (prix par place fixé par Kovoit)",
        request=s.PublicationSerializer,
        responses={201: s.TrajetConducteurSerializer},
    )
    def post(self, request):
        entree = s.PublicationSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        trajet = services.publier(request.user, **entree.validated_data)
        return succes("Trajet publié.", s.TrajetConducteurSerializer(trajet).data, 201)


class RechercheVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Rechercher un trajet (départ, arrivée, date et heure)",
        parameters=[s.RechercheSerializer],
        responses=s.ResultatRechercheSerializer(many=True),
    )
    def get(self, request):
        entree = s.RechercheSerializer(data=request.query_params)
        entree.is_valid(raise_exception=True)
        resultats = services.rechercher(request.user, **entree.validated_data)
        message = f"{len(resultats)} trajet(s) trouvé(s)."
        return succes(message, s.ResultatRechercheSerializer(resultats, many=True).data)


class MesTrajetsVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Mes trajets publiés (conducteur)",
        responses=s.TrajetConducteurSerializer(many=True),
    )
    def get(self, request):
        trajets = services.mes_trajets(request.user)
        return reponse_paginee(
            request, trajets, s.TrajetConducteurSerializer, "Trajets récupérés.", self
        )


class TrajetDetailVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Détail d'un trajet + aperçu du paiement (portefeuille, complément Flooz/Mixx)",
        responses=s.TrajetDetailSerializer,
    )
    def get(self, request, pk):
        trajet = services.get_trajet(pk)
        donnees = s.TrajetDetailSerializer(trajet, context={"utilisateur": request.user}).data
        return succes("Trajet récupéré.", donnees)


class PositionVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Envoyer sa position GPS (partage de trajet)",
        request=s.PositionSerializer,
        responses=s.TrajetConducteurSerializer,
    )
    def post(self, request, pk):
        entree = s.PositionSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        trajet = services.mettre_a_jour_position(request.user, pk, **entree.validated_data)
        return succes("Position enregistrée.", s.TrajetConducteurSerializer(trajet).data)


class TerminerVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Terminer le trajet",
        request=None,
        responses=s.TrajetConducteurSerializer,
    )
    def post(self, request, pk):
        trajet = services.terminer(request.user, pk)
        return succes("Trajet terminé.", s.TrajetConducteurSerializer(trajet).data)


class AnnulerVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=[TAG],
        summary="Annuler le trajet (avant le départ)",
        request=None,
        responses=s.TrajetConducteurSerializer,
    )
    def post(self, request, pk):
        trajet = services.annuler(request.user, pk)
        return succes("Trajet annulé.", s.TrajetConducteurSerializer(trajet).data)
