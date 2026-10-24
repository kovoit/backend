"""Tarification branchée sur la publication, la réservation et le portefeuille."""

from decimal import Decimal
from unittest import mock

import pytest

from apps.audit.models import EvenementAudit
from apps.parametres.services import modifier_param
from apps.portefeuille import services as portefeuille
from apps.portefeuille.models import Transaction, TypeTransaction
from apps.reservations import services as reservations
from apps.reservations.code_depart import calculer_code
from apps.vehicules.tests.factories import VehiculeFactory
from conftest import ADIDOGOME, GRAND_MARCHE, demander, publier_trajet

pytestmark = pytest.mark.django_db

ESTIMATION = "/api/v1/trajets/estimation/"


@pytest.fixture(autouse=True)
def prix_calcule(parametres_initialises_tarif):
    """Ici, pas de plancher de test : le prix est celui de la formule (275 F pour le trajet de
    test : ~10 km et 24 min en voiture à 8 L/100 km, 3 places, carburant à 817 F/L, usure 15 F/km,
    temps 300 F/h, commission 15 %)."""


@pytest.fixture
def parametres_initialises_tarif():
    modifier_param("prix_minimum_place", 0)


def corps_estimation(conducteur, places=3):
    return {
        "vehicule_id": str(conducteur.vehicules.first().id),
        "depart_lat": ADIDOGOME["lat"],
        "depart_lng": ADIDOGOME["lng"],
        "arrivee_lat": GRAND_MARCHE["lat"],
        "arrivee_lng": GRAND_MARCHE["lng"],
        "places": places,
    }


def test_publication_fige_le_prix_calcule_et_son_instantane(conducteur):
    trajet = publier_trajet(conducteur)

    t = trajet.tarification
    assert trajet.prix_place == t["prix_place"] == 275
    assert trajet.duree_min == t["duree_min"] > 0
    assert Decimal(t["distance_km"]) == trajet.distance_km
    assert t["passagers_prevus"] == 3 and t["formule_version"] == "v1"
    assert t["parametres"]["prix_carburant_litre"] == "817"
    assert t["parametres"]["taux_commission_pct"] == "15"
    assert (t["commission_place"], t["net_conducteur_place"]) == (41, 234)
    evenement = EvenementAudit.objects.get(action="trajet.publier")
    assert evenement.details["cout_total"] == t["cout_total"]


def test_un_parametre_modifie_ne_change_pas_un_prix_confirme(conducteur, passager):
    trajet = publier_trajet(conducteur)
    modifier_param("prix_carburant_litre", 1000)
    modifier_param("taux_commission_pct", 20)

    reservation = demander(passager, trajet)

    assert reservation.prix == 275
    assert reservation.taux_commission_pct == Decimal(15)  # taux de la publication
    assert (reservation.commission, reservation.net_conducteur) == (41, 234)
    assert publier_trajet(conducteur).prix_place > 275  # seuls les nouveaux trajets changent


def test_consommation_propre_au_vehicule(conducteur):
    conducteur.vehicules.update(consommation_l_100km=Decimal("16.0"))  # double de la référence

    trajet = publier_trajet(conducteur)

    assert trajet.tarification["parametres"]["source_consommation"] == "vehicule"
    assert trajet.prix_place > 275


def test_moto_une_place(conducteur):
    conducteur.vehicules.all().delete()
    VehiculeFactory(proprietaire=conducteur, type_vehicule="moto", nb_places=2)

    trajet = publier_trajet(conducteur, places=1)

    t = trajet.tarification
    assert t["type_vehicule"] == "moto"
    assert t["parametres"]["source_consommation"] == "reference_moto"
    assert t["parametres"]["consommation_l_100km"] == "3.0"
    assert trajet.prix_place == t["prix_place"] > 0


def test_capacite_depassee_refusee(client_de, conducteur):
    reponse = client_de(conducteur).post(
        ESTIMATION, corps_estimation(conducteur, places=5), format="json"
    )

    assert reponse.status_code == 400
    assert reponse.json()["reponse"]["code"] == "PLACES_INVALIDES"


