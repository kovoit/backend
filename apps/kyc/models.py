import os
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models

from apps.core.models import BaseModel


class StockagePrive(FileSystemStorage):
    """Stockage hors de MEDIA_ROOT : aucun fichier n'est accessible par une URL publique."""

    @property
    def base_location(self):
        return settings.PRIVATE_MEDIA_ROOT

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    def url(self, name):
        raise ValueError("Les pièces KYC ne sont pas accessibles par URL.")


class TypeDossier(models.TextChoices):
    PASSAGER = "passager", "Passager"
    CONDUCTEUR = "conducteur", "Conducteur"


class StatutKyc(models.TextChoices):
    NON_VERIFIE = "non_verifie", "Non vérifié"
    EN_ATTENTE = "en_attente", "En attente"
    VERIFIE = "verifie", "Vérifié"
    REJETE = "rejete", "Rejeté"


class TypePiece(models.TextChoices):
    IDENTITE = "identite", "Pièce d'identité"
    SELFIE = "selfie", "Selfie"
    PERMIS = "permis", "Permis de conduire"
    CARTE_GRISE = "carte_grise", "Carte grise"
    ASSURANCE = "assurance", "Assurance"
    PHOTO_VEHICULE = "photo_vehicule", "Photo du véhicule"


def chemin_piece(piece: "KycPiece", nom_fichier: str) -> str:
    extension = Path(nom_fichier).suffix.lower()
    return f"kyc/{piece.dossier.utilisateur_id}/{uuid.uuid4().hex}{extension}"


class KycDossier(BaseModel):
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dossiers_kyc"
    )
    type = models.CharField(max_length=10, choices=TypeDossier.choices)
    statut = models.CharField(
        max_length=12, choices=StatutKyc.choices, default=StatutKyc.NON_VERIFIE
    )
    motif_rejet = models.TextField(blank=True)
    soumis_le = models.DateTimeField(null=True, blank=True)
    traite_le = models.DateTimeField(null=True, blank=True)
    traite_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "dossier KYC"
        verbose_name_plural = "dossiers KYC"
        constraints = [
            models.UniqueConstraint(fields=["utilisateur", "type"], name="un_dossier_par_type")
        ]


class KycPiece(BaseModel):
    dossier = models.ForeignKey(KycDossier, on_delete=models.CASCADE, related_name="pieces")
    type_piece = models.CharField(max_length=20, choices=TypePiece.choices)
    fichier = models.FileField(upload_to=chemin_piece, storage=StockagePrive())

    class Meta(BaseModel.Meta):
        verbose_name = "pièce KYC"
        verbose_name_plural = "pièces KYC"
        constraints = [
            models.UniqueConstraint(fields=["dossier", "type_piece"], name="une_piece_par_type")
        ]


class KycConsultation(BaseModel):
    """Journal : chaque consultation d'une pièce par un administrateur."""

    piece = models.ForeignKey(KycPiece, on_delete=models.CASCADE, related_name="consultations")
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    class Meta(BaseModel.Meta):
        verbose_name = "consultation de pièce KYC"
        verbose_name_plural = "consultations de pièces KYC"
