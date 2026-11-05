from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.accounts.forms import CreationUtilisateurForm, ModificationUtilisateurForm
from apps.accounts.models import User


def est_compte_protege(request, obj) -> bool:
    """Compte staff ou superutilisateur d'un autre que soi : intouchable pour un
    non-superutilisateur (fiche, mot de passe, suppression unitaire ou en masse)."""
    if obj is None or request.user.is_superuser or obj.pk == request.user.pk:
        return False
    return obj.is_staff or obj.is_superuser


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
    # Droits d'administration : modifiables par un superutilisateur seulement (D-37)
    champs_de_droits = ["is_staff", "is_superuser", "groups"]
    # Sur sa propre fiche, un non-superutilisateur ne touche pas non plus à ces champs
    champs_du_compte = ["email", "is_active"]

    def get_readonly_fields(self, request, obj=None):
        champs = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            champs += self.champs_de_droits
            if obj is not None and obj.pk == request.user.pk:
                champs += self.champs_du_compte
        return champs

    def has_change_permission(self, request, obj=None):
        if est_compte_protege(request, obj):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if est_compte_protege(request, obj):
            return False
        return super().has_delete_permission(request, obj)

    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": ["email", "prenom", "nom", "telephone", "password1", "password2"],
            },
        ),
    ]


# Jetons de la liste noire SimpleJWT : écrans retirés du Django admin, pour tous.
# OutstandingToken affiche le refresh complet (vol de session) et BlacklistedToken
# permet de réactiver un refresh révoqué. La révocation passe par la déconnexion et
# la rotation, jamais par l'admin. token_blacklist précède apps.accounts dans
# INSTALLED_APPS, donc son admin est déjà chargé ici (sinon NotRegistered au démarrage).
admin.site.unregister(OutstandingToken)
admin.site.unregister(BlacklistedToken)

admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin):
    """Les rôles reposent sur le nom des groupes : seul un superutilisateur crée, renomme,
    modifie les permissions ou supprime un groupe (D-37). Consultation selon la permission."""

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
