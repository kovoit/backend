"""F-003, CA-003-3 (D-19) : photo de profil envoyée par PATCH /moi/ (multipart, champ `photo`),
relue par GET /moi/ et visible du passager sur la carte conducteur (recherche, détail du trajet,
profil public)."""

import random
from io import BytesIO
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.accounts.models import User
from conftest import ADIDOGOME, GRAND_MARCHE, publier_trajet

pytestmark = pytest.mark.django_db

MOI = "/api/v1/moi/"


@pytest.fixture(autouse=True)
def media_temporaire(settings, tmp_path) -> Path:
    """Photos écrites dans un dossier temporaire : rien ne reste dans le dépôt."""
    settings.MEDIA_ROOT = str(tmp_path / "media_photos")
    return Path(settings.MEDIA_ROOT)


def jpeg(nom="moi.jpg", couleur=(200, 120, 40)) -> SimpleUploadedFile:
    tampon = BytesIO()
    Image.new("RGB", (64, 64), couleur).save(tampon, format="JPEG")
    return SimpleUploadedFile(nom, tampon.getvalue(), content_type="image/jpeg")


def envoyer_photo(client, fichier):
    return client.patch(MOI, {"photo": fichier}, format="multipart")


def url_photo_envoyee(client, fichier) -> str:
    reponse = envoyer_photo(client, fichier)
    assert reponse.status_code == 200
    url = reponse.json()["reponse"]["photo"]
    assert url, "photo absente de la réponse"
    return url


def test_ca003_3_photo_jpeg_envoyee_en_multipart_puis_relue(
    client_utilisateur, utilisateur, media_temporaire
):
    reponse = envoyer_photo(client_utilisateur, jpeg())

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["statut"] == "success" and corps["message"]
    url = corps["reponse"]["photo"]
    assert url and "photos_profil/" in url and url.endswith(".jpg")
    assert client_utilisateur.get(MOI).json()["reponse"]["photo"] == url
    utilisateur.refresh_from_db()
    assert (media_temporaire / utilisateur.photo.name).is_file()


def test_ca003_3_jpeg_d_environ_2_mo_accepte(client_utilisateur):
    cote = 1350  # bruit aléatoire (graine fixe) : JPEG d'un peu plus de 2 Mo
    image = Image.frombytes("RGB", (cote, cote), random.Random(0).randbytes(cote * cote * 3))
    tampon = BytesIO()
    image.save(tampon, format="JPEG", quality=95)
    assert tampon.tell() > 2_000_000
    fichier = SimpleUploadedFile("photo.jpg", tampon.getvalue(), content_type="image/jpeg")

    reponse = envoyer_photo(client_utilisateur, fichier)

    assert reponse.status_code == 200
    assert reponse.json()["reponse"]["photo"]


def test_fichier_texte_renomme_en_jpg_refuse(client_utilisateur, utilisateur):
    faux = SimpleUploadedFile("moi.jpg", b"pas une image", content_type="image/jpeg")

    reponse = envoyer_photo(client_utilisateur, faux)

    assert reponse.status_code == 400
    corps = reponse.json()
    assert corps["statut"] == "failed" and corps["message"]
    assert corps["reponse"]["code"] == "DONNEES_INVALIDES"
    assert corps["reponse"]["erreurs"]["photo"]
    utilisateur.refresh_from_db()
    assert not utilisateur.photo


def test_remplacer_la_photo_renvoie_la_nouvelle_url(client_utilisateur):
    ancienne = url_photo_envoyee(client_utilisateur, jpeg("avant.jpg"))

    reponse = envoyer_photo(client_utilisateur, jpeg("apres.jpg", couleur=(10, 90, 200)))

    assert reponse.status_code == 200
    nouvelle = reponse.json()["reponse"]["photo"]
    assert nouvelle != ancienne and "apres" in nouvelle
    assert client_utilisateur.get(MOI).json()["reponse"]["photo"] == nouvelle


def test_patch_sans_photo_conserve_la_photo(client_utilisateur):
    url = url_photo_envoyee(client_utilisateur, jpeg())

    reponse = client_utilisateur.patch(MOI, {"prenom": "Edem"}, format="json")

    assert reponse.json()["reponse"]["photo"] == url


@pytest.fixture
def trajet_avec_photo(client_de, conducteur):
    """Le conducteur envoie sa photo par l'API, puis publie un trajet."""
    url = url_photo_envoyee(client_de(conducteur), jpeg("kodjo.jpg"))
    return publier_trajet(conducteur), url


def test_ca003_3_photo_du_conducteur_dans_la_recherche(client_de, passager, trajet_avec_photo):
    trajet, url = trajet_avec_photo
    criteres = {
        "depart_lat": ADIDOGOME["lat"],
        "depart_lng": ADIDOGOME["lng"],
        "arrivee_lat": GRAND_MARCHE["lat"],
        "arrivee_lng": GRAND_MARCHE["lng"],
        "date_heure": trajet.depart_le.isoformat(),
    }

    reponse = client_de(passager).get("/api/v1/trajets/recherche/", criteres)

    assert reponse.status_code == 200
    (resultat,) = reponse.json()["reponse"]
    assert resultat["trajet"]["conducteur"]["photo"] == url


def test_ca003_3_photo_du_conducteur_dans_le_detail_du_trajet(
    client_de, passager, trajet_avec_photo
):
    trajet, url = trajet_avec_photo

    reponse = client_de(passager).get(f"/api/v1/trajets/{trajet.id}/")

    assert reponse.status_code == 200
    assert reponse.json()["reponse"]["conducteur"]["photo"] == url


def test_photo_du_conducteur_dans_son_profil_public(client_de, passager, trajet_avec_photo):
    trajet, url = trajet_avec_photo

    reponse = client_de(passager).get(f"/api/v1/utilisateurs/{trajet.conducteur_id}/")

    assert reponse.status_code == 200
    assert reponse.json()["reponse"]["photo"] == url


def test_conducteur_sans_photo_renvoie_null(client_de, passager, trajet):
    User.objects.filter(pk=trajet.conducteur_id).update(photo="")

    reponse = client_de(passager).get(f"/api/v1/trajets/{trajet.id}/")

    assert reponse.json()["reponse"]["conducteur"]["photo"] is None
