"""Portefeuille (PRD §7). Chaque mouvement est une ligne du journal `Transaction`.

solde_total = recharge + credit + remboursement − debit − retrait − commission  (voir
bloque      = blocage − deblocage                                    repository.COMPTEES)
disponible  = solde_total − bloque
"""

import re
from dataclasses import dataclass

from apps.accounts.repository import user_repository
from apps.core.exceptions import Conflit, DonneesInvalides
from apps.portefeuille.models import MoyenPaiement, StatutTransaction
from apps.portefeuille.models import TypeTransaction as T
from apps.portefeuille.repository import transaction_repository


class SoldeInsuffisant(Conflit):
    code = "SOLDE_INSUFFISANT"
    message = "Solde disponible insuffisant. Rechargez votre portefeuille."


def moyens_paiement() -> list[dict]:
    return [{"code": code, "libelle": libelle} for code, libelle in MoyenPaiement.choices]


def verifier_moyen(moyen: str) -> None:
    if moyen not in MoyenPaiement.values:
        raise DonneesInvalides("Moyen de paiement inconnu (flooz ou mixx).", code="MOYEN_INCONNU")


def numero_mobile_money(numero: str) -> str:
    """Numéro togolais à 8 chiffres (ex. 90123456) : espaces et indicatif +228 / 00228 retirés."""
    chiffres = re.sub(r"\D", "", numero or "")
    if len(chiffres) > 8 and chiffres.startswith(("00228", "228")):
        chiffres = chiffres.removeprefix("00").removeprefix("228")
    if len(chiffres) != 8:
        raise DonneesInvalides(
            "Numéro Mobile Money togolais invalide (8 chiffres, ex. 90 12 34 56).",
            code="TELEPHONE_INVALIDE",
        )
    return chiffres


@dataclass
class Solde:
    total: int
    bloque: int
    disponible: int


def solde(utilisateur) -> Solde:
    s = transaction_repository.sommes_par_type(utilisateur)
    total = s.get(T.RECHARGE, 0) + s.get(T.CREDIT, 0) + s.get(T.REMBOURSEMENT, 0)
    total -= s.get(T.DEBIT, 0) + s.get(T.RETRAIT, 0) + s.get(T.COMMISSION, 0)
    bloque = s.get(T.BLOCAGE, 0) - s.get(T.DEBLOCAGE, 0)
    return Solde(total=total, bloque=bloque, disponible=total - bloque)


def historique(utilisateur):
    return transaction_repository.historique(utilisateur)


def ecrire(
    utilisateur,
    type_: str,
    montant: int,
    reservation=None,
    reference: str = "",
    moyen: str = "",
    statut: str = StatutTransaction.VALIDEE,
    telephone: str = "",
):
    if montant > 0:
        return transaction_repository.create(
            utilisateur=utilisateur,
            type=type_,
            montant=montant,
            reservation=reservation,
            reference_externe=reference,
            moyen_paiement=moyen,
            statut=statut,
            telephone=telephone,
        )
    return None


def recharge_suggeree(complement: int) -> int:
    """Montant à proposer pour combler un complément : au moins la recharge minimale."""
    from apps.parametres.services import get_param

    return max(complement, get_param("recharge_min")) if complement > 0 else 0


def apercu_paiement(utilisateur, montant: int) -> dict:
    """Écran « Détails du trajet » : ce qui sera pris sur le portefeuille et le complément."""
    disponible = max(solde(utilisateur).disponible, 0)
    complement = max(montant - disponible, 0)
    return {
        "montant_total": montant,
        "solde_disponible": disponible,
        "complement_a_payer": complement,
        "recharge_suggeree": recharge_suggeree(complement),
        "moyens_paiement": moyens_paiement(),
    }


def verrouiller(utilisateur) -> None:
    """Sérialise les opérations d'un même utilisateur (évite la double dépense)."""
    user_repository.get_for_update(utilisateur.id)
