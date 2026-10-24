"""Expiration automatique (tâche planifiée) : aucun montant ne reste bloqué indéfiniment.

- Demande sans réponse du conducteur à l'heure du départ : refusée, montant débloqué.
- Place acceptée sans code de départ ni absence `delai_resolution_h` après le départ :
  annulée sans incident pour personne, montant débloqué.
- Trajet que le conducteur n'a jamais terminé, `delai_resolution_h` après le départ : clos
  (passagers montés « terminée », donc clôture et paiement du conducteur ensuite).
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.audit.services import journaliser
from apps.parametres.services import get_param
from apps.portefeuille import services as portefeuille
from apps.reservations.models import StatutReservation as S
from apps.reservations.repository import reservation_repository
from apps.reservations.services.annulation import _annuler
from apps.reservations.services.commun import (
    libelle_trajet,
    notifier_conducteur,
    notifier_passager,
    transitionner,
)


def _journaliser(reservation, cause: str) -> None:
    journaliser(
        "reservation.expirer",
        ressource=reservation,
        systeme=True,
        categorie="metier",
        details={"cause": cause, "montant_debloque": reservation.montant_total},
    )


def _expirer_demande(reservation_id) -> bool:
    with transaction.atomic():
        reservation = reservation_repository.get_verrouillee(reservation_id)
        if reservation.statut != S.DEMANDEE:  # traitée entre-temps par le conducteur
            return False
        transitionner(reservation, S.REFUSEE)
        portefeuille.debloquer(reservation)
        _journaliser(reservation, "sans_reponse_du_conducteur")
    notifier_passager(
        reservation,
        "Demande expirée",
        f"Le conducteur n'a pas répondu à votre demande pour {libelle_trajet(reservation)}. "
        "Le montant bloqué vous a été rendu.",
    )
    return True


def _expirer_acceptee(reservation_id) -> bool:
    with transaction.atomic():
        reservation = reservation_repository.get_verrouillee(reservation_id)
        if reservation.statut != S.ACCEPTEE:  # code saisi ou absence déclarée entre-temps
            return False
        _annuler(reservation, auteur=None, compter_incident=False)
        _journaliser(reservation, "prise_en_charge_non_confirmee")
    message = (
        f"Ni code de départ ni absence n'ont été enregistrés pour {libelle_trajet(reservation)} : "
        "la réservation est annulée."
    )
    notifier_passager(reservation, "Réservation annulée", f"{message} Le montant vous a été rendu.")
    notifier_conducteur(reservation, "Réservation annulée", message)
    return True


def expirer_reservations() -> int:
    """Renvoie le nombre de réservations expirées."""
    maintenant = timezone.now()
    limite = maintenant - timedelta(hours=get_param("delai_resolution_h"))
    nombre = 0
    for reservation in reservation_repository.demandes_sans_reponse(maintenant):
        nombre += _expirer_demande(reservation.id)
    for reservation in reservation_repository.acceptees_non_resolues(limite):
        nombre += _expirer_acceptee(reservation.id)
    from apps.trajets.repository import trajet_repository
    from apps.trajets.services import clore_trajet_abandonne

    for trajet in trajet_repository.non_clos_partis_avant(limite):
        nombre += clore_trajet_abandonne(trajet.id)
    return nombre
