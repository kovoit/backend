from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.forms import CreationUtilisateurForm, ModificationUtilisateurForm
from apps.accounts.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = CreationUtilisateurForm
    form = ModificationUtilisateurForm
    ordering = ["-cree_le"]
    list_display = ["email", "prenom", "nom", "telephone", "mode_actif", "statut_compte"]
    list_filter = ["statut_compte", "mode_actif", "email_verifie", "is_staff"]
    search_fields = ["email", "nom", "prenom", "telephone"]
    readonly_fields = ["cree_le", "modifie_le", "last_login"]
    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("Profil", {"fields": ["prenom", "nom", "telephone", "photo", "mode_actif"]}),
        ("Statut", {"fields": ["email_verifie", "statut_compte", "suspendu_jusqu_au"]}),
        ("Droits", {"fields": ["is_active", "is_staff", "is_superuser", "groups"]}),
        ("Dates", {"fields": ["cree_le", "modifie_le", "last_login"]}),
    ]
    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": ["email", "prenom", "nom", "telephone", "password1", "password2"],
            },
        ),
    ]
