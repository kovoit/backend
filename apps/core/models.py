import uuid

from django.db import models


class BaseModel(models.Model):
    """Modèle abstrait : identifiant UUID + horodatages de création et de modification."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cree_le = models.DateTimeField("créé le", auto_now_add=True)
    modifie_le = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-cree_le"]
