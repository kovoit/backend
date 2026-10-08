"""Portefeuille simulé (PRD §7). Chaque mouvement est une ligne du journal `Transaction`.

solde_total = recharge + credit + remboursement − debit − retrait
bloque      = blocage − deblocage
disponible  = solde_total − bloque
"""

from dataclasses import dataclass

from django.db import transaction

from apps.accounts.repository import user_repository
from apps.core.exceptions import Conflit, DonneesInvalides
from apps.parametres.services import get_param
from apps.portefeuille.models import TypeTransaction as T
from apps.portefeuille.provider import provider
from apps.portefeuille.repository import transaction_repository


class SoldeInsuffisant(Conflit):
    code = "SOLDE_INSUFFISANT"
    message = "Solde disponible insuffisant. Rechargez votre portefeuille."


@dataclass
class Solde:
    total: int
    bloque: int
    disponible: int


def solde(utilisateur) -> Solde:
    s = transaction_repository.sommes_par_type(utilisateur)
    total = s.get(T.RECHARGE, 0) + s.get(T.CREDIT, 0) + s.get(T.REMBOURSEMENT, 0)
    total -= s.get(T.DEBIT, 0) + s.get(T.RETRAIT, 0)
    bloque = s.get(T.BLOCAGE, 0) - s.get(T.DEBLOCAGE, 0)
    return Solde(total=total, bloque=bloque, disponible=total - bloque)


def historique(utilisateur):
    return transaction_repository.historique(utilisateur)


def _ecrire(utilisateur, type_: str, montant: int, reservation=None, reference: str = ""):
    if montant > 0:
        transaction_repository.create(
            utilisateur=utilisateur,
            type=type_,
            montant=montant,
            reservation=reservation,
            reference_externe=reference,
        )


def _verrouiller(utilisateur) -> None:
    """Sérialise les opérations d'un même utilisateur (évite la double dépense)."""
    user_repository.get_for_update(utilisateur.id)


def recharger(utilisateur, montant: int) -> Solde:
    if montant < get_param("recharge_min"):
        raise DonneesInvalides(f"Recharge minimum : {get_param('recharge_min')} F CFA.")
    reference = provider.collecter(utilisateur, montant)
    _ecrire(utilisateur, T.RECHARGE, montant, reference=reference)
    return solde(utilisateur)


def retirer(utilisateur, montant: int) -> Solde:
    if montant < get_param("retrait_min"):
        raise DonneesInvalides(f"Retrait minimum : {get_param('retrait_min')} F CFA.")
    with transaction.atomic():
        _verrouiller(utilisateur)
        if solde(utilisateur).disponible < montant:
            raise SoldeInsuffisant("Solde disponible insuffisant pour ce retrait.")
        _ecrire(utilisateur, T.RETRAIT, montant, reference=provider.verser(utilisateur, montant))
    return solde(utilisateur)


# --- Mouvements liés à une réservation (appelés dans la transaction du service réservation) ---


def bloquer(reservation) -> None:
    passager = reservation.passager
    _verrouiller(passager)
    if solde(passager).disponible < reservation.montant_total:
        raise SoldeInsuffisant()
    _ecrire(passager, T.BLOCAGE, reservation.montant_total, reservation)


def debloquer(reservation) -> None:
    passager = reservation.passager
    bloque = transaction_repository.somme(passager, reservation, T.BLOCAGE)
    bloque -= transaction_repository.somme(passager, reservation, T.DEBLOCAGE)
    _ecrire(passager, T.DEBLOCAGE, bloque, reservation)


def debiter(reservation) -> None:
    """Le montant bloqué est réellement débité (code de départ saisi ou absence)."""
    debloquer(reservation)
    _ecrire(reservation.passager, T.DEBIT, reservation.montant_total, reservation)


def crediter_conducteur(reservation) -> None:
    """Le conducteur reçoit le prix ; les frais de service restent à Kovoit."""
    _ecrire(reservation.trajet.conducteur, T.CREDIT, reservation.prix, reservation)


def rembourser(reservation) -> None:
    debite = transaction_repository.somme(reservation.passager, reservation, T.DEBIT)
    _ecrire(reservation.passager, T.REMBOURSEMENT, debite, reservation)
