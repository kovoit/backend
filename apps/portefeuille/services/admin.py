"""Back-office : journal des transactions et retraits à verser."""

from apps.portefeuille.models import Transaction
from apps.portefeuille.repository import transaction_repository


def lister_transactions(**filtres):
    return transaction_repository.lister_admin(**filtres)


def get_transaction(transaction_id) -> Transaction:
    return transaction_repository.get_by_id(transaction_id)
