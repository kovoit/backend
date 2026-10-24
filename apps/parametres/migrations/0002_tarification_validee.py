"""Valeurs de tarification validées par Kovoit le 24/10/2026, appliquées aux bases existantes.

`seed_parametres` ne remplace jamais une valeur en base : sans cette migration, une base créée
avant la validation garde les anciennes valeurs de départ. Seules les valeurs encore égales à
l'ancienne valeur de départ sont modifiées ; une valeur changée par un administrateur est
conservée. Les trajets déjà publiés gardent leur prix (figé à la publication).
"""

from django.core.cache import cache
from django.db import migrations

# clé : (ancienne valeur de départ, valeur validée)
VALEURS = {
    "consommation_voiture_l_100km": (7.0, 8.0),
    "consommation_moto_l_100km": (2.5, 3.0),
    "cout_horaire_conducteur": (0, 300),
    "entretien_voiture_par_km": (0, 15),
    "entretien_moto_par_km": (0, 5),
}


def _egal(valeur, attendue) -> bool:
    try:
        return float(valeur) == float(attendue)
    except (TypeError, ValueError):
        return False


def appliquer(apps, schema_editor):
    Parametre = apps.get_model("parametres", "Parametre")
    for cle, (ancienne, validee) in VALEURS.items():
        parametre = Parametre.objects.filter(cle=cle).first()
        if parametre is not None and _egal(parametre.valeur, ancienne):
            parametre.valeur = validee
            parametre.save(update_fields=["valeur", "modifie_le"])
            cache.delete(f"parametre:{cle}")  # même clé que services._cle_cache


class Migration(migrations.Migration):
    dependencies = [("parametres", "0001_initial")]

    operations = [migrations.RunPython(appliquer, migrations.RunPython.noop)]
