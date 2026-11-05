"""Accélération du temps pour tester un trajet de bout en bout (dev local, commande
`avancer_trajet`).

Au lieu de changer l'horloge du serveur, on recule les horaires d'UN trajet : son départ, sa
dernière position et les horodatages de ses réservations. Tout se passe comme si le temps avait
avancé pour ce trajet. Les tâches planifiées (expiration, clôture automatique) sont ensuite
lancées tout de suite, sans attendre celery beat. Elles sont globales : elles traitent toute la
base, comme celery beat, pas seulement ce trajet. Le recul n'est pas journalisé dans l'audit
(outil de dev, comme les commandes `seed_*`).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import ActionInterdite, RessourceIntrouvable
from apps.reservations import services as reservations
from apps.reservations.repository import reservation_repository
from apps.trajets.repository import trajet_repository


@dataclass(frozen=True)
class Avance:
    trajet_id: str
    minutes: int
    depart_le: datetime
    expirees: int
    cloturees: int


def trajet_a_avancer(trajet_id=None):
    """Le trajet demandé, ou à défaut le dernier trajet non clos créé."""
    if trajet_id:
        return trajet_repository.get_by_id(trajet_id)
    trajet = trajet_repository.dernier_non_clos()
    if trajet is None:
        raise RessourceIntrouvable("Aucun trajet publié, complet ou en cours.")
    return trajet


def avancer_trajet(trajet_id=None, minutes: int | None = None) -> Avance:
    """Avance le temps de `minutes` pour un trajet ; sans `minutes`, jusqu'à l'heure de départ
    (0 min si le départ est déjà passé : seules les tâches planifiées tournent)."""
    if not settings.DEBUG:
        raise ActionInterdite("avancer_trajet est réservé au développement (DJANGO_DEBUG=True).")
    trajet = trajet_a_avancer(trajet_id)
    with transaction.atomic():
        trajet = trajet_repository.get_verrouille(trajet.id)
        if minutes is None:
            restant = trajet.depart_le - timezone.now()
            minutes = max(0, int(restant.total_seconds() // 60) + 1)
        delta = timedelta(minutes=minutes)
        trajet_repository.reculer_horaires(trajet.id, delta)
        reservation_repository.reculer_horodatages(trajet.id, delta)
    expirees = reservations.expirer_reservations()
    cloturees = reservations.cloturer_automatiquement()
    trajet = trajet_repository.get_by_id(trajet.id)
    return Avance(str(trajet.id), minutes, trajet.depart_le, expirees, cloturees)
