"""Formulaires du Django admin (backoffice interne) pour le modèle User à email."""

from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm

from apps.accounts.models import User


class CreationUtilisateurForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "prenom", "nom", "telephone")

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class ModificationUtilisateurForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()
