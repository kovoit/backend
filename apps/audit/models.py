"""Journal d'audit : un événement par action importante, en ajout seul.

Aucune clé étrangère : l'historique survit à la suppression des comptes et des ressources
(et une mise à NULL en cascade serait une modification, interdite par le trigger PostgreSQL).
"""

import uuid

from django.db import models
from django.utils import timezone


class Categorie(models.TextChoices):
    METIER = "metier", "Métier"
    ADMIN = "admin", "Administration"
    SECURITE = "securite", "Sécurité"
    TECHNIQUE = "technique", "Technique"


class Resultat(models.TextChoices):
    SUCCES = "succes", "Réussi"
    REFUS = "refus", "Refusé"
    ECHEC = "echec", "Échec technique"


class Gravite(models.TextChoices):
    INFO = "info", "Information"
    AVERTISSEMENT = "avertissement", "Avertissement"
    CRITIQUE = "critique", "Critique"


class Canal(models.TextChoices):
    WEB = "web", "Web (back-office)"
    MOBILE = "mobile", "Application mobile"
    API = "api", "API (canal non identifié)"
    SYSTEME = "systeme", "Système"


class Role(models.TextChoices):
    PASSAGER = "passager", "Passager"
    CONDUCTEUR = "conducteur", "Conducteur"
    ADMIN = "admin", "Administrateur"
    SYSTEME = "systeme", "Système"
    ANONYME = "anonyme", "Non connecté"


class EvenementAudit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    survenu_le = models.DateTimeField(default=timezone.now)
    enregistre_le = models.DateTimeField(default=timezone.now)
    categorie = models.CharField(max_length=16, choices=Categorie.choices)
    action = models.CharField(max_length=64)
    resultat = models.CharField(max_length=8, choices=Resultat.choices)
    gravite = models.CharField(max_length=16, choices=Gravite.choices)
    canal = models.CharField(max_length=8, choices=Canal.choices)
    acteur_id = models.UUIDField(null=True, blank=True)
    acteur_role = models.CharField(max_length=16, choices=Role.choices)
    ressource_type = models.CharField(max_length=32, blank=True)
    ressource_id = models.CharField(max_length=64, blank=True)
    code_motif = models.CharField(max_length=64, blank=True)
    request_id = models.CharField(max_length=32, blank=True)
    # Champs autorisés seulement (voir audit/securite.py) : jamais de secret ni de document
    details = models.JSONField(default=dict, blank=True)
    changements = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-enregistre_le"]
        indexes = [
            models.Index(fields=["-enregistre_le"], name="audit_date"),
            models.Index(fields=["acteur_id", "-enregistre_le"], name="audit_acteur"),
            models.Index(fields=["ressource_type", "ressource_id"], name="audit_ressource"),
            models.Index(fields=["categorie", "-enregistre_le"], name="audit_categorie"),
            models.Index(fields=["action", "-enregistre_le"], name="audit_action"),
            models.Index(fields=["request_id"], name="audit_requete"),
        ]

    def __str__(self) -> str:
        return f"{self.enregistre_le:%Y-%m-%d %H:%M:%S} {self.action} ({self.resultat})"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise PermissionError("Journal d'audit en ajout seul : modification interdite.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Journal d'audit en ajout seul : suppression interdite.")
