from django.core.management.base import BaseCommand

from apps.parametres.services import initialiser_parametres


class Command(BaseCommand):
    help = "Crée les paramètres manquants avec leur valeur de départ (n'écrase rien)."

    def handle(self, *args, **options):
        crees = initialiser_parametres()
        self.stdout.write(self.style.SUCCESS(f"{crees} paramètre(s) créé(s)."))
