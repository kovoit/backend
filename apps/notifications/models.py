from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class Plateforme(models.TextChoices):
    ANDROID = "android", "Android"
    IOS = "ios", "iOS"
    WEB = "web", "Web"


class AppareilNotification(BaseModel):
    """Téléphone d'un utilisateur, identifié par son jeton de notification push (FCM)."""

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="appareils"
    )
    jeton = models.CharField(max_length=255, unique=True)
    plateforme = models.CharField(max_length=10, choices=Plateforme.choices)

    class Meta(BaseModel.Meta):
        verbose_name = "appareil"
        verbose_name_plural = "appareils"
