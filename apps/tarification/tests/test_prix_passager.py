"""Un passager qui ne fait qu'une partie du trajet paie selon sa propre distance (cahier des
charges, « Calcul des distances »). Le prix affiché avant la réservation est celui débité."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.parametres.services import modifier_param
from apps.reservations import services as reservations
from apps.tarification.calcul import part_du_trajet, prix_passager
from apps.trajets import services as trajets
from conftest import ADIDOGOME, GRAND_MARCHE

pytestmark = pytest.mark.django_db

D = Decimal
# 2e carrefour au milieu du trajet Adidogomé → Grand Marché
MILIEU = {"lat": 6.1520, "lng": 1.1955, "libelle": "Carrefour du milieu"}
ARRIVEE = {"arrivee_lat": GRAND_MARCHE["lat"] + 0.001, "arrivee_lng": GRAND_MARCHE["lng"]}


@pytest.fixture(autouse=True)
def sans_plancher_de_test():
    modifier_param("prix_minimum_place", 0)


@pytest.fixture
def trajet_deux_points(conducteur):
    return trajets.publier(
        conducteur,
        vehicule_id=conducteur.vehicules.first().id,
        depart_lat=ADIDOGOME["lat"],
        depart_lng=ADIDOGOME["lng"],
        depart_libelle="Adidogomé",
        arrivee_lat=GRAND_MARCHE["lat"],
        arrivee_lng=GRAND_MARCHE["lng"],
        arrivee_libelle="Grand Marché",
        depart_le=timezone.now() + timedelta(hours=2),
        places=3,
        points=[{"lat": 6.1750, "lng": 1.1700, "libelle": "Carrefour Adidogomé"}, MILIEU],
    )


def test_part_du_trajet_et_prix_proportionnel():
    assert part_du_trajet(5, 10) == D("0.500")
    assert part_du_trajet(12, 10) == D(1)  # jamais plus que la place
    assert part_du_trajet(3, 0) == D(1)
    assert prix_passager(275, D("0.500"), 5, 0) == 140  # 137,5 arrondi au multiple de 5 supérieur
    assert prix_passager(275, D(1), 5, 0) == 275
    assert prix_passager(275, D("0.010"), 5, 100) == 100  # minimum de la place respecté


def test_passager_au_milieu_paie_moins_et_le_meme_prix_partout(
    client_de, passager, trajet_deux_points
):
    trajet = trajet_deux_points
    milieu = trajet.points.get(ordre=2)
    debut = trajet.points.get(ordre=1)
    client = client_de(passager)

    # Recherche depuis le carrefour du milieu : point proposé = milieu, prix réduit
    recherche = client.get(
        "/api/v1/trajets/recherche/",
        {
            "depart_lat": MILIEU["lat"],
            "depart_lng": MILIEU["lng"],
            **ARRIVEE,
            "date_heure": trajet.depart_le.isoformat(),
        },
    ).json()["reponse"]
    resultat = next(r for r in recherche if r["trajet"]["id"] == str(trajet.id))
    assert resultat["point_propose"]["id"] == str(milieu.id)
    prix_affiche = resultat["prix_passager"]
    assert 0 < prix_affiche < trajet.prix_place

    # Détail du trajet pour ce point : même prix, aperçu du paiement sur ce montant
    detail = client.get(
        f"/api/v1/trajets/{trajet.id}/", {"point_id": str(milieu.id), **ARRIVEE}
    ).json()["reponse"]
    assert detail["prix_passager"] == prix_affiche
    assert detail["paiement"]["montant_total"] == prix_affiche

    # Réservation : exactement ce prix, commission et net calculés dessus
    reservation = reservations.demander_place(
        passager, trajet_id=trajet.id, point_id=milieu.id, arrivee_libelle="Grand Marché", **ARRIVEE
    )
    assert reservation.prix == prix_affiche
    assert D("0.3") < reservation.part_trajet < D("0.7")
    assert reservation.commission + reservation.net_conducteur == prix_affiche

    # Depuis le premier carrefour : quasiment tout le trajet, le prix de la place
    complet = client.get(
        f"/api/v1/trajets/{trajet.id}/", {"point_id": str(debut.id), **ARRIVEE}
    ).json()["reponse"]
    assert complet["prix_passager"] == trajet.prix_place


def test_detail_sans_point_affiche_le_prix_de_la_place(client_de, passager, trajet_deux_points):
    detail = client_de(passager).get(f"/api/v1/trajets/{trajet_deux_points.id}/").json()["reponse"]

    assert detail["prix_passager"] == trajet_deux_points.prix_place


def test_point_d_un_autre_trajet_refuse(client_de, passager, trajet_deux_points, trajet):
    autre_point = trajet.points.first()

    reponse = client_de(passager).get(
        f"/api/v1/trajets/{trajet_deux_points.id}/", {"point_id": str(autre_point.id), **ARRIVEE}
    )

    assert reponse.status_code == 404
