"""F-055 (contrat C2) : filtre de recherche `type_vehicule` (absent ou vide : tous les types)."""

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.kyc.tests.factories import verifier_kyc
from apps.vehicules.tests.factories import VehiculeFactory
from conftest import GRAND_MARCHE, publier_trajet

pytestmark = pytest.mark.django_db

RECHERCHE = "/api/v1/trajets/recherche/"


@pytest.fixture
def trajets_moto_et_voiture(conducteur):
    """Deux trajets compatibles avec la même recherche : une voiture et une moto."""
    motard = UserFactory(prenom="Yao")
    verifier_kyc(motard, "conducteur")
    VehiculeFactory(proprietaire=motard, type_vehicule="moto", nb_places=2)
    voiture = publier_trajet(conducteur)
    moto = publier_trajet(motard, places=1)
    return moto, voiture


def chercher(client, trajet, **filtre):
    criteres = {
        "depart_lat": 6.1748,
        "depart_lng": 1.1695,
        "arrivee_lat": GRAND_MARCHE["lat"],
        "arrivee_lng": GRAND_MARCHE["lng"],
        "date_heure": trajet.depart_le.isoformat(),
        **filtre,
    }
    return client.get(RECHERCHE, criteres)


def ids(reponse) -> set[str]:
    assert reponse.status_code == 200
    return {r["trajet"]["id"] for r in reponse.json()["reponse"]}


@pytest.mark.parametrize(
    ("filtre", "attendus"),
    [
        ({"type_vehicule": "moto"}, {"moto"}),
        ({"type_vehicule": "voiture"}, {"voiture"}),
        ({}, {"moto", "voiture"}),
        ({"type_vehicule": ""}, {"moto", "voiture"}),
    ],
)
def test_filtre_type_vehicule(client_de, passager, trajets_moto_et_voiture, filtre, attendus):
    moto, voiture = trajets_moto_et_voiture
    par_nom = {"moto": str(moto.id), "voiture": str(voiture.id)}

    reponse = chercher(client_de(passager), voiture, **filtre)

    assert ids(reponse) == {par_nom[nom] for nom in attendus}
    resultat = reponse.json()["reponse"][0]
    assert {"trajet", "point_propose", "distance_marche_km", "ecart_minutes", "prix_passager"} == (
        resultat.keys()
    )


@pytest.mark.parametrize("valeur", ["camion", "MOTO"])
def test_type_vehicule_inconnu_refuse(client_de, passager, trajets_moto_et_voiture, valeur):
    _, voiture = trajets_moto_et_voiture

    reponse = chercher(client_de(passager), voiture, type_vehicule=valeur)

    assert reponse.status_code == 400
    corps = reponse.json()
    assert corps["statut"] == "failed" and corps["message"]
    assert corps["reponse"]["code"] == "DONNEES_INVALIDES"
    assert corps["reponse"]["erreurs"]["type_vehicule"]
