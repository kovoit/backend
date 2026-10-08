"""Registre des paramètres métier : clé, valeur de départ, type et rôle (PRD §11).

Ces valeurs ne servent qu'à initialiser la table `parametres` (commande `seed_parametres`).
Le code lit toujours la valeur en base via `get_param()`.
"""

from dataclasses import dataclass

ENTIER = "entier"
DECIMAL = "decimal"


@dataclass(frozen=True)
class Defaut:
    valeur: int | float
    type_valeur: str
    description: str


PARAMETRES_PAR_DEFAUT: dict[str, Defaut] = {
    # Prix et portefeuille simulé
    "prix_simulation": Defaut(300, ENTIER, "Prix temporaire par passager (F CFA)."),
    "frais_service": Defaut(0, ENTIER, "Frais de service Kovoit par passager (F CFA)."),
    "recharge_min": Defaut(500, ENTIER, "Montant minimum d'une recharge simulée (F CFA)."),
    "retrait_min": Defaut(500, ENTIER, "Montant minimum d'un retrait simulé (F CFA)."),
    # Correspondance des trajets
    "rayon_depart_km": Defaut(
        1.5, DECIMAL, "Distance max départ passager / point de prise en charge (km)."
    ),
    "rayon_arrivee_km": Defaut(
        1.5, DECIMAL, "Distance max arrivée passager / arrivée conducteur (km)."
    ),
    "fenetre_horaire_min": Defaut(15, ENTIER, "Écart max heure souhaitée / heure de départ (min)."),
    # Réservation, annulation, absence, clôture
    "delai_annulation_min": Defaut(
        30, ENTIER, "En dessous : annulation tardive (min avant départ)."
    ),
    "tolerance_retard_min": Defaut(
        10, ENTIER, "Délai avant de pouvoir déclarer une absence (min)."
    ),
    "delai_confirmation_auto_h": Defaut(
        3, ENTIER, "Clôture automatique après la fin du trajet (h)."
    ),
    "code_depart_max_essais": Defaut(5, ENTIER, "Essais max de saisie du code de départ."),
    # Fiabilité et suspension
    "seuil_incidents": Defaut(
        3, ENTIER, "Incidents (annulations tardives + absences) avant suspension."
    ),
    "periode_incidents_j": Defaut(
        30, ENTIER, "Période de calcul de la fiabilité et des incidents (jours)."
    ),
    "duree_suspension_j": Defaut(7, ENTIER, "Durée d'une suspension automatique (jours)."),
    # OTP email
    "otp_validite_min": Defaut(10, ENTIER, "Durée de validité d'un code OTP (min)."),
    "otp_max_essais": Defaut(5, ENTIER, "Essais max de saisie d'un code OTP."),
    "otp_delai_renvoi_s": Defaut(60, ENTIER, "Délai minimum entre deux envois d'OTP (s)."),
    "otp_max_par_heure": Defaut(5, ENTIER, "Nombre max d'OTP envoyés par heure et par email."),
}
