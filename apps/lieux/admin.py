from django.contrib import admin

from apps.lieux.models import Lieu


@admin.register(Lieu)
class LieuAdmin(admin.ModelAdmin):
    """Référentiel des lieux proposés dans l'app : ajouter, corriger, désactiver."""

    list_display = ["libelle", "quartier", "type", "lat", "lng", "actif"]
    list_filter = ["type", "actif"]
    search_fields = ["libelle", "quartier"]
    list_editable = ["actif"]

    def has_delete_permission(self, request, obj=None):
        return False  # désactiver plutôt que supprimer
