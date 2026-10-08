from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class StatutTrajet(models.TextChoices):
    PUBLIE = "publie", "Publié"
    COMPLET = "complet", "Complet"
    EN_COURS = "en_cours", "En cours"
    TERMINE = "termine", "Terminé"
    ANNULE = "annule", "Annulé"


class Trajet(BaseModel):
    conducteur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="trajets_conduits"
    )
    vehicule = models.ForeignKey(
        "vehicules.Vehicule", on_delete=models.PROTECT, related_name="trajets"
    )
    depart_lat = models.FloatField()
    depart_lng = models.FloatField()
    depart_libelle = models.CharField(max_length=255)
    arrivee_lat = models.FloatField()
    arrivee_lng = models.FloatField()
    arrivee_libelle = models.CharField(max_length=255)
    depart_le = models.DateTimeField("départ le", db_index=True)
    places_total = models.PositiveSmallIntegerField()
    places_restantes = models.PositiveSmallIntegerField()
    distance_km = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    prix_place = models.PositiveIntegerField("prix par place (F CFA)")
    statut = models.CharField(
        max_length=10, choices=StatutTrajet.choices, default=StatutTrajet.PUBLIE, db_index=True
    )
    # Dernière position connue du conducteur (lien « Partager mon trajet »)
    position_lat = models.FloatField(null=True, blank=True)
    position_lng = models.FloatField(null=True, blank=True)
    position_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["depart_le"]
        verbose_name = "trajet"
        verbose_name_plural = "trajets"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(places_restantes__lte=models.F("places_total")),
                name="places_restantes_inferieures_au_total",
            ),
            models.CheckConstraint(
                condition=models.Q(places_total__gte=1), name="au_moins_une_place"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.depart_libelle} → {self.arrivee_libelle} ({self.depart_le:%d/%m %H:%M})"


class PointPriseEnCharge(BaseModel):
    trajet = models.ForeignKey(Trajet, on_delete=models.CASCADE, related_name="points")
    ordre = models.PositiveSmallIntegerField()
    lat = models.FloatField()
    lng = models.FloatField()
    libelle = models.CharField(max_length=255)

    class Meta:
        ordering = ["ordre"]
        verbose_name = "point de prise en charge"
        verbose_name_plural = "points de prise en charge"
        constraints = [
            models.UniqueConstraint(fields=["trajet", "ordre"], name="ordre_unique_par_trajet")
        ]
