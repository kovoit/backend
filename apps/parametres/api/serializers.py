from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.api.serializers import AdminResumeSerializer
from apps.parametres.defauts import DECIMAL, ENTIER, GROUPES, PARAMETRES_PAR_DEFAUT, Defaut
from apps.parametres.models import Parametre


class GroupeSerializer(serializers.Serializer):
    code = serializers.ChoiceField(choices=list(GROUPES))
    libelle = serializers.CharField()


class ParametreSerializer(serializers.ModelSerializer):
    """Valeur en base + métadonnées du registre (type, thème, unité, minimum)."""

    type_valeur = serializers.SerializerMethodField()
    groupe = serializers.SerializerMethodField()
    unite = serializers.SerializerMethodField()
    minimum = serializers.SerializerMethodField()
    modifie_par = AdminResumeSerializer(read_only=True, allow_null=True)

    class Meta:
        model = Parametre
        fields = [
            "cle",
            "valeur",
            "type_valeur",
            "description",
            "groupe",
            "unite",
            "minimum",
            "modifie_le",
            "modifie_par",
        ]
        read_only_fields = fields

    @staticmethod
    def _defaut(parametre: Parametre) -> Defaut:
        return PARAMETRES_PAR_DEFAUT[parametre.cle]

    @extend_schema_field(serializers.ChoiceField(choices=[ENTIER, DECIMAL]))
    def get_type_valeur(self, parametre: Parametre) -> str:
        return self._defaut(parametre).type_valeur

    @extend_schema_field(GroupeSerializer)
    def get_groupe(self, parametre: Parametre) -> dict:
        code = self._defaut(parametre).groupe
        return {"code": code, "libelle": GROUPES[code]}

    def get_unite(self, parametre: Parametre) -> str:
        return self._defaut(parametre).unite

    @extend_schema_field(serializers.FloatField())
    def get_minimum(self, parametre: Parametre) -> int | float:
        return self._defaut(parametre).minimum


class ModificationParametreSerializer(serializers.Serializer):
    valeur = serializers.JSONField(help_text="Nouvelle valeur (nombre).")
