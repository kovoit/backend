from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class StatutReservation(models.TextChoices):
    DEMANDEE = "demandee", "Demandée"
    ACCEPTEE = "acceptee", "Acceptée"
    REFUSEE = "refusee", "Refusée"
    ANNULEE = "annulee", "Annulée"
    ABSENT = "absent", "Passager absent"
    EN_COURS = "en_cours", "En cours"
    TERMINEE = "terminee", "Terminée"
    LITIGE = "litige", "En litige"
    CLOTUREE = "cloturee", "Clôturée"


STATUTS_ACTIFS = [
    StatutReservation.DEMANDEE,
    StatutReservation.ACCEPTEE,
    StatutReservation.EN_COURS,
]


class Reservation(BaseModel):
    trajet = models.ForeignKey(
        "trajets.Trajet", on_delete=models.PROTECT, related_name="reservations"
    )
    passager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reservations"
    )
    point = models.ForeignKey(
        "trajets.PointPriseEnCharge", on_delete=models.PROTECT, related_name="reservations"
    )
    arrivee_lat = models.FloatField()
    arrivee_lng = models.FloatField()
    arrivee_libelle = models.CharField(max_length=255, blank=True)
    distance_km = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    prix = models.PositiveIntegerField("prix (F CFA)")
    frais_service = models.PositiveIntegerField("frais de service (F CFA)", default=0)
    statut = models.CharField(
        max_length=10,
        choices=StatutReservation.choices,
        default=StatutReservation.DEMANDEE,
        db_index=True,
    )
    # Le code de départ n'est jamais stocké : il est dérivé de ce sel et de SECRET_KEY.
    code_depart_sel = models.CharField(max_length=64, blank=True)
    essais_code = models.PositiveSmallIntegerField(default=0)

    acceptee_le = models.DateTimeField(null=True, blank=True)
    refusee_le = models.DateTimeField(null=True, blank=True)
    annulee_le = models.DateTimeField(null=True, blank=True)
    absent_le = models.DateTimeField(null=True, blank=True)
    en_cours_le = models.DateTimeField(null=True, blank=True)
    terminee_le = models.DateTimeField(null=True, blank=True)
    litige_le = models.DateTimeField(null=True, blank=True)
    cloturee_le = models.DateTimeField(null=True, blank=True)

    annulee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    annulation_tardive = models.BooleanField(default=False)
    absence_lat = models.FloatField(null=True, blank=True)
    absence_lng = models.FloatField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "réservation"
        verbose_name_plural = "réservations"
        constraints = [
            models.UniqueConstraint(
                fields=["trajet", "passager"],
                condition=models.Q(statut__in=STATUTS_ACTIFS),
                name="une_reservation_active_par_trajet",
            )
        ]

    @property
    def montant_total(self) -> int:
        return self.prix + self.frais_service
