from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import BaseModel


class Note(BaseModel):
    reservation = models.ForeignKey(
        "reservations.Reservation", on_delete=models.CASCADE, related_name="notes"
    )
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notes_donnees"
    )
    cible = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notes_recues"
    )
    note = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    commentaire = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "note"
        verbose_name_plural = "notes"
        constraints = [
            models.UniqueConstraint(
                fields=["reservation", "auteur"], name="une_note_par_reservation_et_auteur"
            ),
            models.CheckConstraint(
                condition=models.Q(note__gte=1, note__lte=5), name="note_entre_1_et_5"
            ),
        ]


class StatutSignalement(models.TextChoices):
    OUVERT = "ouvert", "Ouvert"
    TRAITE = "traite", "Traité"


class DecisionLitige(models.TextChoices):
    CREDITER_CONDUCTEUR = "crediter_conducteur", "Payer le conducteur"
    REMBOURSER_PASSAGER = "rembourser_passager", "Rembourser le passager"


class Signalement(BaseModel):
    reservation = models.ForeignKey(
        "reservations.Reservation", on_delete=models.CASCADE, related_name="signalements"
    )
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="signalements_faits"
    )
    cible = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="signalements_recus"
    )
    motif = models.TextField()
    statut = models.CharField(
        max_length=10, choices=StatutSignalement.choices, default=StatutSignalement.OUVERT
    )
    resolution = models.TextField(blank=True)
    decision = models.CharField(max_length=25, choices=DecisionLitige.choices, blank=True)
    traite_le = models.DateTimeField(null=True, blank=True)
    traite_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "signalement"
        verbose_name_plural = "signalements"
