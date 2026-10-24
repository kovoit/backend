from apps.core.repository import BaseRepository
from apps.notifications.models import AppareilNotification, Notification


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


class NotificationRepository(BaseRepository[Notification]):
    model = Notification
    message_introuvable = "Notification introuvable."

    def de(self, utilisateur):
        return self.filter(utilisateur=utilisateur).order_by("-cree_le")

    def compter_non_lues(self, utilisateur) -> int:
        return self.filter(utilisateur=utilisateur, lue_le__isnull=True).count()

    def get_de(self, utilisateur, notification_id) -> Notification:
        return self._get(self.filter(utilisateur=utilisateur), pk=notification_id)

    def marquer_toutes_lues(self, utilisateur, maintenant) -> int:
        return self.filter(utilisateur=utilisateur, lue_le__isnull=True).update(lue_le=maintenant)


appareil_repository = AppareilRepository()
notification_repository = NotificationRepository()
