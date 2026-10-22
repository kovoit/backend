"""Lieux connus de départ (repris de la liste de l'équipe mobile, coordonnées approximatives).

À compléter et corriger dans le Django admin (Lieux connus). Idempotent : un lieu déjà présent
(même libellé et quartier) n'est pas modifié.
"""

import unicodedata

from django.db import migrations

LIEUX = [
    ("Carrefour Franciscain", "Adidogomé", "carrefour", 6.1660, 1.1650),
    ("Carrefour Avedji", "Avedji", "carrefour", 6.1690, 1.1840),
    ("Carrefour Totsi", "Totsi", "carrefour", 6.1780, 1.1980),
    ("Université de Lomé · Entrée sud", "Tokoin", "repere", 6.1680, 1.2140),
    ("Grand Marché", "Assigamé", "repere", 6.1300, 1.2230),
    ("Carrefour Déckon", "Centre-ville", "carrefour", 6.1310, 1.2180),
    ("CHU Sylvanus Olympio", "Tokoin", "repere", 6.1350, 1.2160),
    ("Agoè-Zongo", "Agoè", "carrefour", 6.2200, 1.2050),
    ("Agoè Assiyéyé", "Agoè", "quartier", 6.2290, 1.2120),
    ("Bè Kpota", "Bè", "quartier", 6.1420, 1.2420),
    ("Port autonome", "Zone portuaire", "repere", 6.1360, 1.2850),
    ("Baguida centre", "Baguida", "quartier", 6.1530, 1.3200),
    ("Hédzranawoé", "Hédzranawoé", "quartier", 6.1590, 1.2420),
    ("Stade de Kégué", "Kégué", "repere", 6.1810, 1.2490),
    ("Tokoin Hôpital", "Tokoin", "carrefour", 6.1450, 1.2140),
]


def _normaliser(texte: str) -> str:
    # Copie figée de apps.lieux.models.normaliser (une migration ne dépend pas du code vivant)
    decompose = unicodedata.normalize("NFKD", texte.casefold())
    return "".join(c for c in decompose if not unicodedata.combining(c)).strip()


def creer(apps, schema_editor):
    Lieu = apps.get_model("lieux", "Lieu")
    for libelle, quartier, type_lieu, lat, lng in LIEUX:
        Lieu.objects.get_or_create(
            libelle=libelle,
            quartier=quartier,
            defaults={
                "type": type_lieu,
                "lat": lat,
                "lng": lng,
                "recherche": _normaliser(f"{libelle} {quartier}"),
            },
        )


class Migration(migrations.Migration):
    dependencies = [("lieux", "0001_initial")]

    operations = [migrations.RunPython(creer, migrations.RunPython.noop)]
