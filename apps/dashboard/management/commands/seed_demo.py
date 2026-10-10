"""Données de démonstration pour tester l'API dans Swagger (développement uniquement).

Crée (sans doublon si relancée) un passager et un conducteur déjà vérifiés, un véhicule,
un trajet publié pour demain, et affiche des jetons JWT prêts à coller dans « Authorize ».
Pour remplir le back-office React avec un mois d'activité, utiliser plutôt `seed_backoffice`.
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.repository import user_repository
from apps.kyc.models import StatutKyc, TypeDossier
from apps.kyc.repository import dossier_repository
from apps.portefeuille import services as portefeuille
from apps.trajets import services as trajets
from apps.trajets.repository import trajet_repository
from apps.vehicules import services as vehicules

PASSAGER = {
    "email": "afi.demo@kovoit.tg",
    "prenom": "Afi",
    "nom": "Mensah",
    "telephone": "+22890111111",
}
CONDUCTEUR = {
    "email": "kodjo.demo@kovoit.tg",
    "prenom": "Kodjo",
    "nom": "Agbeko",
    "telephone": "+22890222222",
}


class Command(BaseCommand):
    help = "Crée des comptes et un trajet de démonstration (DEBUG uniquement)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo est réservé au développement (DJANGO_DEBUG=True).")

        passager = self._compte(PASSAGER, [TypeDossier.PASSAGER])
        conducteur = self._compte(CONDUCTEUR, [TypeDossier.PASSAGER, TypeDossier.CONDUCTEUR])
        if portefeuille.solde(passager).disponible < 1000:
            portefeuille.recharger(passager, 5000, "flooz")
        vehicule = vehicules.mes_vehicules(conducteur).first() or vehicules.declarer(
            conducteur,
            type_vehicule="voiture",
            marque="Toyota",
            modele="Corolla",
            couleur="Grise",
            immatriculation="TG0001DM",
            nb_places=5,
        )
        trajet = self._trajet(conducteur, vehicule)

        self.stdout.write(self.style.SUCCESS("Données de démonstration prêtes.\n"))
        for role, utilisateur in (("PASSAGER", passager), ("CONDUCTEUR", conducteur)):
            jetons = RefreshToken.for_user(utilisateur)
            self.stdout.write(f"{role} : {utilisateur.email}")
            self.stdout.write(f"  access  : {jetons.access_token}")
            self.stdout.write(f"  refresh : {jetons}\n")
        point = trajet.points.first()
        self.stdout.write(
            f"Trajet {trajet.id} — départ {timezone.localtime(trajet.depart_le):%d/%m %H:%M}"
        )
        self.stdout.write(f"  point de prise en charge : {point.id}")
        self.stdout.write(
            "  recherche : depart_lat=6.1748&depart_lng=1.1695&arrivee_lat=6.1305"
            f"&arrivee_lng=1.2220&date_heure={trajet.depart_le.isoformat()}"
        )

    def _compte(self, donnees: dict, dossiers: list[str]):
        utilisateur, _ = user_repository.get_ou_creer(donnees["email"])
        champs = {k: v for k, v in donnees.items() if k != "email"}
        utilisateur = user_repository.update(utilisateur, email_verifie=True, **champs)
        for type_dossier in dossiers:
            dossier = dossier_repository.get_ou_creer(utilisateur, type_dossier)
            dossier_repository.update(dossier, statut=StatutKyc.VERIFIE)
        return utilisateur

    def _trajet(self, conducteur, vehicule):
        existant = trajet_repository.a_venir_de_conducteur(conducteur, timezone.now()).first()
        if existant:
            return existant
        demain = timezone.localtime() + timedelta(days=1)
        return trajets.publier(
            conducteur,
            vehicule_id=vehicule.id,
            depart_lat=6.1745,
            depart_lng=1.1690,
            depart_libelle="Adidogomé",
            arrivee_lat=6.1300,
            arrivee_lng=1.2220,
            arrivee_libelle="Grand Marché",
            depart_le=demain.replace(hour=7, minute=30, second=0, microsecond=0),
            places=3,
            points=[{"lat": 6.1750, "lng": 1.1700, "libelle": "Carrefour Adidogomé"}],
        )
