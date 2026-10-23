from datetime import date, datetime

from django.db.models import Q, Sum

from apps.core.repository import BaseRepository
from apps.portefeuille.models import StatutTransaction, Transaction, TypeTransaction

# Lignes qui comptent dans le solde : validées, et retraits en attente (montant déjà retenu)
COMPTEES = Q(statut=StatutTransaction.VALIDEE) | Q(
    type=TypeTransaction.RETRAIT, statut=StatutTransaction.EN_ATTENTE
)


class TransactionRepository(BaseRepository[Transaction]):
    model = Transaction

    def sommes_par_type(self, utilisateur) -> dict[str, int]:
        lignes = (
            self.filter(COMPTEES, utilisateur=utilisateur)
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

    def get_de(self, utilisateur, transaction_id) -> Transaction:
        return self._get(self.filter(utilisateur=utilisateur), pk=transaction_id)

    def get_verrouillee(self, transaction_id) -> Transaction:
        return self._get(self.model.objects.select_for_update(), pk=transaction_id)

    def recharges_en_attente(self, depuis: datetime):
        return self.filter(
            type=TypeTransaction.RECHARGE, statut=StatutTransaction.EN_ATTENTE, cree_le__gte=depuis
        )

    def recharges_expirees(self, avant: datetime):
        return self.filter(
            type=TypeTransaction.RECHARGE, statut=StatutTransaction.EN_ATTENTE, cree_le__lt=avant
        )

    def lister_admin(
        self,
        type_: str | None = None,
        statut: str | None = None,
        moyen: str | None = None,
        recherche: str | None = None,
        du: date | None = None,
        au: date | None = None,
    ):
        """Back-office. Retraits en attente : les plus anciens d'abord (à verser en premier)."""
        queryset = self.queryset().select_related("utilisateur")
        filtres = {"type": type_, "statut": statut, "moyen_paiement": moyen}
        queryset = queryset.filter(**{champ: v for champ, v in filtres.items() if v})
        if recherche:
            queryset = queryset.filter(
                Q(utilisateur__email__icontains=recherche)
                | Q(utilisateur__nom__icontains=recherche)
                | Q(utilisateur__prenom__icontains=recherche)
                | Q(telephone__icontains=recherche)
                | Q(reference_externe__icontains=recherche)
                | Q(reference_operateur__icontains=recherche)
            )
        if du:
            queryset = queryset.filter(cree_le__date__gte=du)
        if au:
            queryset = queryset.filter(cree_le__date__lte=au)
        a_verser = type_ == TypeTransaction.RETRAIT and statut == StatutTransaction.EN_ATTENTE
        return queryset.order_by("cree_le" if a_verser else "-cree_le")

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
