"""Photos sur Cloudinary (CLOUDINARY_URL) : envoi, URL du CDN, suppression. Aucun appel réseau :
le SDK Cloudinary est remplacé par un faux qui garde les envois en mémoire."""

from io import BytesIO
from pathlib import Path

import cloudinary.uploader
import pytest
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.core import stockage
from apps.core.stockage import StockageCloudinary, compte_cloudinary
from apps.kyc.models import KycPiece, StockagePrive

URL_COMPTE = "cloudinary://123456:secret%2Fabc@kovoit-demo"
CDN = "https://res.cloudinary.com/kovoit-demo/image/upload/v1/"  # v1 : image dans un dossier


class FauxCloudinary:
    def __init__(self):
        self.envois: dict[str, bytes] = {}
        self.suppressions: list[str] = []
        self.options: list[dict] = []

    def upload(self, fichier, public_id, **options):
        self.envois[public_id] = fichier.read()
        self.options.append(options)
        return {"public_id": public_id, "format": "jpg"}

    def destroy(self, public_id, **options):
        self.suppressions.append(public_id)
        return {"result": "ok"}


@pytest.fixture
def faux_cloudinary(monkeypatch, settings):
    faux = FauxCloudinary()
    monkeypatch.setattr(cloudinary.uploader, "upload", faux.upload)
    monkeypatch.setattr(cloudinary.uploader, "destroy", faux.destroy)
    settings.CLOUDINARY_URL = URL_COMPTE
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {"BACKEND": "apps.core.stockage.StockageCloudinary"},
    }
    return faux


def jpeg(nom="moi.jpg") -> SimpleUploadedFile:
    tampon = BytesIO()
    Image.new("RGB", (32, 32), (200, 120, 40)).save(tampon, format="JPEG")
    return SimpleUploadedFile(nom, tampon.getvalue(), content_type="image/jpeg")


def test_compte_lu_depuis_l_url():
    assert compte_cloudinary(URL_COMPTE) == {
        "cloud_name": "kovoit-demo",
        "api_key": "123456",
        "api_secret": "secret/abc",
    }


@pytest.mark.parametrize("url", ["", "https://kovoit-demo", "cloudinary://123456@kovoit-demo"])
def test_url_de_compte_invalide_refusee(url):
    with pytest.raises(ImproperlyConfigured, match="CLOUDINARY_URL invalide"):
        compte_cloudinary(url)


@pytest.mark.django_db
def test_photo_de_profil_envoyee_sur_cloudinary(client_utilisateur, utilisateur, faux_cloudinary):
    reponse = client_utilisateur.patch("/api/v1/moi/", {"photo": jpeg()}, format="multipart")

    assert reponse.status_code == 200
    url = reponse.json()["reponse"]["photo"]
    (public_id,) = faux_cloudinary.envois
    assert public_id.startswith("photos_profil/moi_")
    assert url == f"{CDN}{public_id}.jpg"
    assert faux_cloudinary.options[0]["cloud_name"] == "kovoit-demo"
    utilisateur.refresh_from_db()
    assert utilisateur.photo.name == f"{public_id}.jpg"
    assert not Path(utilisateur.photo.name).exists()  # rien sur le disque du serveur


def test_deux_envois_du_meme_nom_ne_s_ecrasent_pas(faux_cloudinary):
    photos = StockageCloudinary()

    premier = photos.save("vehicules/yaris.jpg", ContentFile(b"a"))
    second = photos.save("vehicules/yaris.jpg", ContentFile(b"b"))

    assert premier != second and len(faux_cloudinary.envois) == 2
    assert photos.exists(premier) is False


def test_nom_trop_long_raccourci_pour_le_champ(faux_cloudinary):
    nom = StockageCloudinary().save(f"photos_profil/{'x' * 150}.jpg", ContentFile(b"a"))

    assert len(nom) <= 100


def test_suppression_de_la_photo(faux_cloudinary):
    photos = StockageCloudinary()
    nom = photos.save("vehicules/yaris.jpg", ContentFile(b"a"))

    photos.delete(nom)
    photos.delete("")

    assert faux_cloudinary.suppressions == [nom.removesuffix(".jpg")]


def test_lecture_par_le_cdn(faux_cloudinary, monkeypatch):
    lues = []

    class Reponse(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def faux_urlopen(url, timeout):
        lues.append(url)
        return Reponse(b"octets")

    monkeypatch.setattr(stockage, "urlopen", faux_urlopen)

    fichier = StockageCloudinary().open("vehicules/yaris_ab12cd34.jpg")

    assert fichier.read() == b"octets"
    assert lues == [f"{CDN}vehicules/yaris_ab12cd34.jpg"]


def test_les_pieces_kyc_ne_vont_jamais_sur_cloudinary(faux_cloudinary):
    assert isinstance(KycPiece._meta.get_field("fichier").storage, StockagePrive)
