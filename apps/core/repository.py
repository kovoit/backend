"""Repository de base : seul point d'accès à l'ORM. Chaque app en hérite."""

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.exceptions import RessourceIntrouvable


class BaseRepository[M: models.Model]:
    model: type[M]
    message_introuvable = "La ressource demandée est introuvable."

    def queryset(self) -> models.QuerySet[M]:
        return self.model._default_manager.all()

    def get_by_id(self, pk: Any) -> M:
        return self._get(self.queryset(), pk=pk)

    def get_for_update(self, pk: Any) -> M:
        """Verrouille la ligne : à appeler uniquement dans un `transaction.atomic()`."""
        return self._get(self.queryset().select_for_update(), pk=pk)

    def get_or_none(self, **filtres) -> M | None:
        try:
            return self.queryset().get(**filtres)
        except (self.model.DoesNotExist, ValidationError, ValueError):
            return None

    def filter(self, *conditions: models.Q, **filtres) -> models.QuerySet[M]:
        return self.queryset().filter(*conditions, **filtres)

    def exists(self, *conditions: models.Q, **filtres) -> bool:
        return self.queryset().filter(*conditions, **filtres).exists()

    def compter(self, *conditions: models.Q, **filtres) -> int:
        return self.queryset().filter(*conditions, **filtres).count()

    def create(self, **donnees) -> M:
        return self.model._default_manager.create(**donnees)

    def update(self, instance: M, **champs) -> M:
        for nom, valeur in champs.items():
            setattr(instance, nom, valeur)
        champs_a_sauver = list(champs)
        if any(champ.name == "modifie_le" for champ in instance._meta.concrete_fields):
            champs_a_sauver.append("modifie_le")
        instance.save(update_fields=champs_a_sauver)
        return instance

    def delete(self, instance: M) -> None:
        instance.delete()

    def _get(self, queryset: models.QuerySet[M], **filtres) -> M:
        try:
            return queryset.get(**filtres)
        except (self.model.DoesNotExist, ValidationError, ValueError) as exc:
            raise RessourceIntrouvable(self.message_introuvable) from exc
