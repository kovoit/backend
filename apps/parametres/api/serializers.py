from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.parametres.defauts import DECIMAL, ENTIER, PARAMETRES_PAR_DEFAUT
from apps.parametres.models import Parametre


class ParametreSerializer(serializers.ModelSerializer):
    type_valeur = serializers.SerializerMethodField()
    modifie_par = serializers.UUIDField(source="modifie_par_id", read_only=True, allow_null=True)

    class Meta:
        model = Parametre
        fields = ["cle", "valeur", "type_valeur", "description", "modifie_le", "modifie_par"]
        read_only_fields = fields

    @extend_schema_field(serializers.ChoiceField(choices=[ENTIER, DECIMAL], allow_null=True))
    def get_type_valeur(self, parametre: Parametre) -> str | None:
        defaut = PARAMETRES_PAR_DEFAUT.get(parametre.cle)
        return defaut.type_valeur if defaut else None


class ModificationParametreSerializer(serializers.Serializer):
    valeur = serializers.JSONField(help_text="Nouvelle valeur (nombre).")
