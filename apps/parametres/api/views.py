from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView

from apps.core.api.reponses import succes
from apps.parametres import services
from apps.parametres.api.serializers import ModificationParametreSerializer, ParametreSerializer

TAG = "admin - paramètres"


class ParametreListeVue(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=[TAG],
        summary="Lister les paramètres métier",
        responses=ParametreSerializer(many=True),
    )
    def get(self, request):
        parametres = services.lister_parametres()
        return succes("Paramètres récupérés.", ParametreSerializer(parametres, many=True).data)


class ParametreDetailVue(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=[TAG],
        summary="Modifier la valeur d'un paramètre",
        request=ModificationParametreSerializer,
        responses=ParametreSerializer,
    )
    def patch(self, request, cle: str):
        entree = ModificationParametreSerializer(data=request.data)
        entree.is_valid(raise_exception=True)
        parametre = services.modifier_param(cle, entree.validated_data["valeur"], par=request.user)
        return succes("Paramètre modifié.", ParametreSerializer(parametre).data)
