"""D-63 : les numéros déjà enregistrés passent à la forme +228XXXXXXXX (D-62).

Seuls les mobiles togolais lisibles (D-64, D-65 : 8 chiffres commençant par 7 ou 9) sont convertis ;
les autres, fixes compris, restent inchangés (aucune perte) et leur nombre est affiché.
Rejouable sans effet. Retour arrière sans effet (noop) : l'ancienne saisie n'est pas conservée ;
la forme +228XXXXXXXX reste valide avec l'ancienne règle."""

import re

from django.db import migrations

# Figée : copie de apps/core/telephone.py au moment de la migration (ne pas l'importer)
SEPARATEURS = re.compile(
    r"[\s\-.()"
    r"\u2010-\u2015\u2212"  # tirets Unicode, signe moins (D-65)
    r"\u200b-\u200f\u202a-\u202e\u2066-\u2069"  # largeur nulle, marques bidirectionnelles
    r"\u2060\ufeff]"  # gluon de mots, BOM
)
FORMAT = re.compile(r"(?:\+228|00228|228)?([79][0-9]{7})")


def lire(saisie: str) -> str | None:
    if len(saisie) > 32:
        return None
    correspondance = FORMAT.fullmatch(SEPARATEURS.sub("", saisie))
    return "+228" + correspondance.group(1) if correspondance else None


def convertir_telephones(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    a_convertir, illisibles = [], 0
    for compte in User.objects.exclude(telephone="").only("id", "telephone").iterator():
        forme = lire(compte.telephone)
        if forme is None:
            illisibles += 1
        elif forme != compte.telephone:
            compte.telephone = forme
            a_convertir.append(compte)
    User.objects.bulk_update(a_convertir, ["telephone"], batch_size=500)
    if a_convertir or illisibles:
        print(
            f"\n  Téléphones : {len(a_convertir)} convertis au format +228XXXXXXXX, "
            f"{illisibles} illisibles laissés inchangés."
        )


class Migration(migrations.Migration):
    dependencies = [("accounts", "0006_roles_admins_existants")]

    operations = [migrations.RunPython(convertir_telephones, migrations.RunPython.noop)]
