from apps.core.repository import BaseRepository
from apps.notifications.models import AppareilNotification


class AppareilRepository(BaseRepository[AppareilNotification]):
    model = AppareilNotification
    message_introuvable = "Appareil introuvable."

    def jetons_de(self, utilisateur) -> list[str]:
        return list(self.filter(utilisateur=utilisateur).values_list("jeton", flat=True))

    def enregistrer(self, utilisateur, jeton: str, plateforme: str) -> AppareilNotification:
        appareil, _ = self.model.objects.update_or_create(
            jeton=jeton, defaults={"utilisateur": utilisateur, "plateforme": plateforme}
        )
        return appareil

    def supprimer_jeton(self, jeton: str) -> None:
        self.filter(jeton=jeton).delete()


appareil_repository = AppareilRepository()
