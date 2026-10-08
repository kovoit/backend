from typing import Any

from apps.core.repository import BaseRepository
from apps.parametres.models import Parametre


class ParametreRepository(BaseRepository[Parametre]):
    model = Parametre
    message_introuvable = "Paramètre introuvable."

    def lister(self):
        return self.queryset().select_related("modifie_par").order_by("cle")

    def get_valeur(self, cle: str) -> Any | None:
        return self.queryset().filter(cle=cle).values_list("valeur", flat=True).first()

    def creer_si_absent(self, cle: str, valeur: Any, description: str) -> bool:
        _, cree = self.model.objects.get_or_create(
            cle=cle, defaults={"valeur": valeur, "description": description}
        )
        return cree


parametre_repository = ParametreRepository()
