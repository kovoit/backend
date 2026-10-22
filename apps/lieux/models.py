import unicodedata

from django.db import models

from apps.core.models import BaseModel


def normaliser(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte.casefold())
    return "".join(c for c in decompose if not unicodedata.combining(c)).strip()


class TypeLieu(models.TextChoices):
    CARREFOUR = "carrefour", "Carrefour"
    QUARTIER = "quartier", "Quartier"
    REPERE = "repere", "Repère"


class Lieu(BaseModel):
    """Lieu connu de Lomé, proposé à la saisie du départ et de l'arrivée (app mobile).

    Référentiel géré dans le Django admin ; un lieu retiré est désactivé, pas supprimé.
    """

    libelle = models.CharField(max_length=120)
    quartier = models.CharField(max_length=80, blank=True)
    type = models.CharField(max_length=12, choices=TypeLieu.choices)
    lat = models.FloatField()
    lng = models.FloatField()
    actif = models.BooleanField(default=True)
    # Libellé et quartier sans accents ni majuscules : « hedzra » trouve « Hédzranawoé »
    recherche = models.CharField(max_length=210, editable=False, db_index=True)

    class Meta(BaseModel.Meta):
        ordering = ["libelle"]
        verbose_name = "lieu"
        verbose_name_plural = "lieux"
        constraints = [
            models.UniqueConstraint(fields=["libelle", "quartier"], name="lieu_unique"),
            models.CheckConstraint(
                condition=models.Q(lat__gte=-90, lat__lte=90, lng__gte=-180, lng__lte=180),
                name="lieu_coordonnees_valides",
            ),
        ]

    def save(self, *args, **kwargs):
        self.recherche = normaliser(f"{self.libelle} {self.quartier}")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.libelle} ({self.quartier})" if self.quartier else self.libelle
