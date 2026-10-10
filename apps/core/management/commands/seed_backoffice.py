"""Remplit la base locale avec 30 jours d'activité fictive, via les services métier.

Développement uniquement : refusé quand DEBUG=False. Pour recommencer : `manage.py flush`.
"""

import random
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test import override_settings
from django.utils import timezone
from freezegun import freeze_time

from apps.accounts import services as comptes
from apps.accounts.repository import user_repository
from apps.confiance import services as confiance
from apps.core.demo import personnes
from apps.core.demo.activite import a_heure, demander, journee, publier
from apps.portefeuille import services as portefeuille
from apps.reservations import services as reservations

JOURS = 30
NB_CONDUCTEURS = 8
NB_PERSONNES = 24
# Issue des dossiers KYC selon l'index de la personne (absent : dossier non soumis)
REJETS = {
    7: "Permis de conduire expiré : merci d'envoyer un permis en cours de validité.",
    22: "Selfie flou : le visage n'est pas reconnaissable.",
}
EN_ATTENTE = {6, 20, 21}


class Command(BaseCommand):
    help = "Crée des données de démonstration (utilisateurs, KYC, trajets, réservations…)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_backoffice est réservé au développement (DEBUG=True).")
        if user_repository.exists(email__endswith=f"@{personnes.DOMAINE}"):
            raise CommandError("Données de démo déjà présentes. Repartir de zéro : manage.py flush")
        admin = user_repository.filter(is_staff=True).first()
        if admin is None:
            raise CommandError("Créez d'abord un administrateur : manage.py createsuperuser")

        # Pas d'appel réseau (OSRM) ni de notification push pendant la génération
        with override_settings(
            ROUTAGE_PROVIDER="apps.routage.providers.FakeRoutingProvider",
            NOTIFICATIONS_PUSH_SENDER="apps.notifications.push.FakePushSender",
        ):
            compteur = self._generer(admin, random.Random(2026))
        self.stdout.write(self.style.SUCCESS(f"Données de démo créées : {compteur}"))

    def _generer(self, admin, rng: random.Random) -> dict:
        maintenant = timezone.now()
        aujourd_hui = timezone.localdate()
        compteur = {"trajets": 0, "litiges": 0, "en_attente_confirmation": 0}
        with freeze_time(maintenant - timedelta(days=JOURS + 10)) as horloge:
            conducteurs, passagers = self._personnes(admin, horloge)
            for decalage in range(JOURS, 0, -1):
                jour = aujourd_hui - timedelta(days=decalage)
                recent = decalage <= 2
                journee(jour, horloge, conducteurs, passagers, rng, compteur, recent)
            horloge.move_to(maintenant)
            self._a_venir(conducteurs, passagers, rng)
            self._traitements_admin(admin)
        compteur["utilisateurs"] = NB_PERSONNES
        return compteur

    def _personnes(self, admin, horloge):
        conducteurs, passagers = [], []
        for index in range(NB_PERSONNES):
            personne = personnes.creer_personne(index)
            types = ["conducteur", "passager"] if index < NB_CONDUCTEURS else ["passager"]
            if index < NB_CONDUCTEURS:
                personnes.declarer_voiture(personne, index)
            for type_dossier in types if index != 23 else []:
                if index in EN_ATTENTE and type_dossier == types[0]:
                    continue  # soumis plus tard, laissé en attente
                dossier = personnes.soumettre_dossier(personne, type_dossier)
                motif = REJETS.get(index) if type_dossier == types[0] else None
                personnes.traiter_dossier(dossier, admin, motif)
            if index < NB_CONDUCTEURS and index not in EN_ATTENTE and index not in REJETS:
                conducteurs.append(personne)
            elif index not in EN_ATTENTE and index not in REJETS and index != 23:
                portefeuille.recharger(personne, 20_000, "flooz")
                passagers.append(personne)
            horloge.tick(timedelta(hours=3))
        return conducteurs, passagers

    def _a_venir(self, conducteurs, passagers, rng):
        """Trajets publiés pour plus tard, dossiers KYC récemment soumis."""
        for numero, conducteur in enumerate(conducteurs[:3]):
            depart = a_heure(timezone.localdate() + timedelta(days=1), 7, 30 + numero * 10)
            trajet = publier(conducteur, numero, depart)
            for passager in rng.sample(passagers, k=2):
                reservation = demander(passager, trajet, rng)
                if numero != 0:
                    reservations.accepter(conducteur, reservation.id)
        for index in sorted(EN_ATTENTE):
            personne = user_repository.get_par_email(personnes.email_de(index))
            personnes.soumettre_dossier(personne, "conducteur" if index < 8 else "passager")

    def _traitements_admin(self, admin):
        """Un signalement déjà tranché par l'admin, un compte suspendu."""
        signalement = confiance.lister_signalements("ouvert").first()
        if signalement is not None:
            confiance.traiter_signalement(
                admin,
                signalement.id,
                "Trajet vérifié avec les deux parties : le conducteur est payé.",
                "crediter_conducteur",
            )
        suspendu = user_repository.get_par_email(personnes.email_de(19))
        comptes.suspendre_par_admin(
            suspendu, "Signalement d'un comportement dangereux au volant.", 7
        )
