"""Page publique « Suivre le trajet » (HTML) ouverte par le proche."""

import pytest
from django.utils import timezone

from apps.partage import services as partage
from apps.reservations import services as reservations
from apps.trajets.models import Trajet

pytestmark = pytest.mark.django_db


@pytest.fixture
def lien(passager, reservation_acceptee):
    return partage.creer_lien(passager, reservation_acceptee.id)


def test_page_lisible_sans_coordonnees_privees(api_client, lien, conducteur):
    reponse = api_client.get(f"/suivi/{lien.jeton}/")

    page = reponse.content.decode()
    assert reponse.status_code == 200
    assert reponse["Content-Type"].startswith("text/html")
    assert "Kodjo" in page and "TG" in page
    assert "Pas encore partagée par le conducteur" in page
    assert conducteur.email not in page and conducteur.telephone not in page
    assert '<meta http-equiv="refresh" content="30">' in page


def test_le_jeton_ne_fuit_pas(api_client, lien):
    reponse = api_client.get(f"/suivi/{lien.jeton}/")

    assert reponse["Referrer-Policy"] == "no-referrer"
    assert "noindex" in reponse["X-Robots-Tag"]
    assert "no-store" in reponse["Cache-Control"] or "no-cache" in reponse["Cache-Control"]


def test_position_du_conducteur_affichee(api_client, lien):
    Trajet.objects.filter(pk=lien.reservation.trajet_id).update(
        position_lat=6.17234, position_lng=1.21456, position_le=timezone.now()
    )

    page = api_client.get(f"/suivi/{lien.jeton}/").content.decode()

    assert "Voir la position sur la carte" in page
    assert "mlat=6.17234&amp;mlon=1.21456" in page
    assert 'rel="noreferrer noopener"' in page


def test_lien_expire_ou_inconnu(api_client, passager, lien):
    assert api_client.get("/suivi/jeton-inconnu/").status_code == 404

    reservations.annuler(passager, lien.reservation_id)
    reponse = api_client.get(f"/suivi/{lien.jeton}/")
    assert reponse.status_code == 404
    assert "plus valable" in reponse.content.decode()
