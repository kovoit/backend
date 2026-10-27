from django.contrib import admin

from apps.accounts.roles import FINANCE, roles_de
from apps.portefeuille.models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Consultation seule du journal, réservée au rôle Finance (et aux superutilisateurs).
    Le versement et le refus des retraits se font dans le back-office React, écrits au
    journal d'audit (D-38)."""

    list_display = ["cree_le", "utilisateur", "type", "montant", "statut", "moyen_paiement",
                    "telephone", "reference_externe", "reference_operateur"]  # fmt: skip
    list_filter = ["type", "statut", "moyen_paiement"]
    search_fields = ["utilisateur__email", "reference_externe", "reference_operateur", "telephone"]

    def has_module_permission(self, request):
        return FINANCE in roles_de(request.user) and super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        return FINANCE in roles_de(request.user) and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
