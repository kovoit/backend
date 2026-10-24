"""Registre des paramètres métier : clé, valeur de départ, type, unité, minimum (PRD §11).

Ces valeurs ne servent qu'à initialiser la table `parametres` (commande `seed_parametres`).
Le code lit toujours la valeur en base via `get_param()`. L'ordre du registre est celui de
l'écran Paramètres du back-office.
"""

from apps.parametres.defauts_tarification import PARAMETRES_TARIFICATION
from apps.parametres.types import DECIMAL, ENTIER, Defaut

__all__ = ["DECIMAL", "ENTIER", "GROUPES", "PARAMETRES_PAR_DEFAUT", "Defaut"]


GROUPES = {
    "tarification": "Tarification des trajets",
    "prix": "Portefeuille et paiements",
    "correspondance": "Correspondance des trajets",
    "reservation": "Réservation, annulation et clôture",
    "fiabilite": "Fiabilité et suspension",
    "otp": "Connexion par code (OTP)",
    "audit": "Journal d'audit",
}


PARAMETRES_PAR_DEFAUT: dict[str, Defaut] = {
    **PARAMETRES_TARIFICATION,
    "recharge_min": Defaut(
        500, ENTIER, "Montant minimum d'une recharge simulée (F CFA).", "prix", "F CFA"
    ),
    "recharge_max": Defaut(
        100_000,
        ENTIER,
        "Montant maximum d'une recharge (F CFA) : limite la fraude et les erreurs de saisie.",
        "prix",
        "F CFA",
        500,
    ),
    "retrait_min": Defaut(
        500, ENTIER, "Montant minimum d'un retrait simulé (F CFA).", "prix", "F CFA"
    ),
    "paiement_attente_max_min": Defaut(
        60,
        ENTIER,
        "Délai maximal de confirmation d'un paiement Mobile Money (min).",
        "prix",
        "min",
        5,
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
    "delai_resolution_h": Defaut(
        6,
        ENTIER,
        "Réservation acceptée sans prise en charge ni absence : annulée et argent débloqué "
        "ce délai après le départ (h).",
        "reservation",
        "h",
        1,
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
    "audit_retention_jours": Defaut(
        365,
        ENTIER,
        "Durée de conservation des événements du journal d'audit (jours).",
        "audit",
        "jours",
        30,
    ),
}
