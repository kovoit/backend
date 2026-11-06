"""Photos (profil, véhicule) sur Cloudinary, activé par la variable CLOUDINARY_URL.

Les pièces KYC n'y passent jamais : elles ont leur propre stockage privé (`apps.kyc.models`).
Le nom gardé en base est l'identifiant Cloudinary suivi de l'extension
(`photos_profil/moi_3f9a1c2b.jpg`) ; l'URL renvoyée est celle du CDN, en HTTPS.
"""

import posixpath
import uuid
from urllib.parse import unquote, urlparse
from urllib.request import urlopen

import cloudinary
import cloudinary.uploader
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

# Les noms tiennent dans un FileField (100 caractères) une fois le suffixe unique ajouté
LONGUEUR_MAX_RACINE = 80


def compte_cloudinary(url: str) -> dict[str, str]:
    """`cloudinary://<api_key>:<api_secret>@<cloud_name>` → identifiants du compte."""
    morceaux = urlparse(url)
    cloud_name = morceaux.netloc.rpartition("@")[2]
    complet = morceaux.username and morceaux.password and cloud_name
    if morceaux.scheme != "cloudinary" or not complet:
        raise ImproperlyConfigured(
            "CLOUDINARY_URL invalide : attendu cloudinary://<api_key>:<api_secret>@<cloud_name>"
        )
    return {
        "cloud_name": cloud_name,
        "api_key": unquote(morceaux.username),
        "api_secret": unquote(morceaux.password),
    }


def _identifiant(nom: str) -> tuple[str, str]:
    """Nom en base → (identifiant Cloudinary, format sans le point)."""
    racine, extension = posixpath.splitext(nom)
    return racine, extension.lstrip(".")


@deconstructible
class StockageCloudinary(Storage):
    def __init__(self, url: str | None = None):
        self.url_compte = url

    @property
    def _compte(self) -> dict[str, str]:
        return compte_cloudinary(self.url_compte or settings.CLOUDINARY_URL)

    def _save(self, name, content):
        racine, _ = _identifiant(name)
        public_id = f"{racine[:LONGUEUR_MAX_RACINE]}_{uuid.uuid4().hex[:8]}"
        if hasattr(content, "seek"):
            content.seek(0)
        resultat = cloudinary.uploader.upload(
            content, public_id=public_id, resource_type="image", overwrite=False, **self._compte
        )
        return f"{resultat['public_id']}.{resultat['format']}"

    def _open(self, name, mode="rb"):
        with urlopen(self.url(name), timeout=10) as reponse:  # noqa: S310 — URL HTTPS du CDN
            return ContentFile(reponse.read(), name=name)

    def delete(self, name):
        if name:
            public_id, _ = _identifiant(name)
            cloudinary.uploader.destroy(public_id, invalidate=True, **self._compte)

    def exists(self, name):
        # Chaque envoi reçoit un suffixe unique : aucun nom ne peut déjà exister
        return False

    def url(self, name):
        public_id, extension = _identifiant(name)
        image = cloudinary.CloudinaryImage(public_id)
        return image.build_url(
            secure=True, format=extension or None, cloud_name=self._compte["cloud_name"]
        )
