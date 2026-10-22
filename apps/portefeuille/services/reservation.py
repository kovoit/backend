"""Mouvements liés à une réservation (appelés dans la transaction du service réservation)."""

from apps.portefeuille.models import MoyenPaiement
from apps.portefeuille.models import TypeTransaction as T
from apps.portefeuille.provider import get_provider
from apps.portefeuille.repository import transaction_repository
from apps.portefeuille.services.commun import (
    SoldeInsuffisant,
    ecrire,
    recharge_suggeree,
    solde,
    verifier_moyen,
    verrouiller,
)


def bloquer(reservation, moyen: str | None = None) -> int:
    """Bloque le montant sur le portefeuille et renvoie le complément encaissé (0 si le solde
    suffisait). Avec un paiement à confirmer (PayGate), le complément ne peut pas être encaissé
    pendant la réservation : le passager recharge d'abord ce complément, puis réserve."""
    passager = reservation.passager
    verrouiller(passager)
    complement = max(reservation.montant_total - solde(passager).disponible, 0)
    fournisseur = get_provider()
    if complement and (fournisseur.asynchrone or not moyen):
        message = (
            f"Solde insuffisant : rechargez {complement} F CFA par Flooz ou Mixx, puis réservez."
            if fournisseur.asynchrone
            else f"Solde insuffisant : payez le complément de {complement} F CFA par Flooz ou Mixx."
        )
        raise SoldeInsuffisant(
            message,
            erreurs={
                "complement_a_payer": complement,
                "recharge_suggeree": recharge_suggeree(complement),
                "moyens_paiement": MoyenPaiement.values,
                "recharge_requise": fournisseur.asynchrone,
            },
        )
    if complement:
        verifier_moyen(moyen)
        identifiant = f"resa-{reservation.id}"
        resultat = fournisseur.collecter(
            passager, complement, moyen, passager.telephone, identifiant
        )
        ecrire(passager, T.RECHARGE, complement, reservation, resultat.reference, moyen)
    ecrire(passager, T.BLOCAGE, reservation.montant_total, reservation)
    return complement


def debloquer(reservation) -> None:
    passager = reservation.passager
    bloque = transaction_repository.somme(passager, reservation, T.BLOCAGE)
    bloque -= transaction_repository.somme(passager, reservation, T.DEBLOCAGE)
    ecrire(passager, T.DEBLOCAGE, bloque, reservation)


def debiter(reservation) -> None:
    """Le montant bloqué est réellement débité (code de départ saisi ou absence)."""
    debloquer(reservation)
    ecrire(reservation.passager, T.DEBIT, reservation.montant_total, reservation)


def crediter_conducteur(reservation) -> None:
    """Le conducteur reçoit le prix ; les frais de service restent à Kovoit."""
    ecrire(reservation.trajet.conducteur, T.CREDIT, reservation.prix, reservation)


def rembourser(reservation) -> None:
    debite = transaction_repository.somme(reservation.passager, reservation, T.DEBIT)
    ecrire(reservation.passager, T.REMBOURSEMENT, debite, reservation)
