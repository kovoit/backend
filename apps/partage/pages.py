"""Page publique « Suivre le trajet » : ce que voit le proche qui ouvre le lien partagé.

HTML rendu par le serveur (aucun script) : lisible sur tout téléphone, rafraîchie toutes les
30 s. Mêmes données que l'API publique (TrajetPartageSerializer) : ni email ni téléphone.
"""

from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.core.exceptions import RessourceIntrouvable
from apps.partage import services
from apps.reservations.models import StatutReservation as S

ETATS = {
    S.ACCEPTEE: "Place confirmée, en attente du départ",
    S.EN_COURS: "En route",
}
RAFRAICHIR_S = 30


def _entetes(reponse):
    # Le jeton est dans l'URL : il ne doit fuiter ni par le Referer, ni dans un moteur de recherche
    reponse["Referrer-Policy"] = "no-referrer"
    reponse["X-Robots-Tag"] = "noindex, nofollow"
    return reponse


@require_GET
@never_cache
def suivre_trajet(request, jeton: str):
    try:
        lien = services.consulter(jeton)
    except RessourceIntrouvable:
        return _entetes(render(request, "partage/suivi.html", {"expire": True}, status=404))
    reservation = lien.reservation
    trajet = reservation.trajet
    en_route = reservation.statut in (S.ACCEPTEE, S.EN_COURS)
    contexte = {
        "expire": False,
        "etat": ETATS.get(reservation.statut, ""),
        "en_route": en_route,
        "rafraichir_s": RAFRAICHIR_S if en_route else None,
        "trajet": trajet,
        "vehicule": trajet.vehicule,
        "position": trajet.position_le is not None and trajet.position_lat is not None,
        "maintenant": timezone.now(),
    }
    return _entetes(render(request, "partage/suivi.html", contexte))
