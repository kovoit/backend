from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class Plateforme(models.TextChoices):
    ANDROID = "android", "Android"
    IOS = "ios", "iOS"
    WEB = "web", "Web"


class Notification(BaseModel):
    """Notification envoyée à un utilisateur, conservée pour l'écran « Notifications » de l'app
    (le push peut ne jamais arriver : téléphone éteint, Firebase non configuré…)."""

    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    titre = models.CharField(max_length=120)
    message = models.TextField()
    # Ce que l'app ouvre quand on touche la notification (reservation_id, trajet_id, destinataire)
    donnees = models.JSONField(default=dict, blank=True)
    lue_le = models.DateTimeField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "notification"
        verbose_name_plural = "notifications"
        indexes = [models.Index(fields=["utilisateur", "-cree_le"])]


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
