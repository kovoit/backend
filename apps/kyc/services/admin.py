"""KYC côté administrateur : validation manuelle et consultation journalisée des pièces."""

from django.db import transaction
from django.utils import timezone

from apps.audit.services import journaliser
from apps.core.exceptions import Conflit, DonneesInvalides
from apps.kyc.models import KycDossier, KycPiece, StatutKyc
from apps.kyc.repository import consultation_repository, dossier_repository, piece_repository
from apps.notifications.services import notifier


def lister_dossiers(
    statut: str | None = None, type_dossier: str | None = None, recherche: str | None = None
):
    return dossier_repository.lister(statut, type_dossier, recherche)


def dossiers_soumis(utilisateur):
    return dossier_repository.soumis_de(utilisateur)


def get_dossier(dossier_id) -> KycDossier:
    return dossier_repository.get_by_id(dossier_id)


def _traiter(dossier_id, admin, statut: str, motif: str = "") -> KycDossier:
    action = "kyc.valider" if statut == StatutKyc.VERIFIE else "kyc.rejeter"
    with transaction.atomic():
        dossier = dossier_repository.get_for_update(dossier_id)
        if dossier.statut != StatutKyc.EN_ATTENTE:
            raise Conflit(
                "Seul un dossier en attente peut être traité.", code="DOSSIER_NON_EN_ATTENTE"
            )
        dossier_repository.update(
            dossier, statut=statut, motif_rejet=motif, traite_le=timezone.now(), traite_par=admin
        )
        journaliser(
            action,
            ressource=dossier,
            acteur=admin,
            changements={"statut": [StatutKyc.EN_ATTENTE, statut]},
            details={
                "type_dossier": dossier.type,
                "utilisateur_id": dossier.utilisateur_id,
                "motif": motif,
            },
        )
    return dossier_repository.get_by_id(dossier_id)


def valider(dossier_id, admin) -> KycDossier:
    dossier = _traiter(dossier_id, admin, StatutKyc.VERIFIE)
    notifier(
        dossier.utilisateur,
        "Identité vérifiée",
        f"Votre dossier {dossier.get_type_display().lower()} a été validé.",
    )
    return dossier


def rejeter(dossier_id, admin, motif: str) -> KycDossier:
    if not motif.strip():
        raise DonneesInvalides("Le motif de rejet est obligatoire.", code="MOTIF_OBLIGATOIRE")
    dossier = _traiter(dossier_id, admin, StatutKyc.REJETE, motif.strip())
    notifier(
        dossier.utilisateur,
        "Dossier rejeté",
        f"Votre dossier {dossier.get_type_display().lower()} a été rejeté : {dossier.motif_rejet}. "
        "Vous pouvez le corriger et le soumettre à nouveau.",
    )
    return dossier


def consulter_piece(piece_id, admin) -> KycPiece:
    """Renvoie la pièce et journalise la consultation (données sensibles)."""
    piece = piece_repository.get_by_id(piece_id)
    with transaction.atomic():
        consultation_repository.create(piece=piece, admin=admin)
        journaliser(
            "kyc.consulter_piece",
            ressource=piece,
            acteur=admin,
            details={"type_piece": piece.type_piece, "dossier_id": piece.dossier_id},
        )
    return piece
