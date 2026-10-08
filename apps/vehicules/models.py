from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import BaseModel


class TypeVehicule(models.TextChoices):
    MOTO = "moto", "Moto"
    VOITURE = "voiture", "Voiture"


class Vehicule(BaseModel):
    proprietaire = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vehicules"
    )
    type_vehicule = models.CharField(
        "type", max_length=10, choices=TypeVehicule.choices, default=TypeVehicule.VOITURE
    )
    marque = models.CharField(max_length=50)
    modele = models.CharField("modèle", max_length=50)
    couleur = models.CharField(max_length=30)
    immatriculation = models.CharField(max_length=20, unique=True)
    nb_places = models.PositiveSmallIntegerField(
        "nombre de places (conducteur compris)",
        validators=[MinValueValidator(2), MaxValueValidator(9)],
    )
    photo = models.ImageField(upload_to="vehicules/", blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "véhicule"
        verbose_name_plural = "véhicules"

    def __str__(self) -> str:
        return f"{self.marque} {self.modele} ({self.immatriculation})"
