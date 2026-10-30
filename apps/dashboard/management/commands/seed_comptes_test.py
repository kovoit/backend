"""Crée ou remet à l'état voulu 4 comptes de test `@kovoit.test` (développement uniquement)."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.test import override_settings

from apps.dashboard.demo import DEMO_MOT_DE_PASSE, comptes_test


class Command(BaseCommand):
    help = (
        "Crée ou remet à l'état voulu 4 comptes de test (DEBUG uniquement, relançable sans "
        f"doublon), mot de passe {DEMO_MOT_DE_PASSE}, e-mail vérifié, CGU acceptées, photo : "
        "conducteur.verifie@kovoit.test (KYC passager + conducteur vérifiés, véhicule : publie "
        "et réserve) ; conducteur.attente@kovoit.test (véhicule, 2 dossiers KYC en attente) ; "
        "passager.verifie@kovoit.test (KYC passager vérifié : réserve) ; "
        "passager.attente@kovoit.test (KYC passager en attente). Les validations KYC sont "
        "faites au nom du superutilisateur (à défaut d'un autre admin ; sans admin, journal "
        "sans acteur). Aucun e-mail ni push n'est envoyé aux adresses fictives."
    )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_comptes_test est réservé au développement (DEBUG=True).")
        admin = comptes_test.admin_acteur()
        # Pas de notification réelle vers les adresses fictives
        with (
            override_settings(
                EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
                NOTIFICATIONS_PUSH_SENDER="apps.notifications.push.FakePushSender",
            ),
            transaction.atomic(),
        ):
            lignes = [comptes_test.preparer(compte, admin) for compte in comptes_test.COMPTES]
        self._tableau(lignes)
        acteur = admin.email if admin else "aucun admin (journal sans acteur, rôle anonyme)"
        self.stdout.write(f"Validations KYC faites par : {acteur}")

    def _tableau(self, lignes: list[dict]) -> None:
        self.stdout.write(self.style.SUCCESS("Comptes de test prêts.\n"))
        entete = f"{'Adresse':<32} {'Mot de passe':<18} {'KYC':<42} Débloque"
        self.stdout.write(entete)
        self.stdout.write("-" * len(entete))
        for ligne in lignes:
            kyc = ", ".join(f"{type_} {statut}" for type_, statut in ligne["kyc"].items())
            acces = ligne["acces"]
            drapeaux = (
                f"[réserver: {'oui' if acces['peut_reserver'] else 'non'}, "
                f"publier: {'oui' if acces['peut_publier'] else 'non'}]"
            )
            self.stdout.write(
                f"{ligne['utilisateur'].email:<32} {DEMO_MOT_DE_PASSE:<18} {kyc:<42} "
                f"{ligne['debloque']} {drapeaux}"
            )
