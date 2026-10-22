from django.contrib import admin

from apps.audit.models import EvenementAudit


@admin.register(EvenementAudit)
class EvenementAuditAdmin(admin.ModelAdmin):
    """Consultation seule : le journal est en ajout seul, y compris depuis le Django admin."""

    list_display = ["enregistre_le", "action", "resultat", "categorie", "canal", "acteur_role"]
    list_filter = ["categorie", "resultat", "canal", "gravite"]
    search_fields = ["action", "ressource_id", "request_id", "code_motif"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
