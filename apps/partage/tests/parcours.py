"""Parcours réel d'une réservation partagée : chaque statut est atteint par ses vrais services."""

from datetime import timedelta

from freezegun import freeze_time

from apps.confiance import services as confiance
from apps.parametres.services import get_param
from apps.reservations import services as reservations
from apps.reservations.code_depart import calculer_code
from apps.reservations.models import StatutReservation as S
from apps.trajets import services as trajets

# Position transmise par l'app du conducteur (CA-032-1)
POSITION = {"lat": 6.1319, "lng": 1.2228}
POSITION_DANS_LA_PAGE = "mlat=6.13190&amp;mlon=1.22280"
TITRE_LIEN_INVALIDE = "Ce lien n'est plus valable"  # D-50 : le texte du code fait foi

STATUTS_VALIDES = [S.ACCEPTEE, S.EN_COURS]
STATUTS_INVALIDES = [S.TERMINEE, S.LITIGE, S.CLOTUREE, S.ANNULEE, S.ABSENT]


def creer_lien_par_api(client, reservation_id) -> str:
    """Le passager crée le lien ; renvoie le jeton."""
    reponse = client.post(f"/api/v1/reservations/{reservation_id}/partage/")
    assert reponse.status_code == 201, reponse.json()
    return reponse.json()["reponse"]["jeton"]


def _demarrer(conducteur, reservation):
    reservations.saisir_code(conducteur, reservation.id, calculer_code(reservation))


def terminer_trajet(conducteur, reservation):
    """Le conducteur termine le trajet : ses réservations `en_cours` passent `terminee`."""
    trajets.terminer(conducteur, reservation.trajet_id)


def _terminer(conducteur, reservation):
    _demarrer(conducteur, reservation)
    terminer_trajet(conducteur, reservation)


def _declarer_absent(conducteur, reservation):
    tolerance = timedelta(minutes=get_param("tolerance_retard_min") + 1)
    with freeze_time(reservation.trajet.depart_le + tolerance):
        reservations.declarer_absent(conducteur, reservation.id, **POSITION)


def verifier_page_lien_invalide(reponse):
    """Page 404 « lien plus valable » : jamais mise en cache, jamais indexée, jeton non transmis."""
    assert reponse.status_code == 404
    assert reponse["Content-Type"].startswith("text/html")
    assert f"<h1>{TITRE_LIEN_INVALIDE}</h1>" in reponse.content.decode()
    cache_control = {directive.strip() for directive in reponse["Cache-Control"].split(",")}
    assert {"no-cache", "no-store", "must-revalidate"} <= cache_control
    assert reponse["X-Robots-Tag"] == "noindex, nofollow"
    assert reponse["Referrer-Policy"] == "no-referrer"


def amener_au_statut(reservation, statut, passager, conducteur):
    """Fait passer une réservation `acceptee` au statut voulu par les services métier."""
    if statut == S.EN_COURS:
        _demarrer(conducteur, reservation)
    elif statut == S.TERMINEE:
        _terminer(conducteur, reservation)
    elif statut == S.LITIGE:
        _terminer(conducteur, reservation)
        confiance.signaler(passager, reservation.id, "Déposé loin de mon arrêt.")
    elif statut == S.CLOTUREE:
        _terminer(conducteur, reservation)
        reservations.confirmer_arrivee(passager, reservation.id)
    elif statut == S.ANNULEE:
        reservations.annuler(passager, reservation.id)
    elif statut == S.ABSENT:
        _declarer_absent(conducteur, reservation)
    reservation.refresh_from_db()
    assert reservation.statut == statut
    return reservation
