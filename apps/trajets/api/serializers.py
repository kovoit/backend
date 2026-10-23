from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.confiance.api.serializers import PersonneSerializer
from apps.portefeuille.api.serializers import ApercuPaiementSerializer
from apps.portefeuille.services import apercu_paiement
from apps.trajets.api.tarification import TarificationSerializer
from apps.trajets.models import PointPriseEnCharge, Trajet
from apps.vehicules.api.serializers import VehiculeResumeSerializer

LATITUDE = {"min_value": -90, "max_value": 90}
LONGITUDE = {"min_value": -180, "max_value": 180}


class PointSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointPriseEnCharge
        fields = ["id", "ordre", "lat", "lng", "libelle"]


class TrajetSerializer(serializers.ModelSerializer):
    conducteur = PersonneSerializer(read_only=True)
    vehicule = VehiculeResumeSerializer(read_only=True)
    points = PointSerializer(many=True, read_only=True)
    frais_service = serializers.SerializerMethodField(
        help_text="Toujours 0 : la commission Kovoit est à la charge du conducteur (champ conservé "
        "pour la compatibilité des applications)."
    )

    class Meta:
        model = Trajet
        fields = [
            "id",
            "conducteur",
            "vehicule",
            "depart_lat",
            "depart_lng",
            "depart_libelle",
            "arrivee_lat",
            "arrivee_lng",
            "arrivee_libelle",
            "points",
            "depart_le",
            "places_total",
            "places_restantes",
            "distance_km",
            "duree_min",
            "prix_place",
            "frais_service",
            "statut",
        ]

    def get_frais_service(self, trajet: Trajet) -> int:
        return 0


class TrajetDetailSerializer(TrajetSerializer):
    """Écran « Détails du trajet & Réservation » : ajoute l'aperçu du paiement du lecteur.

    Attend `context={"utilisateur": ...}`.
    """

    paiement = serializers.SerializerMethodField()

    class Meta(TrajetSerializer.Meta):
        fields = [*TrajetSerializer.Meta.fields, "paiement"]

    @extend_schema_field(ApercuPaiementSerializer)
    def get_paiement(self, trajet: Trajet) -> dict:
        return apercu_paiement(self.context["utilisateur"], trajet.prix_place)


class TrajetConducteurSerializer(TrajetSerializer):
    nb_demandes = serializers.IntegerField(read_only=True, default=0)
    tarification = serializers.SerializerMethodField(
        help_text="Détail du calcul du prix, figé à la publication (null : trajet publié avant "
        "la tarification automatique)"
    )

    class Meta(TrajetSerializer.Meta):
        fields = [*TrajetSerializer.Meta.fields, "nb_demandes", "position_le", "tarification"]

    @extend_schema_field(TarificationSerializer(allow_null=True))
    def get_tarification(self, trajet: Trajet) -> dict | None:
        return TarificationSerializer(trajet.tarification).data if trajet.tarification else None


class PointEntreeSerializer(serializers.Serializer):
    lat = serializers.FloatField(**LATITUDE)
    lng = serializers.FloatField(**LONGITUDE)
    libelle = serializers.CharField(max_length=255)


class PublicationSerializer(serializers.Serializer):
    vehicule_id = serializers.UUIDField()
    depart_lat = serializers.FloatField(**LATITUDE)
    depart_lng = serializers.FloatField(**LONGITUDE)
    depart_libelle = serializers.CharField(max_length=255)
    arrivee_lat = serializers.FloatField(**LATITUDE)
    arrivee_lng = serializers.FloatField(**LONGITUDE)
    arrivee_libelle = serializers.CharField(max_length=255)
    depart_le = serializers.DateTimeField()
    places = serializers.IntegerField(min_value=1)
    points = PointEntreeSerializer(many=True, min_length=1, max_length=3)


class EstimationSerializer(serializers.Serializer):
    """Mêmes données que la publication, pour le prix affiché avant de publier."""

    vehicule_id = serializers.UUIDField()
    depart_lat = serializers.FloatField(**LATITUDE)
    depart_lng = serializers.FloatField(**LONGITUDE)
    arrivee_lat = serializers.FloatField(**LATITUDE)
    arrivee_lng = serializers.FloatField(**LONGITUDE)
    places = serializers.IntegerField(min_value=1)


class RechercheSerializer(serializers.Serializer):
    depart_lat = serializers.FloatField(**LATITUDE)
    depart_lng = serializers.FloatField(**LONGITUDE)
    arrivee_lat = serializers.FloatField(**LATITUDE)
    arrivee_lng = serializers.FloatField(**LONGITUDE)
    date_heure = serializers.DateTimeField()


class ResultatRechercheSerializer(serializers.Serializer):
    trajet = TrajetSerializer()
    point_propose = PointSerializer()
    distance_marche_km = serializers.FloatField()
    ecart_minutes = serializers.IntegerField()


class PositionSerializer(serializers.Serializer):
    lat = serializers.FloatField(**LATITUDE)
    lng = serializers.FloatField(**LONGITUDE)
