"""Formule de tarification Kovoit (version FORMULE_VERSION) : calcul pur, sans base de données.

Postes du coût du trajet (aucun n'en recouvre un autre) :
- carburant = distance × consommation retenue / 100 × prix du litre ;
  consommation retenue = consommation du véhicule (ou référence du type)
  × (1 + majoration de charge × passagers prévus) ;
- temps     = durée (h) × coût horaire du conducteur (0 = non compté) ;
- entretien = distance × coût d'entretien et d'usure par km (0 = non compté).

Partage : le conducteur paie sa part comme un passager, C / (N + 1). Les N passagers prévus
(N = places proposées) couvrent le reste. La commission Kovoit est à la charge du conducteur :
le montant brut payé par les passagers est majoré pour que, une fois la commission prélevée,
le conducteur touche la contribution prévue des passagers.

Arrondis (F CFA entiers, jamais de nombre flottant) :
- prix d'une place = brut / N arrondi au multiple SUPÉRIEUR de `arrondi` (au moins le minimum) ;
- commission d'une place = prix × taux, arrondie au franc le plus proche (demi vers le haut) ;
- net conducteur d'une place = prix − commission.
Donc pour chaque paiement : payé = commission + net, au franc près (rien n'est perdu ni créé).
"""

from dataclasses import asdict, dataclass
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

FORMULE_VERSION = "v1"
CENT = Decimal(100)
SOIXANTE = Decimal(60)


@dataclass(frozen=True)
class Parametres:
    """Paramètres retenus pour un calcul : conservés tels quels dans l'instantané du prix."""

    prix_carburant_litre: Decimal
    consommation_l_100km: Decimal
    source_consommation: str  # « vehicule » ou « reference_<type> »
    majoration_charge_par_passager_pct: Decimal
    cout_horaire_conducteur: Decimal
    entretien_par_km: Decimal
    taux_commission_pct: Decimal
    arrondi_prix_fcfa: int
    prix_minimum_place: int


@dataclass(frozen=True)
class Devis:
    formule_version: str
    type_vehicule: str
    distance_km: Decimal
    duree_min: int
    source_itineraire: str  # « routage » ou « estimation »
    passagers_prevus: int
    consommation_retenue_l_100km: Decimal
    carburant_litres: Decimal
    cout_carburant: Decimal
    cout_temps: Decimal
    cout_entretien: Decimal
    cout_total: Decimal
    part_conducteur: Decimal
    contribution_passagers: Decimal
    montant_brut_passagers: Decimal
    prix_place: int
    commission_place: int
    net_conducteur_place: int
    total_paye_passagers: int  # prix_place × passagers prévus (arrondis compris)
    commission_kovoit: int
    net_conducteur: int
    parametres: Parametres

    def instantane(self) -> dict:
        """Forme JSON (chaînes pour les décimaux) enregistrée avec le trajet."""

        def serialiser(valeur):
            if isinstance(valeur, Decimal):
                return str(valeur)
            if isinstance(valeur, dict):
                return {cle: serialiser(v) for cle, v in valeur.items()}
            return valeur

        return serialiser(asdict(self))


def _sous(montant: Decimal) -> Decimal:
    """Affichage des postes de coût : 2 décimales (le prix final est un entier)."""
    return montant.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def arrondi_superieur(montant: Decimal, pas: int) -> int:
    pas_decimal = Decimal(pas)
    return int((montant / pas_decimal).to_integral_value(rounding=ROUND_CEILING) * pas_decimal)


def repartir_paiement(prix: int, taux_commission_pct: Decimal) -> tuple[int, int]:
    """(commission, net conducteur) d'un paiement : commission + net == prix, toujours."""
    commission = int(
        (Decimal(prix) * taux_commission_pct / CENT).to_integral_value(rounding=ROUND_HALF_UP)
    )
    return commission, prix - commission


def calculer(
    *,
    distance_km: Decimal,
    duree_min: int,
    type_vehicule: str,
    passagers_prevus: int,
    parametres: Parametres,
    source_itineraire: str = "routage",
) -> Devis:
    if passagers_prevus < 1:
        raise ValueError("Au moins un passager prévu est nécessaire au partage des frais.")
    if distance_km < 0 or duree_min < 0:
        raise ValueError("Distance et durée ne peuvent pas être négatives.")
    if not Decimal(0) <= parametres.taux_commission_pct < CENT:
        raise ValueError("Le taux de commission doit être compris entre 0 et 100 % exclus.")
    p = parametres
    n = Decimal(passagers_prevus)

    majoration = 1 + p.majoration_charge_par_passager_pct / CENT * n
    consommation = p.consommation_l_100km * majoration
    litres = distance_km * consommation / CENT
    cout_carburant = litres * p.prix_carburant_litre
    cout_temps = Decimal(duree_min) / SOIXANTE * p.cout_horaire_conducteur
    cout_entretien = distance_km * p.entretien_par_km
    cout_total = cout_carburant + cout_temps + cout_entretien

    part_conducteur = cout_total / (n + 1)
    contribution = cout_total - part_conducteur
    brut = contribution / (1 - p.taux_commission_pct / CENT)

    prix_place = max(arrondi_superieur(brut / n, p.arrondi_prix_fcfa), p.prix_minimum_place)
    commission_place, net_place = repartir_paiement(prix_place, p.taux_commission_pct)

    return Devis(
        formule_version=FORMULE_VERSION,
        type_vehicule=type_vehicule,
        distance_km=distance_km,
        duree_min=duree_min,
        source_itineraire=source_itineraire,
        passagers_prevus=passagers_prevus,
        consommation_retenue_l_100km=consommation.quantize(Decimal("0.001")),
        carburant_litres=litres.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP),
        cout_carburant=_sous(cout_carburant),
        cout_temps=_sous(cout_temps),
        cout_entretien=_sous(cout_entretien),
        cout_total=_sous(cout_total),
        part_conducteur=_sous(part_conducteur),
        contribution_passagers=_sous(contribution),
        montant_brut_passagers=_sous(brut),
        prix_place=prix_place,
        commission_place=commission_place,
        net_conducteur_place=net_place,
        total_paye_passagers=prix_place * passagers_prevus,
        commission_kovoit=commission_place * passagers_prevus,
        net_conducteur=net_place * passagers_prevus,
        parametres=parametres,
    )


def participation_conducteur(devis: Devis, passagers: int) -> Decimal:
    """Ce que le trajet coûte réellement au conducteur avec `passagers` places payées.

    Les places vides ne sont pas compensées : moins de passagers, plus grosse participation.
    Négative seulement par l'effet des arrondis (quelques francs au plus).
    """
    return _sous(devis.cout_total - Decimal(devis.net_conducteur_place * passagers))
