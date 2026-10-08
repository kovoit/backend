from django.db.models import Avg, Count

from apps.confiance.models import Note, Signalement
from apps.core.repository import BaseRepository


class NoteRepository(BaseRepository[Note]):
    model = Note

    def moyenne_de(self, utilisateur) -> tuple[float | None, int]:
        resultat = self.filter(cible=utilisateur).aggregate(moyenne=Avg("note"), nombre=Count("id"))
        return resultat["moyenne"], resultat["nombre"]


class SignalementRepository(BaseRepository[Signalement]):
    model = Signalement
    message_introuvable = "Signalement introuvable."

    def queryset(self):
        return super().queryset().select_related("reservation", "auteur", "cible")

    def lister(self, statut: str | None = None):
        queryset = self.queryset().order_by("-cree_le")
        return queryset.filter(statut=statut) if statut else queryset


note_repository = NoteRepository()
signalement_repository = SignalementRepository()
