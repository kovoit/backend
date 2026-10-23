"""Recharges et retraits par Mobile Money (Flooz, Mixx) via le fournisseur configuré.

Recharge : la ligne est créée « en attente » AVANT l'appel au fournisseur (identifiant envoyé
à PayGate = id de la ligne), puis validée quand le fournisseur confirme. La confirmation
(client qui interroge, callback PayGate ou tâche planifiée) revérifie toujours le statut
auprès du fournisseur : le contenu d'un callback n'est jamais cru sur parole.
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.audit.models import Resultat as R
from apps.audit.services import journaliser
from apps.core.exceptions import Conflit, DonneesInvalides
from apps.parametres.services import get_param
from apps.portefeuille.models import StatutTransaction as S
from apps.portefeuille.models import Transaction
from apps.portefeuille.models import TypeTransaction as T
from apps.portefeuille.provider import PaiementIndisponible, get_provider
from apps.portefeuille.repository import transaction_repository
from apps.portefeuille.services.commun import (
    SoldeInsuffisant,
    ecrire,
    solde,
    verifier_moyen,
    verrouiller,
)


def _telephone(utilisateur, telephone: str) -> str:
    numero = (telephone or utilisateur.telephone or "").strip()
    if not numero:
        raise DonneesInvalides("Indiquez le numéro Mobile Money.", code="TELEPHONE_REQUIS")
    return numero


def _details(ligne: Transaction) -> dict:
    return {
        "transaction_id": ligne.id,
        "montant": ligne.montant,
        "moyen": ligne.moyen_paiement,
        "reference": ligne.reference_externe,
    }


def recharger(utilisateur, montant: int, moyen: str, telephone: str = "") -> Transaction:
    verifier_moyen(moyen)
    if montant < get_param("recharge_min"):
        raise DonneesInvalides(f"Recharge minimum : {get_param('recharge_min')} F CFA.")
    numero = _telephone(utilisateur, telephone)
    ligne = ecrire(
        utilisateur, T.RECHARGE, montant, moyen=moyen, statut=S.EN_ATTENTE, telephone=numero
    )
    try:  # appel externe hors transaction : la ligne en attente reste la trace de la demande
        resultat = get_provider().collecter(utilisateur, montant, moyen, numero, str(ligne.id))
    except PaiementIndisponible as exc:
        with transaction.atomic():
            transaction_repository.update(ligne, statut=S.ECHOUEE)
            journaliser(
                "paiement.initier",
                ressource=utilisateur,
                resultat=R.ECHEC,
                code_motif=exc.code,
                details=_details(ligne),
            )
        raise
    with transaction.atomic():
        ligne = transaction_repository.update(
            ligne, reference_externe=resultat.reference, statut=resultat.statut
        )
        action = "portefeuille.recharger" if resultat.statut == S.VALIDEE else "paiement.initier"
        journaliser(action, ressource=utilisateur, details=_details(ligne))
    return ligne


def _actualiser(transaction_id, systeme: bool) -> Transaction:
    """Interroge le fournisseur puis valide ou fait échouer la recharge (une seule fois)."""
    ligne = transaction_repository.get_by_id(transaction_id)
    resultat = get_provider().verifier(str(ligne.id), ligne.reference_externe)
    if resultat.statut == S.EN_ATTENTE:
        return ligne
    with transaction.atomic():
        ligne = transaction_repository.get_verrouillee(transaction_id)
        if ligne.statut != S.EN_ATTENTE:  # déjà traitée (callback et client en même temps)
            return ligne
        ligne = transaction_repository.update(
            ligne,
            statut=resultat.statut,
            reference_externe=resultat.reference,
            reference_operateur=resultat.reference_operateur,
        )
        journaliser(
            "paiement.confirmer",
            ressource=ligne.utilisateur,
            acteur=None if systeme else ligne.utilisateur,
            systeme=systeme,
            resultat=R.SUCCES if resultat.statut == S.VALIDEE else R.ECHEC,
            code_motif=resultat.code,
            details=_details(ligne),
        )
    return ligne


def verifier_paiement(utilisateur, transaction_id) -> Transaction:
    """Le client interroge l'état de sa recharge (écran d'attente de l'app mobile)."""
    ligne = transaction_repository.get_de(utilisateur, transaction_id)
    if ligne.type == T.RECHARGE and ligne.statut == S.EN_ATTENTE:
        return _actualiser(ligne.id, systeme=False)
    return ligne


def confirmer_par_callback(identifiant: str) -> None:
    """Callback PayGate : seul l'identifiant est retenu, le statut est revérifié."""
    ligne = transaction_repository.get_or_none(pk=identifiant, type=T.RECHARGE)
    if ligne is not None and ligne.statut == S.EN_ATTENTE:
        _actualiser(ligne.id, systeme=True)


def _abandonner(ligne: Transaction) -> None:
    with transaction.atomic():
        ligne = transaction_repository.update(ligne, statut=S.ECHOUEE)
        journaliser(
            "paiement.confirmer",
            ressource=ligne.utilisateur,
            systeme=True,
            resultat=R.ECHEC,
            code_motif="DELAI_DEPASSE",
            details=_details(ligne),
        )


def verifier_paiements_en_attente() -> int:
    """Tâche planifiée : rattrape les callbacks perdus ; abandonne au-delà du délai maximal."""
    limite = timezone.now() - timedelta(minutes=get_param("paiement_attente_max_min"))
    traites = 0
    for ligne in transaction_repository.recharges_en_attente(limite):
        traites += _actualiser(ligne.id, systeme=True).statut != S.EN_ATTENTE
    for ligne in transaction_repository.recharges_expirees(limite):
        # Dernière vérification : un paiement confirmé tardivement n'est jamais perdu
        if _actualiser(ligne.id, systeme=True).statut == S.EN_ATTENTE:
            _abandonner(ligne)
        traites += 1
    return traites


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
    return ligne


def traiter_retrait(admin, transaction_id, verse: bool, reference: str = "") -> Transaction:
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
            details=_details(ligne),
        )
    return ligne
