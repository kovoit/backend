from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class TypeTransaction(models.TextChoices):
    RECHARGE = "recharge", "Recharge"
    BLOCAGE = "blocage", "Blocage"
    DEBLOCAGE = "deblocage", "Déblocage"
    DEBIT = "debit", "Débit"
    CREDIT = "credit", "Crédit"
    RETRAIT = "retrait", "Retrait"
    REMBOURSEMENT = "remboursement", "Remboursement"


class MoyenPaiement(models.TextChoices):
    """Mobile Money disponibles au Togo (T-Money est devenu Mixx)."""

    FLOOZ = "flooz", "Flooz (Moov Africa)"
    MIXX = "mixx", "Mixx (Togocom)"


class StatutTransaction(models.TextChoices):
    VALIDEE = "validee", "Validée"


class Transaction(BaseModel):
    """Journal en ajout seul : le solde est toujours recalculé, jamais stocké."""

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="transactions"
    )
    type = models.CharField(max_length=15, choices=TypeTransaction.choices)
    montant = models.PositiveIntegerField("montant (F CFA)")
    reservation = models.ForeignKey(
        "reservations.Reservation",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    moyen_paiement = models.CharField(
        max_length=10,
        choices=MoyenPaiement.choices,
        blank=True,
        help_text="Renseigné pour les mouvements passés par Mobile Money (recharge, retrait).",
    )
    reference_externe = models.CharField(max_length=64, blank=True)
    statut = models.CharField(
        max_length=10, choices=StatutTransaction.choices, default=StatutTransaction.VALIDEE
    )

    class Meta(BaseModel.Meta):
        verbose_name = "transaction"
        verbose_name_plural = "transactions"
        constraints = [
            models.CheckConstraint(condition=models.Q(montant__gt=0), name="montant_positif")
        ]
