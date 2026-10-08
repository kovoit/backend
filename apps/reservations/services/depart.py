"""Prise en charge : saisie du code de départ, ou déclaration d'absence du passager."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import Conflit, DonneesInvalides
from apps.parametres.services import get_param
from apps.portefeuille import services as portefeuille
from apps.reservations.code_depart import code_valide
from apps.reservations.models import Reservation, StatutReservation
from apps.reservations.repository import reservation_repository
from apps.reservations.services.commun import (
    libelle_trajet,
    notifier_passager,
    transitionner,
    verrouiller_pour_conducteur,
)
from apps.trajets.repository import trajet_repository
from apps.trajets.services import marquer_en_cours


class CodeDepartInvalide(DonneesInvalides):
    code = "CODE_DEPART_INVALIDE"
    message = "Code de départ incorrect."


class CodeDepartBloque(Conflit):
    code = "CODE_DEPART_BLOQUE"
    message = "Trop d'essais : le code de départ est bloqué. Contactez le support."


def saisir_code(conducteur, reservation_id, code: str) -> Reservation:
    """Le bon code fait passer la réservation « en cours » et débite le passager."""
    with transaction.atomic():
        reservation = verrouiller_pour_conducteur(conducteur, reservation_id)
        if reservation.statut != StatutReservation.ACCEPTEE:
            raise Conflit("Cette réservation n'attend pas de code.", code="CODE_NON_ATTENDU")
        max_essais = get_param("code_depart_max_essais")
        if reservation.essais_code >= max_essais:
            raise CodeDepartBloque()
        valide = code_valide(reservation, code)
        if valide:
            transitionner(reservation, StatutReservation.EN_COURS)
            portefeuille.debiter(reservation)
            marquer_en_cours(trajet_repository.get_verrouille(reservation.trajet_id))
        else:
            essais = reservation.essais_code + 1
            reservation_repository.update(reservation, essais_code=essais)
    # Levée hors transaction pour que le compteur d'essais soit enregistré
    if not valide:
        restants = max_essais - essais
        raise CodeDepartInvalide(f"Code de départ incorrect ({restants} essai(s) restant(s)).")

    notifier_passager(
        reservation, "Bon trajet !", f"Prise en charge confirmée : {libelle_trajet(reservation)}."
    )
    return reservation_repository.get_by_id(reservation.id)


def declarer_absent(conducteur, reservation_id, lat: float, lng: float) -> Reservation:
    """Après l'heure de départ + tolérance, le passager paie et une absence est comptée."""
    from apps.confiance.services import enregistrer_incident

    with transaction.atomic():
        reservation = verrouiller_pour_conducteur(conducteur, reservation_id)
        tolerance = timedelta(minutes=get_param("tolerance_retard_min"))
        if timezone.now() < reservation.trajet.depart_le + tolerance:
            raise Conflit(
                f"Attendez {get_param('tolerance_retard_min')} min après l'heure de départ "
                "avant de déclarer une absence.",
                code="ABSENCE_PREMATUREE",
            )
        transitionner(reservation, StatutReservation.ABSENT, absence_lat=lat, absence_lng=lng)
        portefeuille.debiter(reservation)
        portefeuille.crediter_conducteur(reservation)

    notifier_passager(
        reservation,
        "Absence déclarée",
        f"Le conducteur vous a déclaré absent pour {libelle_trajet(reservation)}. "
        "Le trajet vous est facturé.",
    )
    enregistrer_incident(reservation.passager)
    return reservation_repository.get_by_id(reservation.id)
