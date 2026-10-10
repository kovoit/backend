from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models

from apps.accounts.managers import UserManager
from apps.core.models import BaseModel

valider_telephone = RegexValidator(
    r"^\+?\d{8,15}$", "Numéro de téléphone invalide (8 à 15 chiffres, + facultatif)."
)


class ModeActif(models.TextChoices):
    PASSAGER = "passager", "Passager"
    CONDUCTEUR = "conducteur", "Conducteur"


class StatutCompte(models.TextChoices):
    ACTIF = "actif", "Actif"
    SUSPENDU = "suspendu", "Suspendu"


class User(BaseModel, AbstractBaseUser, PermissionsMixin):
    email = models.EmailField("email", unique=True)
    telephone = models.CharField(
        "téléphone", max_length=16, blank=True, validators=[valider_telephone]
    )
    nom = models.CharField(max_length=100, blank=True)
    prenom = models.CharField("prénom", max_length=100, blank=True)
    photo = models.ImageField(upload_to="photos_profil/", blank=True)
    email_verifie = models.BooleanField("email vérifié", default=False)
    mode_actif = models.CharField(
        max_length=10, choices=ModeActif.choices, default=ModeActif.PASSAGER
    )
    statut_compte = models.CharField(
        max_length=10, choices=StatutCompte.choices, default=StatutCompte.ACTIF
    )
    suspendu_jusqu_au = models.DateTimeField("suspendu jusqu'au", null=True, blank=True)
    motif_suspension = models.TextField("motif de suspension", blank=True)
    is_active = models.BooleanField("actif (Django)", default=True)
    is_staff = models.BooleanField("administrateur", default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["telephone", "nom", "prenom"]

    class Meta(BaseModel.Meta):
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"

    def __str__(self) -> str:
        return f"{self.prenom} {self.nom} <{self.email}>"

    @property
    def profil_complet(self) -> bool:
        """Nom, prénom et téléphone renseignés (obligatoire avant de soumettre un KYC)."""
        return bool(self.nom and self.prenom and self.telephone)


class OtpCode(BaseModel):
    """Code de connexion envoyé par email. Seul le hash est stocké."""

    email = models.EmailField(db_index=True)
    code_hash = models.CharField(max_length=128)
    expire_le = models.DateTimeField()
    essais = models.PositiveSmallIntegerField(default=0)
    utilise = models.BooleanField(default=False)

    class Meta(BaseModel.Meta):
        verbose_name = "code OTP"
        verbose_name_plural = "codes OTP"
