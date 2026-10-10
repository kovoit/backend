"""Registre des paramètres métier : clé, valeur de départ, type, unité, minimum (PRD §11).

Ces valeurs ne servent qu'à initialiser la table `parametres` (commande `seed_parametres`).
Le code lit toujours la valeur en base via `get_param()`. L'ordre du registre est celui de
l'écran Paramètres du back-office.
"""

from dataclasses import dataclass

ENTIER = "entier"
DECIMAL = "decimal"

GROUPES = {
    "prix": "Prix et portefeuille",
    "correspondance": "Correspondance des trajets",
    "reservation": "Réservation, annulation et clôture",
    "fiabilite": "Fiabilité et suspension",
    "otp": "Connexion par code (OTP)",
}


@dataclass(frozen=True)
class Defaut:
    valeur: int | float
    type_valeur: str
    description: str
    groupe: str
    unite: str = ""
    # Plus petite valeur acceptée : 0 casserait certaines règles (ex. suspension sans fin)
    minimum: int | float = 0


PARAMETRES_PAR_DEFAUT: dict[str, Defaut] = {
    "prix_simulation": Defaut(
        300, ENTIER, "Prix temporaire par passager (F CFA).", "prix", "F CFA"
    ),
    "frais_service": Defaut(
        0, ENTIER, "Frais de service Kovoit par passager (F CFA).", "prix", "F CFA"
    ),
    "recharge_min": Defaut(
        500, ENTIER, "Montant minimum d'une recharge simulée (F CFA).", "prix", "F CFA"
    ),
    "retrait_min": Defaut(
        500, ENTIER, "Montant minimum d'un retrait simulé (F CFA).", "prix", "F CFA"
    ),
    "rayon_depart_km": Defaut(
        1.5,
        DECIMAL,
        "Distance max départ passager / point de prise en charge (km).",
        "correspondance",
        "km",
        0.1,
    ),
    "rayon_arrivee_km": Defaut(
        1.5,
        DECIMAL,
        "Distance max arrivée passager / arrivée conducteur (km).",
        "correspondance",
        "km",
        0.1,
    ),
    "fenetre_horaire_min": Defaut(
        15,
        ENTIER,
        "Écart max heure souhaitée / heure de départ (min).",
        "correspondance",
        "min",
        1,
    ),
    "delai_annulation_min": Defaut(
        30, ENTIER, "En dessous : annulation tardive (min avant départ).", "reservation", "min"
    ),
    "tolerance_retard_min": Defaut(
        10, ENTIER, "Délai avant de pouvoir déclarer une absence (min).", "reservation", "min"
    ),
    "delai_confirmation_auto_h": Defaut(
        3, ENTIER, "Clôture automatique après la fin du trajet (h).", "reservation", "h", 1
    ),
    "code_depart_max_essais": Defaut(
        5, ENTIER, "Essais max de saisie du code de départ.", "reservation", "essais", 1
    ),
    "seuil_incidents": Defaut(
        3,
        ENTIER,
        "Incidents (annulations tardives + absences) avant suspension.",
        "fiabilite",
        "incidents",
        1,
    ),
    "periode_incidents_j": Defaut(
        30,
        ENTIER,
        "Période de calcul de la fiabilité et des incidents (jours).",
        "fiabilite",
        "jours",
        1,
    ),
    "duree_suspension_j": Defaut(
        7, ENTIER, "Durée d'une suspension automatique (jours).", "fiabilite", "jours", 1
    ),
    "otp_validite_min": Defaut(
        10, ENTIER, "Durée de validité d'un code OTP (min).", "otp", "min", 1
    ),
    "otp_max_essais": Defaut(5, ENTIER, "Essais max de saisie d'un code OTP.", "otp", "essais", 1),
    "otp_delai_renvoi_s": Defaut(
        60, ENTIER, "Délai minimum entre deux envois d'OTP (s).", "otp", "s"
    ),
    "otp_max_par_heure": Defaut(
        5, ENTIER, "Nombre max d'OTP envoyés par heure et par email.", "otp", "codes", 1
    ),
}
