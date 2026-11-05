"""Données de démonstration (dev local) : commande `seed_backoffice`, 30 jours d'activité."""

from django.db.models import Q

# Comptes fictifs : seed_backoffice (prenom.nom@demo.kovoit.tg) et seed_demo (prenom.demo@kovoit.tg)
COMPTES_DEMO = Q(email__iendswith="@demo.kovoit.tg") | Q(email__iendswith=".demo@kovoit.tg")

# Mot de passe commun à tous les comptes de démo de l'app (seed_demo, seed_backoffice), à dicter
# en démo. Conforme aux 4 validateurs (similarité email / prénom / nom comprise) ; volontairement
# différent du mot de passe du FakeBackend mobile, présent dans l'APK. Jamais l'admin.
DEMO_MOT_DE_PASSE = "Kovoit-Demo-2026"
