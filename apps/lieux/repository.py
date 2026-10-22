from apps.core.repository import BaseRepository
from apps.lieux.models import Lieu, normaliser


class LieuRepository(BaseRepository[Lieu]):
    model = Lieu
    message_introuvable = "Lieu introuvable."

    def rechercher(self, terme: str, limite: int):
        lieux = self.filter(actif=True)
        if terme:
            lieux = lieux.filter(recherche__contains=normaliser(terme))
        return lieux.order_by("libelle")[:limite]


lieu_repository = LieuRepository()
