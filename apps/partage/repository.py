from apps.core.repository import BaseRepository
from apps.partage.models import LienPartage


class LienPartageRepository(BaseRepository[LienPartage]):
    model = LienPartage
    message_introuvable = "Lien de partage invalide ou expiré."

    def queryset(self):
        return (
            super()
            .queryset()
            .select_related("reservation__trajet__conducteur", "reservation__trajet__vehicule")
        )

    def get_par_jeton(self, jeton: str) -> LienPartage:
        return self._get(self.queryset(), jeton=jeton)


lien_repository = LienPartageRepository()
