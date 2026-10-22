"""Données de démonstration (dev local) : commande `seed_backoffice`, 30 jours d'activité."""

from django.db.models import Q

# Comptes fictifs : seed_backoffice (prenom.nom@demo.kovoit.tg) et seed_demo (prenom.demo@kovoit.tg)
COMPTES_DEMO = Q(email__iendswith="@demo.kovoit.tg") | Q(email__iendswith=".demo@kovoit.tg")
