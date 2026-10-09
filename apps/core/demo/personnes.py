"""Personnes fictives : profils, dossiers KYC avec pièces (images générées), véhicules."""

import io
import unicodedata

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image, ImageDraw

from apps.accounts import services as comptes
from apps.accounts.repository import user_repository
from apps.kyc import services as kyc
from apps.kyc.models import TypePiece
from apps.vehicules import services as vehicules

DOMAINE = "demo.kovoit.tg"

PRENOMS = [
    "Kodjo", "Afi", "Kossi", "Yawa", "Komi", "Akossiwa", "Edem", "Mawuli", "Sena", "Dela",
    "Kafui", "Esso", "Abla", "Folly", "Ayélé", "Elom", "Sélom", "Enyonam", "Yao", "Ama",
    "Kokou", "Adjoa", "Fafa", "Dodzi",
]  # fmt: skip
NOMS = [
    "Mensah", "Amégan", "Akakpo", "Agbéko", "Lawson", "Kpodar", "Adjo", "Ahadji", "Dossou",
    "Tchalla", "Gbadoé", "Attiogbé", "Amouzou", "Kodjovi", "Sodji",
]  # fmt: skip
VOITURES = [
    ("Toyota", "Yaris", "Gris"),
    ("Kia", "Picanto", "Blanc"),
    ("Hyundai", "i10", "Rouge"),
    ("Toyota", "Corolla", "Noir"),
    ("Suzuki", "Swift", "Bleu"),
]
PIECES = {
    "passager": [TypePiece.IDENTITE, TypePiece.SELFIE],
    "conducteur": [
        TypePiece.IDENTITE,
        TypePiece.SELFIE,
        TypePiece.PERMIS,
        TypePiece.CARTE_GRISE,
        TypePiece.PHOTO_VEHICULE,
    ],
}


def _slug(valeur: str) -> str:
    sans_accents = unicodedata.normalize("NFD", valeur).encode("ascii", "ignore").decode()
    return sans_accents.lower()


def _image(titre: str, titulaire: str) -> SimpleUploadedFile:
    """Pièce fictive lisible dans la visionneuse du back-office."""
    image = Image.new("RGB", (640, 400), "#EFF3F9")
    dessin = ImageDraw.Draw(image)
    dessin.rectangle((24, 24, 616, 376), outline="#93A9CF", width=4)
    dessin.text((60, 150), titre, fill="#0F2A55", font_size=34)
    dessin.text((60, 210), titulaire, fill="#3D63A0", font_size=24)
    dessin.text((60, 300), "Document fictif - demonstration", fill="#D9731A", font_size=18)
    tampon = io.BytesIO()
    image.save(tampon, format="PNG")
    return SimpleUploadedFile(f"{_slug(titre)}.png", tampon.getvalue(), content_type="image/png")


def _identite(index: int) -> tuple[str, str]:
    return PRENOMS[index % len(PRENOMS)], NOMS[(index * 7) % len(NOMS)]


def email_de(index: int) -> str:
    prenom, nom = _identite(index)
    return f"{_slug(prenom)}.{_slug(nom)}{index}@{DOMAINE}"


def creer_personne(index: int):
    prenom, nom = _identite(index)
    utilisateur = user_repository.creer(email_de(index), email_verifie=True)
    return comptes.modifier_profil(
        utilisateur, nom=nom, prenom=prenom, telephone=f"+2289{index:07d}"
    )


def declarer_voiture(conducteur, index: int):
    marque, modele, couleur = VOITURES[index % len(VOITURES)]
    return vehicules.declarer(
        conducteur,
        type_vehicule="voiture",
        marque=marque,
        modele=modele,
        couleur=couleur,
        immatriculation=f"TG {1000 + index * 37} D{chr(65 + index % 26)}",
        nb_places=5,
    )


def soumettre_dossier(utilisateur, type_dossier: str):
    titulaire = f"{utilisateur.prenom} {utilisateur.nom}"
    for type_piece in PIECES[type_dossier]:
        titre = TypePiece(type_piece).label
        kyc.ajouter_piece(utilisateur, type_dossier, type_piece, _image(titre, titulaire))
    return kyc.soumettre(utilisateur, type_dossier)


def traiter_dossier(dossier, admin, motif_rejet: str | None = None):
    if motif_rejet:
        return kyc.rejeter(dossier.id, admin, motif_rejet)
    return kyc.valider(dossier.id, admin)
