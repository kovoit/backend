from django import forms
from django.contrib import admin

from apps.core.exceptions import ErreurMetier
from apps.parametres import services
from apps.parametres.models import Parametre


class ParametreForm(forms.ModelForm):
    class Meta:
        model = Parametre
        fields = ["valeur"]

    def clean_valeur(self):
        valeur = self.cleaned_data["valeur"]
        try:
            services.valider_valeur(self.instance.cle, valeur)
        except ErreurMetier as exc:
            raise forms.ValidationError(exc.message) from exc
        return valeur


@admin.register(Parametre)
class ParametreAdmin(admin.ModelAdmin):
    form = ParametreForm
    list_display = ["cle", "valeur", "description", "modifie_le", "modifie_par"]
    search_fields = ["cle", "description"]
    fields = ["cle", "valeur", "description", "modifie_le", "modifie_par"]
    readonly_fields = ["cle", "description", "modifie_le", "modifie_par"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        services.modifier_param(obj.cle, form.cleaned_data["valeur"], par=request.user)
