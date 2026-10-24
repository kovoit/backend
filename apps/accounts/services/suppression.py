"""Suppression du compte par l'utilisateur (exigence Google Play et App Store).

Le compte n'est pas effacé de la base : trajets, paiements et journal d'audit doivent rester
cohérents (et l'historique des transactions est conservé, obligation comptable). Il est
anonymisé et désactivé : identité, contact et photo effacés, pièces KYC supprimées,
téléphones et notifications effacés, sessions révoquées. Refusé tant qu'un engagement ou de
l'argent est en cours (rien ne doit rester bloqué pour un passager ou un conducteur).
"""

import uuid

from django.db import transaction

from apps.accounts.repository import user_repository
from apps.audit.services import journaliser
from apps.core.exceptions import ActionInterdite, Conflit

CONFIRMATION = "SUPPRIMER"


class SuppressionImpossible(Conflit):
    code = "SUPPRESSION_IMPOSSIBLE"


def obstacles(utilisateur) -> list[str]:
    """Ce qui empêche la suppression (liste vide : suppression possible)."""
    from apps.portefeuille.repository import transaction_repository
    from apps.portefeuille.services import solde
    from apps.reservations.repository import reservation_repository
    from apps.trajets.repository import trajet_repository

    raisons = []
    if reservation_repository.engagements_non_clos(utilisateur).exists():
        raisons.append("Vous avez une réservation en cours : annulez-la ou attendez sa clôture.")
    if trajet_repository.non_clos_de_conducteur(utilisateur).exists():
        raisons.append("Vous avez un trajet publié non terminé : annulez-le ou terminez-le.")
    if solde(utilisateur).total > 0:
        raisons.append("Votre portefeuille n'est pas vide : retirez d'abord votre solde.")
    if transaction_repository.operations_en_attente(utilisateur).exists():
        raisons.append("Une recharge ou un retrait est en attente : attendez qu'il soit traité.")
    return raisons


def supprimer_compte(utilisateur, confirmation: str) -> None:
    from apps.kyc.repository import piece_repository
    from apps.notifications.repository import appareil_repository, notification_repository

    if utilisateur.is_staff:
        raise ActionInterdite(
            "Un compte administrateur se supprime depuis le Django admin.", code="COMPTE_ADMIN"
        )
    if confirmation.strip().upper() != CONFIRMATION:
        raise ActionInterdite(
            f"Saisissez {CONFIRMATION} pour confirmer la suppression.", code="CONFIRMATION_REQUISE"
        )
    raisons = obstacles(utilisateur)
    if raisons:
        raise SuppressionImpossible(" ".join(raisons), erreurs={"raisons": raisons})

    with transaction.atomic():
        # Trace sans donnée personnelle : seul l'identifiant interne reste lié à l'événement
        journaliser("compte.supprimer", ressource=utilisateur, acteur=utilisateur)
        piece_repository.supprimer_de(utilisateur)  # fichiers des pièces d'identité effacés
        appareil_repository.supprimer_de(utilisateur)
        notification_repository.supprimer_de(utilisateur)
        user_repository.revoquer_sessions(utilisateur)
        user_repository.anonymiser(utilisateur, f"supprime-{uuid.uuid4().hex}@supprime.invalid")