def test_estimation_avant_publication_sans_rien_enregistrer(client_de, conducteur):
    reponse = client_de(conducteur).post(ESTIMATION, corps_estimation(conducteur), format="json")

    assert reponse.status_code == 200
    devis = reponse.json()["reponse"]
    assert devis["prix_place"] == 275
    assert devis["commission_kovoit"] + devis["net_conducteur"] == devis["total_paye_passagers"]
    assert devis["cout_carburant"] and devis["part_conducteur"]
    assert not conducteur.trajets_conduits.exists()


def test_estimation_reservee_aux_conducteurs_habilites(client_de, passager):
    reponse = client_de(passager).post(ESTIMATION, {}, format="json")

    assert reponse.status_code == 403


def test_prix_envoye_par_l_application_ignore(client_de, conducteur, passager):
    """Le prix, la commission et le net ne sont jamais acceptés du client."""
    trajet = publier_trajet(conducteur)
    reponse = client_de(passager).post(
        "/api/v1/reservations/",
        {
            "trajet_id": str(trajet.id),
            "point_id": str(trajet.points.first().id),
            "arrivee_lat": GRAND_MARCHE["lat"],
            "arrivee_lng": GRAND_MARCHE["lng"],
            "prix": 1,
            "commission": 0,
            "net_conducteur": 1,
        },
        format="json",
    )

    assert reponse.status_code == 201
    assert reponse.json()["reponse"]["prix"] == 275


def test_itineraire_indisponible_estimation_signalee(settings, conducteur):
    settings.ROUTAGE_PROVIDER = "apps.routage.providers.OsrmProvider"
    with mock.patch("urllib.request.urlopen", side_effect=OSError("hors ligne")):
        trajet = publier_trajet(conducteur)

    assert trajet.tarification["source_itineraire"] == "estimation"
    assert trajet.distance_km > 0 and trajet.duree_min > 0
    assert trajet.prix_place > 0


def test_commission_encaissee_au_versement_seulement(conducteur, passager):
    trajet = publier_trajet(conducteur)
    reservation = reservations.accepter(conducteur, demander(passager, trajet).id)
    commissions = Transaction.objects.filter(type=TypeTransaction.COMMISSION)
    assert not commissions.exists()  # calculée, pas encore encaissée

    reservations.saisir_code(conducteur, reservation.id, calculer_code(reservation))
    reservations.terminer_reservations_du_trajet(trajet)
    reservations.confirmer_arrivee(passager, reservation.id)

    assert portefeuille.solde(passager).total == 5000 - 275
    assert portefeuille.solde(conducteur).total == 234  # 275 − 41
    assert list(commissions.values_list("montant", flat=True)) == [41]
    evenement = EvenementAudit.objects.get(action="portefeuille.reverser")
    assert evenement.details["commission"] + evenement.details["net_conducteur"] == 275


def test_annulation_rembourse_sans_commission(conducteur, passager):
    trajet = publier_trajet(conducteur)
    reservation = reservations.accepter(conducteur, demander(passager, trajet).id)

    reservations.annuler(passager, reservation.id)

    assert portefeuille.solde(passager).disponible == 5000
    assert not Transaction.objects.filter(type=TypeTransaction.COMMISSION).exists()


def test_le_conducteur_declare_la_consommation_de_son_vehicule(client_de, conducteur):
    vehicule = conducteur.vehicules.first()
    url = f"/api/v1/vehicules/{vehicule.id}/"

    reponse = client_de(conducteur).patch(url, {"consommation_l_100km": "6.5"}, format="json")
    assert reponse.status_code == 200
    assert reponse.json()["reponse"]["consommation_l_100km"] == "6.5"
    trop = client_de(conducteur).patch(url, {"consommation_l_100km": "45"}, format="json")
    assert trop.status_code == 400
