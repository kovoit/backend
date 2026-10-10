from datetime import timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from conftest import demander, publier_trajet

pytestmark = pytest.mark.django_db

URL = "/api/v1/admin/trajets/"


def test_liste_au_format_admin(client_admin, trajet):
    ligne = client_admin.get(URL).json()["reponse"]["results"][0]

    assert ligne["depart"] == {"lat": 6.1745, "lng": 1.169, "libelle": "Adidogomé"}
    assert ligne["arrivee"]["libelle"] == "Grand Marché"
    # Coordonnées du conducteur : visibles par l'admin uniquement
    assert ligne["conducteur"]["telephone"] == trajet.conducteur.telephone
    assert ligne["conducteur"]["email"] == trajet.conducteur.email
    assert isinstance(ligne["distance_km"], float)


def test_liste_plus_recents_d_abord(client_admin, conducteur):
    proche = publier_trajet(conducteur, depart_dans=timedelta(hours=2))
    lointain = publier_trajet(conducteur, depart_dans=timedelta(days=3))

    lignes = client_admin.get(URL).json()["reponse"]["results"]

    assert [ligne["id"] for ligne in lignes] == [str(lointain.id), str(proche.id)]


@pytest.mark.parametrize("terme", ["kodjo", "grand marché", "carrefour adidogomé"])
def test_recherche_conducteur_ou_lieu(client_admin, trajet, terme):
    resultats = client_admin.get(URL, {"recherche": terme}).json()["reponse"]

    # Un seul résultat même si plusieurs champs correspondent (pas de doublon)
    assert [ligne["id"] for ligne in resultats["results"]] == [str(trajet.id)]


def test_recherche_sans_resultat(client_admin, trajet):
    assert client_admin.get(URL, {"recherche": "Baguida"}).json()["reponse"]["count"] == 0


def test_filtre_par_jour_heure_de_lome(client_admin, conducteur):
    with freeze_time("2026-10-08 20:00"):
        soir = publier_trajet(conducteur, depart_dans=timedelta(hours=3, minutes=30))  # 23:30
        publier_trajet(conducteur, depart_dans=timedelta(hours=5))  # lendemain 01:00

    lignes = client_admin.get(URL, {"date": "2026-10-08"}).json()["reponse"]["results"]

    assert [ligne["id"] for ligne in lignes] == [str(soir.id)]


def test_filtres_invalides(client_admin):
    reponse = client_admin.get(URL, {"statut": "vole", "date": "hier"})

    assert reponse.status_code == 400
    assert set(reponse.json()["reponse"]["erreurs"]) == {"statut", "date"}


def test_detail_avec_points_vehicule_et_reservations(client_admin, trajet, passager):
    reservation = demander(passager, trajet)

    detail = client_admin.get(f"{URL}{trajet.id}/").json()["reponse"]

    assert detail["points"][0]["libelle"] == "Carrefour Adidogomé"
    assert detail["points"][0]["ordre"] == 1
    assert detail["vehicule"]["nb_places"] == 5
    assert len(detail["reservations"]) == 1
    ligne = detail["reservations"][0]
    assert ligne["id"] == str(reservation.id)
    assert ligne["passager"]["telephone"] == passager.telephone
    assert ligne["point_libelle"] == "Carrefour Adidogomé"
    assert ligne["trajet_id"] == str(trajet.id)


def test_detail_ne_montre_jamais_le_code_de_depart(client_admin, reservation_acceptee):
    corps = client_admin.get(f"{URL}{reservation_acceptee.trajet_id}/").content.decode()

    assert "code_depart" not in corps
    assert "essais_code" not in corps


def test_detail_introuvable(client_admin):
    assert client_admin.get(f"{URL}00000000-0000-0000-0000-000000000000/").status_code == 404


def test_reserve_aux_admins(client_utilisateur, trajet):
    assert client_utilisateur.get(URL).status_code == 403
    assert client_utilisateur.get(f"{URL}{trajet.id}/").status_code == 403


def test_trajet_passe_reste_consultable(client_admin, conducteur):
    with freeze_time(timezone.now() - timedelta(days=10)):
        ancien = publier_trajet(conducteur)

    assert client_admin.get(f"{URL}{ancien.id}/").status_code == 200
