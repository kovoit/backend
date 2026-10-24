"""Paramètres de la tarification des trajets (apps/tarification/calcul.py).

Valeurs de départ validées par Kovoit le 24/10/2026 : carburant 817 F/L, commission 15 %,
consommations de référence 8 L (voiture) et 3 L (moto) / 100 km, usure 15 F/km (voiture) et
5 F/km (moto), temps du conducteur 300 F/h. Le prix couvre carburant, usure et temps.
"""

from apps.parametres.types import DECIMAL, ENTIER, Defaut

PARAMETRES_TARIFICATION: dict[str, Defaut] = {
    "prix_carburant_litre": Defaut(
        817, ENTIER, "Prix du carburant (F CFA par litre).", "tarification", "F CFA/L", 1
    ),
    "consommation_voiture_l_100km": Defaut(
        8.0,
        DECIMAL,
        "Consommation de référence d'une voiture, si le véhicule n'a pas la sienne "
        "(valeur validée par Kovoit le 24/10/2026).",
        "tarification",
        "L/100 km",
        0.5,
        30,
    ),
    "consommation_moto_l_100km": Defaut(
        3.0,
        DECIMAL,
        "Consommation de référence d'une moto, si le véhicule n'a pas la sienne "
        "(valeur validée par Kovoit le 24/10/2026).",
        "tarification",
        "L/100 km",
        0.5,
        30,
    ),
    "majoration_charge_par_passager_pct": Defaut(
        0,
        DECIMAL,
        "Surconsommation due à la charge, par passager prévu (%). 0 : non appliquée.",
        "tarification",
        "%",
        0,
        10,
    ),
    "cout_horaire_conducteur": Defaut(
        300,
        ENTIER,
        "Coût du temps du conducteur (F CFA/h). 0 : non compté.",
        "tarification",
        "F CFA/h",
    ),
    "entretien_voiture_par_km": Defaut(
        15,
        DECIMAL,
        "Entretien et usure d'une voiture (F CFA/km). 0 : non compté.",
        "tarification",
        "F CFA/km",
    ),
    "entretien_moto_par_km": Defaut(
        5,
        DECIMAL,
        "Entretien et usure d'une moto (F CFA/km). 0 : non compté.",
        "tarification",
        "F CFA/km",
    ),
    "taux_commission_pct": Defaut(
        15,
        DECIMAL,
        "Commission Kovoit, prélevée sur les paiements des passagers et à la charge du "
        "conducteur (%).",
        "tarification",
        "%",
        0,
        50,
    ),
    "arrondi_prix_fcfa": Defaut(
        5,
        ENTIER,
        "Le prix d'une place est arrondi au multiple supérieur de ce montant (F CFA).",
        "tarification",
        "F CFA",
        1,
        100,
    ),
    "prix_minimum_place": Defaut(
        0, ENTIER, "Prix minimum d'une place (F CFA). 0 : aucun minimum.", "tarification", "F CFA"
    ),
    "coef_detour_estimation": Defaut(
        1.3,
        DECIMAL,
        "Itinéraire indisponible : distance estimée = vol d'oiseau × ce coefficient.",
        "tarification",
        "×",
        1,
        3,
    ),
    "vitesse_moyenne_kmh": Defaut(
        25,
        ENTIER,
        "Itinéraire indisponible : durée estimée à cette vitesse moyenne (km/h).",
        "tarification",
        "km/h",
        5,
        120,
    ),
}
