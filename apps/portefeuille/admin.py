from django.contrib import admin, messages

from apps.core.exceptions import ErreurMetier
from apps.portefeuille import services
from apps.portefeuille.models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Consultation du journal ; seuls les retraits en attente se traitent (versement manuel
    tant que le versement automatique PayGate n'est pas branché). Tout passe par le service,
    donc par le journal d'audit."""

    list_display = ["cree_le", "utilisateur", "type", "montant", "statut", "moyen_paiement",
                    "telephone", "reference_externe", "reference_operateur"]  # fmt: skip
    list_filter = ["type", "statut", "moyen_paiement"]
    search_fields = ["utilisateur__email", "reference_externe", "reference_operateur", "telephone"]
    actions = ["marquer_verse", "refuser_retrait"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def _traiter(self, request, queryset, verse: bool):
        for ligne in queryset:
            try:
                services.traiter_retrait(request.user, ligne.id, verse=verse)
            except ErreurMetier as erreur:
                self.message_user(request, f"{ligne} : {erreur.message}", messages.WARNING)

    @admin.action(description="Retrait versé sur Flooz / Mixx")
    def marquer_verse(self, request, queryset):
        self._traiter(request, queryset, verse=True)

    @admin.action(description="Refuser le retrait (le montant redevient disponible)")
    def refuser_retrait(self, request, queryset):
        self._traiter(request, queryset, verse=False)
