"""Exporte les réponses réelles de l'API utilisées par l'app mobile (son test de contrat).

Hors de la suite normale (le nom ne commence pas par test_). À lancer après un changement d'API :

    KOVOIT_CONTRAT=../mobile/test/fixtures/backend pytest apps/core/tests/contrat_mobile.py

puis, dans mobile/ : flutter test test/core/network/api_contract_test.dart
"""

import json
import os
from pathlib import Path

import pytest
from django.utils import timezone

from apps.reservations import services as reservations
from conftest import CARREFOUR_ADIDOGOME, GRAND_MARCHE, publier_trajet

pytestmark = pytest.mark.django_db
SORTIE = Path(os.environ.get("KOVOIT_CONTRAT", "contrat_mobile"))


def _ecrire(nom, reponse):
    SORTIE.mkdir(parents=True, exist_ok=True)
    corps = reponse.json()
    (SORTIE / f"{nom}.json").write_text(json.dumps(corps, ensure_ascii=False, indent=2), "utf-8")
    return corps["reponse"]


def test_export(client_de, passager, conducteur):
    p, c = client_de(passager), client_de(conducteur)
    trajet = publier_trajet(conducteur)

    _ecrire("lieux", p.get("/api/v1/lieux/", {"q": "univ"}))
    recherche = {
        "depart_lat": CARREFOUR_ADIDOGOME["lat"],
        "depart_lng": CARREFOUR_ADIDOGOME["lng"],
        "arrivee_lat": GRAND_MARCHE["lat"],
        "arrivee_lng": GRAND_MARCHE["lng"],
        "date_heure": timezone.localtime(trajet.depart_le).isoformat(),
    }
    _ecrire("recherche", p.get("/api/v1/trajets/recherche/", recherche))
    _ecrire("trajet_detail", p.get(f"/api/v1/trajets/{trajet.id}/"))
    demande = {
        "trajet_id": str(trajet.id),
        "point_id": str(trajet.points.first().id),
        "arrivee_lat": GRAND_MARCHE["lat"],
        "arrivee_lng": GRAND_MARCHE["lng"],
        "arrivee_libelle": "Grand Marché",
    }
    resa = _ecrire("reservation_creee", p.post("/api/v1/reservations/", demande, format="json"))
    _ecrire("reservations_passager", p.get("/api/v1/reservations/"))
    reservations.accepter(conducteur, resa["id"])
    _ecrire("reservation_acceptee", p.get(f"/api/v1/reservations/{resa['id']}/"))
    _ecrire("trajet_reservations", c.get(f"/api/v1/trajets/{trajet.id}/reservations/"))
    _ecrire("mes_trajets", c.get("/api/v1/trajets/mes-trajets/"))
    _ecrire("partage", p.post(f"/api/v1/reservations/{resa['id']}/partage/"))
    # La réservation a été acceptée : le passager a reçu une notification
    _ecrire("notifications", p.get("/api/v1/notifications/"))
    _ecrire("economies", c.get("/api/v1/moi/economies/"))
    _ecrire("vehicules", c.get("/api/v1/vehicules/"))
    _ecrire("portefeuille", p.get("/api/v1/portefeuille/"))
    operation = {"montant": 1000, "moyen": "mixx"}
    recharge = _ecrire(
        "recharge", p.post("/api/v1/portefeuille/recharger/", operation, format="json")
    )
    transaction = recharge["transaction"]["id"]
    _ecrire("transaction", p.get(f"/api/v1/portefeuille/transactions/{transaction}/"))
    _ecrire("transactions", p.get("/api/v1/portefeuille/transactions/"))
    publication = {
        "vehicule_id": str(conducteur.vehicules.first().id),
        "depart_lat": 6.1745,
        "depart_lng": 1.169,
        "depart_libelle": "Adidogomé",
        "arrivee_lat": 6.13,
        "arrivee_lng": 1.222,
        "arrivee_libelle": "Grand Marché",
        "depart_le": "2099-01-01T07:30:00Z",
        "places": 2,
        "points": [CARREFOUR_ADIDOGOME],
    }
    estimation = {k: publication[k] for k in ("vehicule_id", "depart_lat", "depart_lng")}
    estimation |= {k: publication[k] for k in ("arrivee_lat", "arrivee_lng", "places")}
    _ecrire("estimation", c.post("/api/v1/trajets/estimation/", estimation, format="json"))
    _ecrire("trajet_publie", c.post("/api/v1/trajets/", publication, format="json"))
    _ecrire("erreur_solde", p.post("/api/v1/reservations/", demande, format="json"))
