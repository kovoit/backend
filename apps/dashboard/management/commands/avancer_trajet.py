"""Avance le temps d'un trajet pour le tester sans attendre (DEBUG uniquement).

Usage : manage.py avancer_trajet                     (dernier trajet non clos, jusqu'au départ)
        manage.py avancer_trajet <trajet_id>         (ce trajet, jusqu'au départ)
        manage.py avancer_trajet --minutes 30        (avance de 30 min)
        manage.py avancer_trajet --heures 24         (avance de 24 h, ex. clôture automatique)

Les expirations et clôtures automatiques sont lancées juste après. Elles sont globales : elles
traitent toute la base, comme Celery beat, pas seulement ce trajet. Le recul n'est pas journalisé
dans l'audit (outil de dev, comme les commandes `seed_*`). Durée plafonnée à
`periode_incidents_j` jours : au-delà, la fiabilité et les économies du mois seraient faussées.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.core.exceptions import ErreurMetier
from apps.dashboard.demo.horloge import avancer_trajet
from apps.parametres.services import get_param


class Command(BaseCommand):
    help = (
        "Avance le temps d'un trajet (départ, réservations) puis lance les tâches planifiées. "
        "L'expiration et la clôture lancées sont globales (toute la base, comme Celery beat). "
        "Le recul n'est pas journalisé dans l'audit."
    )

    def add_arguments(self, parser):
        parser.add_argument("trajet_id", nargs="?", help="Défaut : dernier trajet non clos.")
        duree = parser.add_mutually_exclusive_group()
        duree.add_argument("--minutes", type=int, help="Minutes à avancer.")
        duree.add_argument("--heures", type=int, help="Heures à avancer.")

    def handle(self, *args, trajet_id=None, minutes=None, heures=None, **options):
        if not settings.DEBUG:
            raise CommandError("avancer_trajet est réservé au développement (DJANGO_DEBUG=True).")
        if heures is not None:
            minutes = heures * 60
        if minutes is not None:
            self._verifier_duree(minutes)
        try:
            avance = avancer_trajet(trajet_id, minutes)
        except ErreurMetier as exc:
            raise CommandError(str(exc)) from exc

        depart = timezone.localtime(avance.depart_le).strftime("%d/%m %H:%M")
        if avance.minutes == 0:
            self.stdout.write(
                "Départ déjà passé : utilisez --minutes ou --heures "
                f"(trajet {avance.trajet_id}, horaires inchangés)."
            )
        else:
            self.stdout.write(f"Trajet {avance.trajet_id} avancé de {avance.minutes} min.")
        self.stdout.write(f"Départ désormais le {depart}.")
        self.stdout.write(
            f"Expirées : {avance.expirees} · clôturées automatiquement : {avance.cloturees}."
        )
        self.stdout.write(
            "Rappels : absence possible "
            f"{get_param('tolerance_retard_min')} min après le départ ; "
            "demandes sans réponse refusées au départ ; places acceptées non résolues annulées "
            f"{get_param('delai_resolution_h')} h après le départ ; "
            f"clôture automatique {get_param('delai_confirmation_auto_h')} h après la fin."
        )

    def _verifier_duree(self, minutes: int) -> None:
        if minutes < 1:
            raise CommandError("La durée doit être d'au moins 1 minute.")
        jours = get_param("periode_incidents_j")
        if minutes > jours * 24 * 60:
            raise CommandError(
                f"Durée limitée à {jours * 24 * 60} min ({jours} jours, periode_incidents_j) : "
                "au-delà, les incidents sortent de la période de calcul, la fiabilité et les "
                "économies du mois seraient faussées."
            )
