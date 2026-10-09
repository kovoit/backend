"""Cycle de vie d'un trajet côté conducteur, et gestion des places."""

from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import Conflit, RessourceIntrouvable
from apps.trajets.models import StatutTrajet, Trajet
from apps.trajets.repository import trajet_repository

STATUTS_OUVERTS = {StatutTrajet.PUBLIE, StatutTrajet.COMPLET}


def get_trajet(trajet_id) -> Trajet:
    return trajet_repository.get_by_id(trajet_id)


def get_trajet_du_conducteur(conducteur, trajet_id) -> Trajet:
    trajet = trajet_repository.get_by_id(trajet_id)
    if trajet.conducteur_id != conducteur.id:
        raise RessourceIntrouvable("Trajet introuvable.")
    return trajet


def mes_trajets(conducteur):
    return trajet_repository.de_conducteur(conducteur)


def lister_trajets(statut: str | None = None, recherche: str | None = None, jour=None):
    return trajet_repository.lister(statut, recherche, jour)


def retirer_place(trajet: Trajet) -> None:
    """Trajet verrouillé. Passe à « complet » quand il n'y a plus de place."""
    if trajet.places_restantes < 1:
        raise Conflit("Plus aucune place disponible sur ce trajet.", code="PLUS_DE_PLACE")
    restantes = trajet.places_restantes - 1
    statut = StatutTrajet.COMPLET if restantes == 0 else trajet.statut
    trajet_repository.update(trajet, places_restantes=restantes, statut=statut)


def rendre_place(trajet: Trajet) -> None:
    """Trajet verrouillé. Un trajet complet redevient « publié »."""
    statut = StatutTrajet.PUBLIE if trajet.statut == StatutTrajet.COMPLET else trajet.statut
    trajet_repository.update(
        trajet,
        places_restantes=min(trajet.places_restantes + 1, trajet.places_total),
        statut=statut,
    )


def marquer_en_cours(trajet: Trajet) -> None:
    if trajet.statut in STATUTS_OUVERTS:
        trajet_repository.update(trajet, statut=StatutTrajet.EN_COURS)


def annuler(conducteur, trajet_id) -> Trajet:
    from apps.reservations.services import annuler_reservations_du_trajet

    trajet = get_trajet_du_conducteur(conducteur, trajet_id)
    with transaction.atomic():
        trajet = trajet_repository.get_verrouille(trajet.id)
        if trajet.statut not in STATUTS_OUVERTS or trajet.depart_le <= timezone.now():
            raise Conflit("Ce trajet ne peut plus être annulé.", code="TRAJET_NON_ANNULABLE")
        trajet_repository.update(trajet, statut=StatutTrajet.ANNULE)
        annuler_reservations_du_trajet(trajet, conducteur)
    return trajet_repository.get_by_id(trajet.id)


def terminer(conducteur, trajet_id) -> Trajet:
    from apps.reservations.services import terminer_reservations_du_trajet

    trajet = get_trajet_du_conducteur(conducteur, trajet_id)
    with transaction.atomic():
        trajet = trajet_repository.get_verrouille(trajet.id)
        if trajet.statut not in STATUTS_OUVERTS | {StatutTrajet.EN_COURS}:
            raise Conflit("Ce trajet est déjà terminé ou annulé.", code="TRAJET_CLOS")
        terminer_reservations_du_trajet(trajet)
        trajet_repository.update(trajet, statut=StatutTrajet.TERMINE)
    return trajet_repository.get_by_id(trajet.id)


def mettre_a_jour_position(conducteur, trajet_id, lat: float, lng: float) -> Trajet:
    trajet = get_trajet_du_conducteur(conducteur, trajet_id)
    if trajet.statut in {StatutTrajet.TERMINE, StatutTrajet.ANNULE}:
        raise Conflit("Le trajet est terminé.", code="TRAJET_CLOS")
    return trajet_repository.update(
        trajet, position_lat=lat, position_lng=lng, position_le=timezone.now()
    )


def annuler_trajets_a_venir(conducteur) -> None:
    """Compte suspendu : annule ses trajets à venir (et les réservations associées)."""
    for trajet in trajet_repository.a_venir_de_conducteur(conducteur, timezone.now()):
        annuler(conducteur, trajet.id)
