from datetime import datetime

from django.db.models import Sum

from apps.core.repository import BaseRepository
from apps.portefeuille.models import Transaction, TypeTransaction


class TransactionRepository(BaseRepository[Transaction]):
    model = Transaction

    def sommes_par_type(self, utilisateur) -> dict[str, int]:
        lignes = (
            self.filter(utilisateur=utilisateur)
            .values("type")
            .annotate(total=Sum("montant"))
            .values_list("type", "total")
        )
        return dict(lignes)

    def somme(self, utilisateur, reservation, type_: str) -> int:
        total = self.filter(utilisateur=utilisateur, reservation=reservation, type=type_).aggregate(
            total=Sum("montant")
        )["total"]
        return total or 0

    def historique(self, utilisateur):
        return self.filter(utilisateur=utilisateur).order_by("-cree_le")

    def credits_de(self, utilisateur, depuis: datetime | None = None):
        queryset = self.filter(utilisateur=utilisateur, type=TypeTransaction.CREDIT)
        return queryset.filter(cree_le__gte=depuis) if depuis else queryset

    def total_credits(self, utilisateur=None, depuis: datetime | None = None) -> int:
        queryset = self.filter(type=TypeTransaction.CREDIT)
        if utilisateur is not None:
            queryset = queryset.filter(utilisateur=utilisateur)
        if depuis:
            queryset = queryset.filter(cree_le__gte=depuis)
        return queryset.aggregate(total=Sum("montant"))["total"] or 0

    def credits_par_trajet(self, utilisateur):
        return (
            self.credits_de(utilisateur)
            .values(
                "reservation__trajet_id",
                "reservation__trajet__depart_le",
                "reservation__trajet__depart_libelle",
                "reservation__trajet__arrivee_libelle",
            )
            .annotate(montant=Sum("montant"))
            .order_by("-reservation__trajet__depart_le")
        )


transaction_repository = TransactionRepository()
