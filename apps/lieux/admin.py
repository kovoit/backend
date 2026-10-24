from django import forms
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from apps.lieux.models import Lieu

# Grand Lomé (large) : refuse une coordonnée tapée de travers (inversion lat/lng, Ghana…)
LAT_LOME = (6.05, 6.35)
LNG_LOME = (1.05, 1.45)


class LieuForm(forms.ModelForm):
    class Meta:
        model = Lieu
        fields = ["libelle", "quartier", "type", "lat", "lng", "actif", "verifie_le"]

    def clean(self):
        donnees = super().clean()
        lat, lng = donnees.get("lat"), donnees.get("lng")
        if lat is not None and not LAT_LOME[0] <= lat <= LAT_LOME[1]:
            self.add_error(
                "lat", f"Hors de Lomé : latitude attendue entre {LAT_LOME[0]} et {LAT_LOME[1]}."
            )
        if lng is not None and not LNG_LOME[0] <= lng <= LNG_LOME[1]:
            self.add_error(
                "lng", f"Hors de Lomé : longitude attendue entre {LNG_LOME[0]} et {LNG_LOME[1]}."
            )
        return donnees


@admin.register(Lieu)
class LieuAdmin(admin.ModelAdmin):
    """Référentiel des lieux proposés dans l'app : ajouter, corriger, désactiver, et noter ceux
    dont la position a été vérifiée sur place ou sur une carte."""

    form = LieuForm
    list_display = ["libelle", "quartier", "type", "lat", "lng", "carte", "verifie_le", "actif"]
    list_filter = ["type", "actif", ("verifie_le", admin.EmptyFieldListFilter)]
    search_fields = ["libelle", "quartier"]
    list_editable = ["actif"]
    actions = ["marquer_verifie"]

    @admin.display(description="Carte")
    def carte(self, lieu: Lieu):
        url = f"https://www.openstreetmap.org/?mlat={lieu.lat}&mlon={lieu.lng}#map=18/{lieu.lat}/{lieu.lng}"
        return format_html(
            '<a href="{}" target="_blank" rel="noreferrer">Voir sur la carte</a>', url
        )

    @admin.action(description="Position vérifiée (aujourd'hui)")
    def marquer_verifie(self, request, queryset):
        nombre = queryset.update(verifie_le=timezone.now())
        self.message_user(request, f"{nombre} lieu(x) marqué(s) comme vérifié(s).")

    def has_delete_permission(self, request, obj=None):
        return False  # désactiver plutôt que supprimer
