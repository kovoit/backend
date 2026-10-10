"""Activité fictive : trajets du matin, réservations et leur cycle de vie complet.

Chaque étape passe par les services métier ; l'horloge (freezegun) avance comme dans la réalité.
"""

import random
from datetime import date, datetime, time, timedelta

from django.utils import timezone

from apps.confiance import services as confiance
from apps.core.demo.lieux import itineraire
from apps.parametres.services import get_param
from apps.reservations import services as reservations
from apps.reservations.code_depart import calculer_code
from apps.trajets import services as trajets

MOTIFS_LITIGE = [
    "Le conducteur m'a déposé loin de mon arrêt.",
    "Le trajet n'a pas eu lieu comme prévu, je conteste le paiement.",
    "Le passager prétend ne pas être monté alors qu'il a voyagé.",
]
COMMENTAIRES = ["Très ponctuel, merci !", "Conduite prudente.", "", "Un peu en retard.", ""]


def a_heure(jour: date, heure: int, minute: int = 0) -> datetime:
    return timezone.make_aware(datetime.combine(jour, time(heure, minute)))


def publier(conducteur, numero: int, depart_le: datetime, places: int = 3):
    route = itineraire(numero)
    return trajets.publier(
        conducteur,
        vehicule_id=conducteur.vehicules.first().id,
        depart_lat=route["depart"]["lat"],
        depart_lng=route["depart"]["lng"],
        depart_libelle=route["depart"]["libelle"],
        arrivee_lat=route["arrivee"]["lat"],
        arrivee_lng=route["arrivee"]["lng"],
        arrivee_libelle=route["arrivee"]["libelle"],
        depart_le=depart_le,
        places=places,
        points=route["points"],
    )


def demander(passager, trajet, rng: random.Random):
    return reservations.demander_place(
        passager,
        trajet_id=trajet.id,
        point_id=rng.choice(list(trajet.points.all())).id,
        arrivee_lat=trajet.arrivee_lat,
        arrivee_lng=trajet.arrivee_lng,
        arrivee_libelle=trajet.arrivee_libelle,
    )


def _decisions(conducteur, trajet, passagers, rng):
    """Demandes à 06:00 : la plupart acceptées, quelques refus et annulations."""
    acceptees = []
    for passager in rng.sample(passagers, k=rng.randint(1, trajet.places_total)):
        reservation = demander(passager, trajet, rng)
        tirage = rng.random()
        if tirage < 0.1:
            reservations.refuser(conducteur, reservation.id)
        elif tirage < 0.18:
            reservations.annuler(passager, reservation.id)
        else:
            acceptees.append(reservations.accepter(conducteur, reservation.id))
    return acceptees


def _apres_arrivee(reservation, rng, recent: bool, compteur: dict):
    """Clôture par le passager, litige occasionnel, ou confirmation encore attendue."""
    passager, conducteur = reservation.passager, reservation.trajet.conducteur
    tirage = rng.random()
    if tirage < 0.05:
        confiance.signaler(passager, reservation.id, rng.choice(MOTIFS_LITIGE))
        compteur["litiges"] += 1
    elif recent and tirage < 0.5:
        compteur["en_attente_confirmation"] += 1
    else:
        reservations.confirmer_arrivee(passager, reservation.id)
        note = rng.choice([5, 5, 4, 4, 3])
        confiance.noter(passager, reservation.id, note, rng.choice(COMMENTAIRES))
        if rng.random() < 0.6:
            confiance.noter(conducteur, reservation.id, rng.choice([5, 4]))


def journee(jour: date, horloge, conducteurs, passagers, rng, compteur: dict, recent: bool):
    """2 à 4 trajets : publication 06:00, départ 07:30, arrivée 08:15."""
    tolerance = timedelta(minutes=get_param("tolerance_retard_min") + 1)
    for numero in range(rng.randint(2, 4)):
        conducteur = conducteurs[(jour.toordinal() + numero) % len(conducteurs)]
        horloge.move_to(a_heure(jour, 6, numero * 5))
        depart = a_heure(jour, 7, 30 + numero * 5)
        trajet = publier(conducteur, jour.toordinal() + numero, depart)
        autres = [p for p in passagers if p.id != conducteur.id]
        acceptees = _decisions(conducteur, trajet, autres, rng)
        compteur["trajets"] += 1
        if not acceptees:
            trajets.annuler(conducteur, trajet.id)
            continue

        horloge.move_to(depart + tolerance)
        montes = []
        for reservation in acceptees:
            if rng.random() < 0.06:
                reservations.declarer_absent(
                    conducteur, reservation.id, trajet.depart_lat, trajet.depart_lng
                )
            else:
                reservations.saisir_code(conducteur, reservation.id, calculer_code(reservation))
                montes.append(reservation)

        horloge.move_to(depart + timedelta(minutes=45))
        trajets.terminer(conducteur, trajet.id)
        for reservation in montes:
            _apres_arrivee(reservation, rng, recent, compteur)
