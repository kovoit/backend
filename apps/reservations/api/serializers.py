from rest_framework import serializers

from apps.confiance.api.serializers import PersonneSerializer
from apps.portefeuille.models import MoyenPaiement
from apps.reservations.code_depart import calculer_code
from apps.reservations.models import Reservation, StatutReservation
from apps.trajets.api.serializers import LATITUDE, LONGITUDE, PointSerializer, TrajetSerializer

CHAMPS_COMMUNS = [
    "id",
    "statut",
    "point",
    "arrivee_lat",
    "arrivee_lng",
    "arrivee_libelle",
    "distance_km",
    "prix",
    "frais_service",
    "montant_total",
    "moyen_paiement",
    "complement_paye",
    "annulation_tardive",
    "cree_le",
    "acceptee_le",
    "refusee_le",
    "annulee_le",
    "absent_le",
    "en_cours_le",
    "terminee_le",
    "litige_le",
    "cloturee_le",
]


class ReservationPassagerSerializer(serializers.ModelSerializer):
    """Vue du passager : seule vue qui contient le code de départ."""

    trajet = TrajetSerializer(read_only=True)
    point = PointSerializer(read_only=True)
    montant_total = serializers.IntegerField(read_only=True)
    code_depart = serializers.SerializerMethodField(
        help_text="Code à donner au conducteur, présent seulement si la réservation est acceptée."
    )

    class Meta:
        model = Reservation
        fields = ["trajet", *CHAMPS_COMMUNS, "code_depart"]

    def get_code_depart(self, reservation: Reservation) -> str | None:
        if reservation.statut != StatutReservation.ACCEPTEE:
            return None
        return calculer_code(reservation)


class ReservationConducteurSerializer(serializers.ModelSerializer):
    """Vue du conducteur : JAMAIS de code de départ."""

    trajet = serializers.UUIDField(source="trajet_id", read_only=True)
    passager = PersonneSerializer(read_only=True)
    point = PointSerializer(read_only=True)
    montant_total = serializers.IntegerField(read_only=True)
    essais_code = serializers.IntegerField(read_only=True)

    class Meta:
        model = Reservation
        fields = ["trajet", "passager", *CHAMPS_COMMUNS, "essais_code"]


class DemandeSerializer(serializers.Serializer):
    trajet_id = serializers.UUIDField()
    point_id = serializers.UUIDField(help_text="Point de prise en charge choisi")
    arrivee_lat = serializers.FloatField(**LATITUDE)
    arrivee_lng = serializers.FloatField(**LONGITUDE)
    arrivee_libelle = serializers.CharField(max_length=255, required=False, default="")
    moyen_paiement = serializers.ChoiceField(
        choices=MoyenPaiement.choices,
        required=False,
        allow_null=True,
        default=None,
        help_text="Obligatoire seulement si le portefeuille ne couvre pas le montant : "
        "le complément est payé par ce moyen.",
    )


class CodeDepartSerializer(serializers.Serializer):
    code = serializers.RegexField(r"^\d{4}$", error_messages={"invalid": "Code à 4 chiffres."})


class AbsenceSerializer(serializers.Serializer):
    lat = serializers.FloatField(**LATITUDE)
    lng = serializers.FloatField(**LONGITUDE)


def serialiser_pour(utilisateur, reservation: Reservation) -> dict:
    """Choisit la vue selon le rôle de l'utilisateur dans la réservation."""
    if utilisateur.id == reservation.passager_id:
        return ReservationPassagerSerializer(reservation).data
    return ReservationConducteurSerializer(reservation).data
