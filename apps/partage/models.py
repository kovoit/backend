from django.db import models

from apps.core.models import BaseModel


class LienPartage(BaseModel):
    """Lien public « Partager mon trajet ».

    Valable jusqu'à l'arrivée, c'est-à-dire tant que la réservation est `acceptee` ou
    `en_cours` (D-05).
    """

    reservation = models.OneToOneField(
        "reservations.Reservation", on_delete=models.CASCADE, related_name="lien_partage"
    )
    jeton = models.CharField(max_length=64, unique=True)

    class Meta(BaseModel.Meta):
        verbose_name = "lien de partage"
        verbose_name_plural = "liens de partage"
