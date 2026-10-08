from django.conf import settings
from django.db import models


class Parametre(models.Model):
    """Paramètre métier modifiable par l'administrateur (aucune valeur en dur dans le code)."""

    cle = models.CharField("clé", max_length=64, primary_key=True)
    valeur = models.JSONField()
    description = models.CharField(max_length=255, blank=True)
    modifie_le = models.DateTimeField("modifié le", auto_now=True)
    modifie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="modifié par",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        ordering = ["cle"]
        verbose_name = "paramètre"
        verbose_name_plural = "paramètres"

    def __str__(self) -> str:
        return f"{self.cle} = {self.valeur}"
