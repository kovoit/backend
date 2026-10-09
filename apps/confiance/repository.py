from django.db.models import Avg, Count

from apps.confiance.models import Note, Signalement
from apps.core.repository import BaseRepository


class NoteRepository(BaseRepository[Note]):
    model = Note

    def moyenne_de(self, utilisateur) -> tuple[float | None, int]:
        resultat = self.filter(cible=utilisateur).aggregate(moyenne=Avg("note"), nombre=Count("id"))
        return resultat["moyenne"], resultat["nombre"]

    def dernieres_recues(self, utilisateur, nombre: int):
        return self.filter(cible=utilisateur).select_related("auteur").order_by("-cree_le")[:nombre]


class SignalementRepository(BaseRepository[Signalement]):
    model = Signalement
    message_introuvable = "Signalement introuvable."

    def queryset(self):
        return super().queryset().select_related("reservation", "auteur", "cible")

    def de_reservation(self, reservation):
        return self.filter(reservation=reservation).order_by("cree_le")

    def lister(self, statut: str | None = None):
        """File de travail : les plus anciens d'abord. traite_par (facultatif) joint ici seulement,
        car une jointure externe est incompatible avec le FOR UPDATE de get_for_update."""
        queryset = (
            self.queryset()
            .select_related(
                "traite_par",
                "reservation__passager",
                "reservation__trajet__conducteur",
                "reservation__point",
            )
            .order_by("cree_le")
        )
        return queryset.filter(statut=statut) if statut else queryset


note_repository = NoteRepository()
signalement_repository = SignalementRepository()
