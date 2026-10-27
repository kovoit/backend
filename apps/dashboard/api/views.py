from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.views import APIView

from apps.accounts.api.permissions import ADMIN, CONNECTE
from apps.core.api.reponses import succes
from apps.dashboard import services


class EconomieTrajetSerializer(serializers.Serializer):
    trajet_id = serializers.UUIDField()
    depart_le = serializers.DateTimeField()
    depart = serializers.CharField()
    arrivee = serializers.CharField()
    montant = serializers.IntegerField()


class EconomiesSerializer(serializers.Serializer):
    mois_en_cours = serializers.IntegerField()
    total = serializers.IntegerField()
    par_trajet = EconomieTrajetSerializer(many=True)


class EconomiesVue(APIView):
    permission_classes = CONNECTE

    @extend_schema(
        tags=["profil"],
        summary="Mes économies de conducteur (par trajet et cumul du mois)",
        responses=EconomiesSerializer,
    )
    def get(self, request):
        economies = services.economies_conducteur(request.user)
        return succes("Économies calculées.", EconomiesSerializer(economies).data)


class PeriodeEntreeSerializer(serializers.Serializer):
    periode = serializers.ChoiceField(choices=list(services.PERIODES), default="30j")


class PeriodeSerializer(serializers.Serializer):
    code = serializers.ChoiceField(choices=list(services.PERIODES))
    debut = serializers.DateField()
    fin = serializers.DateField()


class IndicateursPeriodeSerializer(serializers.Serializer):
    trajets_publies = serializers.IntegerField()
    trajets_termines = serializers.IntegerField()
    passagers_transportes = serializers.IntegerField()
    economies_realisees = serializers.IntegerField(help_text="Net reçu par les conducteurs")
    commissions_kovoit = serializers.IntegerField(
        help_text="Commissions réellement prélevées (journal des transactions)"
    )
    utilisateurs_verifies = serializers.IntegerField()
    conducteurs_verifies = serializers.IntegerField()


class ATraiterSerializer(serializers.Serializer):
    kyc_en_attente = serializers.IntegerField()
    signalements_ouverts = serializers.IntegerField()
    litiges = serializers.IntegerField()
    retraits_en_attente = serializers.IntegerField(
        help_text="Retraits à verser (statut en_attente), sans limite de période"
    )


class JourSerializer(serializers.Serializer):
    date = serializers.DateField()
    trajets = serializers.IntegerField()
    passagers = serializers.IntegerField()


class TableauDeBordSerializer(serializers.Serializer):
    periode = PeriodeSerializer()
    donnees_demo = serializers.BooleanField(
        help_text="Vrai si la base contient des comptes de démonstration (seed_demo, "
        "seed_backoffice) : les indicateurs incluent alors leur activité fictive."
    )
    indicateurs = IndicateursPeriodeSerializer()
    a_traiter = ATraiterSerializer()
    evolution = JourSerializer(many=True)
    reservations_par_statut = serializers.DictField(child=serializers.IntegerField())


class TableauDeBordVue(APIView):
    permission_classes = ADMIN

    @extend_schema(
        tags=["admin - indicateurs"],
        summary="Tableau de bord : indicateurs de la période, files de travail, évolution",
        description="Visible par tout administrateur, même sans rôle. `a_traiter` compte les "
        "éléments en attente à ce jour (KYC, signalements ouverts, litiges, retraits à verser), "
        "indépendamment de la période.",
        parameters=[PeriodeEntreeSerializer],
        responses=TableauDeBordSerializer,
    )
    def get(self, request):
        entree = PeriodeEntreeSerializer(data=request.query_params)
        entree.is_valid(raise_exception=True)
        donnees = services.tableau_de_bord(entree.validated_data["periode"])
        return succes("Tableau de bord calculé.", TableauDeBordSerializer(donnees).data)
