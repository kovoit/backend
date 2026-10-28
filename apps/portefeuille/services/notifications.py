"""Notifications de l'argent (F-063, D-06) : une seule par issue, jamais pendant l'attente.

Appelées dans la transaction qui écrit la transition de statut, sous verrou : la ligne de
notification disparaît si la transaction est annulée, et l'envoi ne part qu'après validation.
Les messages ne contiennent ni numéro de téléphone ni référence de l'opérateur."""

from apps.notifications.services import notifier
from apps.portefeuille.models import MoyenPaiement, Transaction
from apps.portefeuille.models import StatutTransaction as S


def montant_lisible(montant: int) -> str:
    """1000 → « 1 000 »."""
    return f"{montant:,}".replace(",", " ")


def _moyen(ligne: Transaction) -> str:
    """« Flooz (Moov Africa) » → « Flooz »."""
    if ligne.moyen_paiement not in MoyenPaiement.values:
        return "Mobile Money"
    return MoyenPaiement(ligne.moyen_paiement).label.split(" (")[0]


def _donnees(ligne: Transaction) -> dict:
    return {"type": "transaction", "transaction_id": str(ligne.id)}


def notifier_recharge(ligne: Transaction) -> None:
    """Recharge validée ou échouée ; rien tant qu'elle est en attente."""
    montant = montant_lisible(ligne.montant)
    if ligne.statut == S.VALIDEE:
        titre, message = "Recharge validée", f"Recharge de {montant} F validée"
    elif ligne.statut == S.ECHOUEE:
        titre, message = "Recharge non aboutie", f"Recharge de {montant} F non aboutie"
    else:
        return
    notifier(ligne.utilisateur, titre, message, _donnees(ligne))


def notifier_retrait(ligne: Transaction, motif: str = "") -> None:
    """Retrait versé (manuellement ou automatiquement) ou refusé ; rien tant qu'il attend.
    Titre court et fixe (120 caractères au plus en base) ; le motif va dans le message."""
    montant = montant_lisible(ligne.montant)
    if ligne.statut == S.VALIDEE:
        titre = "Retrait versé"
        message = f"Retrait de {montant} F versé sur votre compte {_moyen(ligne)}"
    elif ligne.statut == S.ECHOUEE:
        cause = f" : {motif.strip()}" if motif.strip() else ""
        titre = "Retrait refusé"
        message = f"Retrait refusé{cause} — le montant est de nouveau disponible"
    else:
        return
    notifier(ligne.utilisateur, titre, message, _donnees(ligne))
