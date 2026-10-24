"""KYC côté utilisateur : ajout des pièces, soumission, statuts."""

from django.db import transaction
from django.utils import timezone

from apps.audit.services import journaliser
from apps.core.exceptions import ActionInterdite, Conflit, DonneesInvalides
from apps.kyc.models import KycDossier, StatutKyc, TypeDossier, TypePiece
from apps.kyc.repository import dossier_repository, piece_repository
from apps.vehicules.repository import vehicule_repository

TAILLE_MAX_OCTETS = 5 * 1024 * 1024
TYPES_MIME_ACCEPTES = {"image/jpeg", "image/png", "application/pdf"}
# Signature réelle du fichier (premiers octets) → extension choisie par le serveur. Le type
# annoncé par le téléphone et le nom du fichier ne sont pas crus.
SIGNATURES = (
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"%PDF-", ".pdf"),
)


def _extension_reelle(fichier) -> str | None:
    debut = fichier.read(8)
    fichier.seek(0)
    return next((ext for signature, ext in SIGNATURES if debut.startswith(signature)), None)


PIECES_OBLIGATOIRES = {
    TypeDossier.PASSAGER: {TypePiece.IDENTITE, TypePiece.SELFIE},
    TypeDossier.CONDUCTEUR: {
        TypePiece.IDENTITE,
        TypePiece.SELFIE,
        TypePiece.PERMIS,
        TypePiece.PHOTO_VEHICULE,
    },
}
# Le conducteur fournit au moins l'une de ces deux pièces
PIECES_AU_CHOIX_CONDUCTEUR = {TypePiece.CARTE_GRISE, TypePiece.ASSURANCE}
STATUTS_MODIFIABLES = {StatutKyc.NON_VERIFIE, StatutKyc.REJETE}


class DossierNonModifiable(Conflit):
    code = "DOSSIER_NON_MODIFIABLE"
    message = "Ce dossier est en cours de vérification ou déjà vérifié."


class DossierIncomplet(DonneesInvalides):
    code = "DOSSIER_INCOMPLET"
    message = "Des pièces obligatoires manquent au dossier."


def _type_dossier(valeur: str) -> TypeDossier:
    if valeur not in TypeDossier.values:
        raise DonneesInvalides("Type de dossier inconnu (passager ou conducteur).")
    return TypeDossier(valeur)


def pieces_manquantes(dossier: KycDossier) -> list[str]:
    presentes = piece_repository.types_presents(dossier)
    manquantes = sorted(PIECES_OBLIGATOIRES[dossier.type] - presentes)
    if dossier.type == TypeDossier.CONDUCTEUR and not presentes & PIECES_AU_CHOIX_CONDUCTEUR:
        manquantes.append("carte_grise_ou_assurance")
    return manquantes


def mes_dossiers(utilisateur) -> list[KycDossier]:
    return [dossier_repository.get_ou_creer(utilisateur, type_) for type_ in TypeDossier]


def ajouter_piece(utilisateur, type_dossier: str, type_piece: str, fichier) -> KycDossier:
    type_dossier = _type_dossier(type_dossier)
    autorisees = PIECES_OBLIGATOIRES[type_dossier]
    if type_dossier == TypeDossier.CONDUCTEUR:
        autorisees = autorisees | PIECES_AU_CHOIX_CONDUCTEUR
    if type_piece not in autorisees:
        raise DonneesInvalides(f"La pièce « {type_piece} » n'est pas demandée pour ce dossier.")
    if fichier.size > TAILLE_MAX_OCTETS:
        raise DonneesInvalides("Fichier trop volumineux (5 Mo maximum).")
    extension = _extension_reelle(fichier)
    if getattr(fichier, "content_type", None) not in TYPES_MIME_ACCEPTES or extension is None:
        raise DonneesInvalides("Format accepté : JPEG, PNG ou PDF.", code="FORMAT_PIECE_INVALIDE")
    fichier.name = f"piece{extension}"  # le nom envoyé par le client n'est jamais conservé

    with transaction.atomic():
        dossier = dossier_repository.get_verrouille(utilisateur, type_dossier)
        if dossier.statut not in STATUTS_MODIFIABLES:
            raise DossierNonModifiable()
        piece_repository.remplacer(dossier, type_piece, fichier)
        # Le type de pièce seulement : jamais le fichier ni son contenu
        journaliser(
            "kyc.deposer_piece",
            ressource=dossier,
            details={"type_dossier": type_dossier, "type_piece": type_piece},
        )
    return dossier_repository.get_by_id(dossier.id)


def soumettre(utilisateur, type_dossier: str) -> KycDossier:
    type_dossier = _type_dossier(type_dossier)
    if not utilisateur.profil_complet:
        raise ActionInterdite(
            "Complétez votre profil (nom, prénom, téléphone) avant de soumettre.",
            code="PROFIL_INCOMPLET",
        )
    with transaction.atomic():
        dossier = dossier_repository.get_verrouille(utilisateur, type_dossier)
        if dossier.statut not in STATUTS_MODIFIABLES:
            raise DossierNonModifiable()
        manquantes = pieces_manquantes(dossier)
        if manquantes:
            raise DossierIncomplet(erreurs={"pieces_manquantes": manquantes})
        dossier_repository.update(
            dossier, statut=StatutKyc.EN_ATTENTE, soumis_le=timezone.now(), motif_rejet=""
        )
        journaliser("kyc.soumettre", ressource=dossier, details={"type_dossier": type_dossier})
    return dossier_repository.get_by_id(dossier.id)


def est_verifie(utilisateur, type_dossier: str) -> bool:
    return dossier_repository.est_verifie(utilisateur, type_dossier)


def peut_publier(utilisateur) -> bool:
    """KYC conducteur vérifié et au moins un véhicule déclaré."""
    return est_verifie(utilisateur, TypeDossier.CONDUCTEUR) and vehicule_repository.exists(
        proprietaire=utilisateur
    )


def statuts_kyc(utilisateur) -> dict[str, str]:
    statuts = dossier_repository.statuts_de(utilisateur)
    return {type_: statuts.get(type_, StatutKyc.NON_VERIFIE) for type_ in TypeDossier.values}
