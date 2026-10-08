from django.core.files.uploadedfile import SimpleUploadedFile

from apps.kyc.models import KycDossier, StatutKyc


def verifier_kyc(utilisateur, type_dossier: str) -> KycDossier:
    dossier, _ = KycDossier.objects.update_or_create(
        utilisateur=utilisateur, type=type_dossier, defaults={"statut": StatutKyc.VERIFIE}
    )
    return dossier


def fichier_png(nom: str = "piece.png", taille: int = 100) -> SimpleUploadedFile:
    return SimpleUploadedFile(nom, b"\x89PNG" + b"0" * taille, content_type="image/png")
