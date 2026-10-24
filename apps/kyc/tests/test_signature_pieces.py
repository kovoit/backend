"""Pièces KYC : le contenu réel du fichier est vérifié, pas seulement le type annoncé."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.exceptions import DonneesInvalides
from apps.kyc import services
from apps.kyc.models import KycPiece

pytestmark = pytest.mark.django_db


def deposer(utilisateur, contenu: bytes, nom="piece.jpg", type_mime="image/jpeg"):
    fichier = SimpleUploadedFile(nom, contenu, content_type=type_mime)
    return services.ajouter_piece(utilisateur, "passager", "identite", fichier)


@pytest.mark.parametrize(
    ("contenu", "extension"),
    [
        (b"\xff\xd8\xff\xe0" + b"0" * 50, ".jpg"),
        (b"\x89PNG\r\n\x1a\n" + b"0" * 50, ".png"),
        (b"%PDF-1.7\n" + b"0" * 50, ".pdf"),
    ],
)
def test_vrais_formats_acceptes_extension_choisie_par_le_serveur(utilisateur, contenu, extension):
    deposer(utilisateur, contenu, nom="mon fichier.HTML")

    piece = KycPiece.objects.get()
    assert piece.fichier.name.endswith(extension)
    assert "HTML" not in piece.fichier.name


@pytest.mark.parametrize(
    "contenu",
    [b"<html><script>alert(1)</script></html>", b"MZ\x90\x00executable", b"GIF89a" + b"0" * 20],
)
def test_faux_jpeg_refuse(utilisateur, contenu):
    with pytest.raises(DonneesInvalides) as exc:
        deposer(utilisateur, contenu)

    assert exc.value.code == "FORMAT_PIECE_INVALIDE"
    assert not KycPiece.objects.exists()
