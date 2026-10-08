from django.db import models

from apps.core.models import BaseModel


class LienPartage(BaseModel):
    """Lien public « Partager mon trajet », valable jusqu'à la clôture de la réservation."""

    reservation = models.OneToOneField(
        "reservations.Reservation", on_delete=models.CASCADE, related_name="lien_partage"
    )
    jeton = models.CharField(max_length=64, unique=True)

    class Meta(BaseModel.Meta):
        verbose_name = "lien de partage"
        verbose_name_plural = "liens de partage"
