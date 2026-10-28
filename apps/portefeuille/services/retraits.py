"""Retraits vers Flooz / Mixx : montant retenu tout de suite, versé (ou refusé) par Kovoit."""

from django.db import transaction

from apps.audit.models import Resultat as R
from apps.audit.services import journaliser
from apps.core.exceptions import Conflit, DonneesInvalides
from apps.parametres.services import get_param
from apps.portefeuille.models import StatutTransaction as S
from apps.portefeuille.models import Transaction
from apps.portefeuille.models import TypeTransaction as T
from apps.portefeuille.provider import get_provider
from apps.portefeuille.repository import transaction_repository
from apps.portefeuille.services.commun import (
    SoldeInsuffisant,
    ecrire,
    solde,
    verifier_moyen,
    verrouiller,
)
from apps.portefeuille.services.mobile_money import _details, _telephone
from apps.portefeuille.services.notifications import notifier_retrait


def retirer(utilisateur, montant: int, moyen: str, telephone: str = "") -> Transaction:
    """Avec PayGate, le retrait est retenu tout de suite et versé manuellement par Kovoit."""
    verifier_moyen(moyen)
    if montant < get_param("retrait_min"):
        raise DonneesInvalides(f"Retrait minimum : {get_param('retrait_min')} F CFA.")
    numero = _telephone(utilisateur, telephone)
    with transaction.atomic():
        verrouiller(utilisateur)
        if solde(utilisateur).disponible < montant:
            raise SoldeInsuffisant("Solde disponible insuffisant pour ce retrait.")
        resultat = get_provider().verser(utilisateur, montant, moyen, numero)
        ligne = ecrire(
            utilisateur,
            T.RETRAIT,
            montant,
            reference=resultat.reference,
            moyen=moyen,
            statut=resultat.statut,
            telephone=numero,
        )
        journaliser(
            "portefeuille.retirer",
            ressource=utilisateur,
            details={**_details(ligne), "statut": ligne.statut},
        )
        notifier_retrait(ligne)  # versé tout de suite (versement automatique) ; rien si en attente
    return ligne


def traiter_retrait(
    admin, transaction_id, verse: bool, reference: str = "", motif: str = ""
) -> Transaction:
    """Back-office : versement manuel effectué (ou refusé : le montant redevient disponible)."""
    with transaction.atomic():
        ligne = transaction_repository.get_verrouillee(transaction_id)
        if ligne.type != T.RETRAIT or ligne.statut != S.EN_ATTENTE:
            raise Conflit("Ce retrait n'est pas en attente.", code="RETRAIT_NON_EN_ATTENTE")
        ligne = transaction_repository.update(
            ligne,
            statut=S.VALIDEE if verse else S.ECHOUEE,
            reference_externe=reference or ligne.reference_externe,
        )
        journaliser(
            "portefeuille.verser",
            ressource=ligne.utilisateur,
            acteur=admin,
            resultat=R.SUCCES if verse else R.REFUS,
            details={**_details(ligne), **({"motif": motif} if motif else {})},
        )
        notifier_retrait(ligne, motif)
    return ligne
