"""Supprime les données de démonstration créées par `seed_demo` et `seed_backoffice`.

Seuls les comptes de démo (…@demo.kovoit.tg, ….demo@kovoit.tg) et tout ce qui s'y rattache
sont supprimés : les administrateurs, les paramètres et les vraies données sont conservés.
Développement uniquement : refusé quand DEBUG=False.

Usage : manage.py purger_demo            (affiche le bilan, demande confirmation)
        manage.py purger_demo --oui      (sans confirmation)
        manage.py purger_demo --simuler  (affiche le bilan, ne supprime rien)
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.dashboard.demo.purge import inventaire, purger

LIBELLES = {
    "comptes": "comptes de démo",
    "trajets": "trajets",
    "reservations": "réservations",
    "transactions": "transactions du portefeuille",
    "pieces_kyc": "pièces KYC",
    "codes_otp": "codes OTP",
}


class Command(BaseCommand):
    help = "Supprime les données de démonstration (seed_demo, seed_backoffice)."

    def add_arguments(self, parser):
        parser.add_argument("--oui", action="store_true", help="Ne pas demander de confirmation.")
        parser.add_argument("--simuler", action="store_true", help="Afficher sans supprimer.")

    def handle(self, *args, oui=False, simuler=False, **options):
        if not settings.DEBUG:
            raise CommandError("purger_demo est réservé au développement (DJANGO_DEBUG=True).")

        bilan = inventaire()
        if not bilan["comptes"]:
            self.stdout.write(self.style.SUCCESS("Aucune donnée de démo : rien à supprimer."))
            return
        self.stdout.write("Données de démo trouvées :")
        for cle, libelle in LIBELLES.items():
            self.stdout.write(f"  - {bilan[cle]} {libelle}")
        if simuler:
            self.stdout.write("Simulation : rien n'a été supprimé.")
            return
        if not oui and input("Supprimer définitivement ces données ? [oui/non] ").strip() != "oui":
            self.stdout.write("Annulé : rien n'a été supprimé.")
            return

        bilan = purger()
        self.stdout.write(
            self.style.SUCCESS(
                f"Supprimé : {bilan['comptes']} comptes, {bilan['trajets']} trajets, "
                f"{bilan['reservations']} réservations, {bilan['transactions']} transactions, "
                f"{bilan['fichiers']} fichiers."
            )
        )
