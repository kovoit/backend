"""API du journal d'audit (admin React). Lecture seule : aucune route ne modifie le journal."""

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from apps.accounts.api.permissions import ADMIN_AUDIT
from apps.audit import services
from apps.audit.api.serializers import (
    EvenementSerializer,
    FiltresSerializer,
    FluxEntreeSerializer,
    FluxSerializer,
    StatsEntreeSerializer,
    StatsSerializer,
)
from apps.core.api.pagination import reponse_paginee
from apps.core.api.reponses import succes
from apps.dashboard.services import bornes

TAG = "admin - audit"


def _valider(serializer_class, request) -> dict:
    entree = serializer_class(data=request.query_params)
    entree.is_valid(raise_exception=True)
    return entree.validated_data


class EvenementListeVue(APIView):
    permission_classes = ADMIN_AUDIT

    @extend_schema(
        tags=[TAG],
        summary="Lister les événements (plus récents d'abord, filtres combinables)",
        parameters=[FiltresSerializer],
        responses=EvenementSerializer(many=True),
    )
    def get(self, request):
        evenements = services.lister_evenements(_valider(FiltresSerializer, request))
        return reponse_paginee(
            request, evenements, EvenementSerializer, "Événements récupérés.", self
        )


class EvenementDetailVue(APIView):
    permission_classes = ADMIN_AUDIT

    @extend_schema(tags=[TAG], summary="Détail d'un événement", responses=EvenementSerializer)
    def get(self, request, pk):
        evenement = services.get_evenement(pk)
        return succes("Événement récupéré.", EvenementSerializer(evenement).data)


class FluxVue(APIView):
    """Flux temps réel par interrogation courte : le client demande les événements enregistrés
    depuis le dernier reçu. Les permissions sont vérifiées à chaque appel ; une coupure ne
    perd rien (reprise au dernier événement reçu, dédoublonnage par id côté client)."""

    permission_classes = ADMIN_AUDIT

    @extend_schema(
        tags=[TAG],
        summary="Nouveaux événements depuis une date (flux temps réel)",
        parameters=[FluxEntreeSerializer],
        responses=FluxSerializer,
    )
    def get(self, request):
        serveur_le = timezone.now()
        filtres = _valider(FluxEntreeSerializer, request)
        flux = services.flux_depuis(filtres.pop("depuis"), filtres)
        donnees = {**flux, "serveur_le": serveur_le}
        return succes("Nouveaux événements.", FluxSerializer(donnees).data)


class StatistiquesVue(APIView):
    permission_classes = ADMIN_AUDIT

    @extend_schema(
        tags=[TAG],
        summary="Indicateurs du journal sur une période",
        parameters=[StatsEntreeSerializer],
        responses=StatsSerializer,
    )
    def get(self, request):
        debut, fin = bornes(_valider(StatsEntreeSerializer, request)["periode"])
        chiffres = {**services.statistiques(debut, fin), "debut": debut, "fin": fin}
        return succes("Indicateurs du journal calculés.", StatsSerializer(chiffres).data)
