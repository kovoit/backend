"""Suppression des données de démonstration (seed_demo, seed_backoffice), et d'elles seules.

Ordre imposé par les clés PROTECT : transactions → réservations → trajets → comptes.
Le reste (dossiers et pièces KYC, notes, signalements, véhicules, appareils, liens de partage)
part en cascade avec les comptes. Les fichiers (pièces KYC, photos) sont effacés après commit.
"""

from pathlib import Path

from django.db import transaction
from django.db.models import Q

from apps.accounts.repository import otp_repository, user_repository
from apps.dashboard.demo import COMPTES_DEMO
from apps.kyc.repository import piece_repository
from apps.portefeuille.repository import transaction_repository
from apps.reservations.repository import reservation_repository
from apps.trajets.repository import trajet_repository
from apps.vehicules.repository import vehicule_repository

SUFFIXES_DEMO = ("@demo.kovoit.tg", ".demo@kovoit.tg")


def _selections(comptes) -> dict:
    trajets = trajet_repository.filter(conducteur__in=comptes)
    # Réservations d'un passager de démo, ou sur un trajet de démo
    reservations = reservation_repository.filter(Q(passager__in=comptes) | Q(trajet__in=trajets))
    return {
        "transactions": transaction_repository.filter(
            Q(utilisateur__in=comptes) | Q(reservation__in=reservations)
        ),
        "reservations": reservations,
        "trajets": trajets,
        "comptes": comptes,
    }


def _comptes():
    return user_repository.filter(COMPTES_DEMO, is_staff=False, is_superuser=False)


def inventaire() -> dict[str, int]:
    """Ce qui serait supprimé, sans rien toucher."""
    comptes = _comptes()
    compte = {nom: qs.count() for nom, qs in _selections(comptes).items()}
    compte["pieces_kyc"] = piece_repository.filter(dossier__utilisateur__in=comptes).count()
    compte["codes_otp"] = otp_repository.filter(_emails_demo()).count()
    return compte


def _emails_demo() -> Q:
    condition = Q()
    for suffixe in SUFFIXES_DEMO:
        condition |= Q(email__iendswith=suffixe)
    return condition


def _fichiers(comptes) -> list:
    """(stockage, nom) de chaque fichier rattaché aux comptes de démo."""
    fichiers = [
        (piece.fichier.storage, piece.fichier.name)
        for piece in piece_repository.filter(dossier__utilisateur__in=comptes)
        if piece.fichier
    ]
    fichiers += [(u.photo.storage, u.photo.name) for u in comptes if u.photo]
    fichiers += [
        (v.photo.storage, v.photo.name)
        for v in vehicule_repository.filter(proprietaire__in=comptes)
        if v.photo
    ]
    return fichiers


def _effacer(fichiers) -> None:
    for stockage, nom in fichiers:
        if stockage.exists(nom):
            stockage.delete(nom)
        # Dossier propre à l'utilisateur (ex. prive/kyc/<id>/) : retiré une fois vide
        dossier = Path(stockage.path(nom)).parent
        if dossier.is_dir() and not any(dossier.iterdir()):
            dossier.rmdir()


def purger() -> dict[str, int]:
    """Supprime tout en une transaction : en cas d'erreur, la base reste intacte."""
    with transaction.atomic():
        comptes = _comptes()
        bilan = inventaire()
        fichiers = _fichiers(comptes)
        selections = _selections(comptes)
        for nom, repository in (
            ("transactions", transaction_repository),
            ("reservations", reservation_repository),
            ("trajets", trajet_repository),
        ):
            # list() : la sélection est figée avant suppression (elle dépend des lignes suivantes)
            ids = list(selections[nom].values_list("id", flat=True))
            repository.filter(id__in=ids).delete()
        otp_repository.filter(_emails_demo()).delete()
        comptes.delete()
        transaction.on_commit(lambda: _effacer(fichiers))
    bilan["fichiers"] = len(fichiers)
    return bilan
