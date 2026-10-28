"""Formulaires du Django admin (backoffice interne) pour le modèle User à email."""

from django import forms
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm

from apps.accounts.models import User
from apps.core.telephone import TelephoneInvalide, normaliser_telephone


def champ_telephone() -> forms.CharField:
    return forms.CharField(
        label="téléphone",
        required=False,
        max_length=32,
        help_text="Mobile togolais à 8 chiffres commençant par 7 ou 9, +228 facultatif "
        "(ex. 90 11 22 33).",
    )


def nettoyer_telephone(formulaire: forms.ModelForm) -> str:
    """Même règle que l'API (D-62) : saisie libre lue puis enregistrée en +228XXXXXXXX.

    Un ancien numéro illisible (laissé tel quel par la migration 0007) reste accepté tant
    qu'on n'y touche pas : modifier un autre champ de la fiche ne bloque pas."""
    saisie = formulaire.cleaned_data.get("telephone", "")
    if not saisie:
        return ""
    if not formulaire.instance._state.adding and "telephone" not in formulaire.changed_data:
        return formulaire.instance.telephone
    try:
        return normaliser_telephone(saisie)
    except TelephoneInvalide as erreur:
        raise forms.ValidationError(erreur.message, code="telephone_invalide") from erreur


class CreationUtilisateurForm(BaseUserCreationForm):
    telephone = champ_telephone()

    class Meta:
        model = User
        fields = ("email", "prenom", "nom", "telephone")

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_telephone(self) -> str:
        return nettoyer_telephone(self)


class ModificationUtilisateurForm(UserChangeForm):
    telephone = champ_telephone()

    class Meta:
        model = User
        fields = "__all__"

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_telephone(self) -> str:
        return nettoyer_telephone(self)
