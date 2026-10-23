"""Formule de tarification (calcul pur). Valeurs attendues calculées à la main."""

from decimal import Decimal

import pytest

from apps.tarification.calcul import (
    Parametres,
    arrondi_superieur,
    calculer,
    participation_conducteur,
    repartir_paiement,
)

D = Decimal


def parametres(**changes) -> Parametres:
    valeurs = {
        "prix_carburant_litre": D(817),
        "consommation_l_100km": D("7"),
        "source_consommation": "reference_voiture",
        "majoration_charge_par_passager_pct": D(0),
        "cout_horaire_conducteur": D(0),
        "entretien_par_km": D(0),
        "taux_commission_pct": D(15),
        "arrondi_prix_fcfa": 5,
        "prix_minimum_place": 0,
    }
    return Parametres(**{**valeurs, **changes})


def devis(distance="10", duree=30, places=3, type_vehicule="voiture", **changes):
    return calculer(
        distance_km=D(distance),
        duree_min=duree,
        type_vehicule=type_vehicule,
        passagers_prevus=places,
        parametres=parametres(**changes),
    )


def test_voiture_carburant_seul_a_817_fcfa():
    d = devis()

    assert d.carburant_litres == D("0.700")
    assert d.cout_carburant == D("571.90")  # 0,7 L × 817
    assert (d.cout_temps, d.cout_entretien, d.cout_total) == (D("0.00"), D("0.00"), D("571.90"))
    assert d.part_conducteur == D("142.98")  # 571,90 / 4
    assert d.contribution_passagers == D("428.93")
    assert d.montant_brut_passagers == D("504.62")  # 428,925 / 0,85
    assert d.prix_place == 170  # 168,21 arrondi au multiple de 5 supérieur
    assert (d.commission_place, d.net_conducteur_place) == (26, 144)  # 25,5 → 26
    assert (d.total_paye_passagers, d.commission_kovoit, d.net_conducteur) == (510, 78, 432)
    assert d.formule_version == "v1"


def test_moto_un_passager():
    d = devis(distance="8", duree=20, places=1, type_vehicule="moto", consommation_l_100km=D("2.5"))

    assert d.cout_carburant == D("163.40")  # 0,2 L × 817
    assert d.part_conducteur == d.contribution_passagers == D("81.70")
    assert (d.prix_place, d.commission_place, d.net_conducteur_place) == (100, 15, 85)


def test_temps_et_entretien_sans_double_comptage():
    d = devis(
        distance="12", duree=36, places=2, cout_horaire_conducteur=D(500), entretien_par_km=D(20)
    )

    assert d.cout_carburant == D("686.28")  # 0,84 L × 817
    assert d.cout_temps == D("300.00")  # 36 min à 500 F/h
    assert d.cout_entretien == D("240.00")  # 12 km × 20 F
    assert d.cout_total == D("1226.28")  # somme exacte des trois postes
    assert d.contribution_passagers == D("817.52")  # 1226,28 × 2/3
    assert (d.prix_place, d.commission_place, d.net_conducteur_place) == (485, 73, 412)


def test_consommation_differente_change_le_prix():
    sobre, gourmande = devis(consommation_l_100km=D(5)), devis(consommation_l_100km=D(10))

    assert sobre.cout_carburant == D("408.50")
    assert gourmande.cout_carburant == D("817.00")
    assert sobre.prix_place < gourmande.prix_place


def test_majoration_de_charge_explicite():
    d = devis(majoration_charge_par_passager_pct=D(2))  # 3 passagers : +6 %

    assert d.consommation_retenue_l_100km == D("7.420")
    assert d.cout_carburant == D("606.21")  # 0,742 L × 817


@pytest.mark.parametrize("places", [1, 2, 3, 4])
def test_plus_de_passagers_prevus_moins_cher_par_place(places):
    assert devis(places=places).prix_place >= devis(places=places + 1).prix_place


def test_places_inoccupees_a_la_charge_du_conducteur():
    d = devis()  # 3 places proposées

    assert participation_conducteur(d, 3) == D("139.90")  # ≈ sa part (142,98), arrondis compris
    assert participation_conducteur(d, 1) == D("427.90")  # une seule place payée
    assert participation_conducteur(d, 0) == d.cout_total


@pytest.mark.parametrize("distance", ["0.5", "3.2", "7.85", "15", "42.7"])
@pytest.mark.parametrize("places", [1, 2, 3, 4, 6])
@pytest.mark.parametrize("taux", ["0", "10", "15", "25"])
def test_aucun_franc_perdu_ni_cree(distance, places, taux):
    d = devis(distance=distance, places=places, taux_commission_pct=D(taux))

    # Chaque paiement : payé = commission + net, au franc près
    assert d.prix_place == d.commission_place + d.net_conducteur_place
    assert d.total_paye_passagers == d.commission_kovoit + d.net_conducteur
    # Net conducteur = contribution des passagers, à l'arrondi près (jamais une 2e commission)
    ecart = D(d.net_conducteur) - d.contribution_passagers
    assert -D("0.5") * places <= ecart < D(places * 5) + 1


def test_commission_zero():
    d = devis(taux_commission_pct=D(0))

    assert d.commission_kovoit == 0
    assert d.prix_place == 145  # 428,93 / 3 = 142,98 → 145


def test_prix_minimum_par_place():
    assert devis(distance="0.5", prix_minimum_place=100).prix_place == 100


def test_arrondi_superieur():
    assert arrondi_superieur(D("168.2"), 5) == 170
    assert arrondi_superieur(D("170"), 5) == 170
    assert arrondi_superieur(D("0.01"), 25) == 25


def test_repartition_d_un_paiement():
    assert repartir_paiement(170, D(15)) == (26, 144)
    assert repartir_paiement(100, D(15)) == (15, 85)
    assert repartir_paiement(0, D(15)) == (0, 0)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"places": 0}, "passager"),
        ({"distance": "-1"}, "négative"),
        ({"taux_commission_pct": D(100)}, "commission"),
    ],
)
def test_donnees_invalides_refusees(changes, message):
    with pytest.raises(ValueError, match=message):
        devis(**changes)


def test_instantane_json_sans_flottant():
    instantane = devis().instantane()

    assert instantane["cout_total"] == "571.90"
    assert instantane["prix_place"] == 170
    assert instantane["parametres"]["prix_carburant_litre"] == "817"
    assert not any(isinstance(v, float) for v in instantane.values())
