"""Validité du lien public selon le statut de la réservation (D-05, F-001).

Le lien est créé en `acceptee`, puis la réservation suit son parcours réel. Il n'est lisible
qu'en `acceptee` et `en_cours` ; ensuite l'API répond 404 `failed` et la page affiche
« Ce lien n'est plus valable » (D-50), sans aucune donnée personnelle.
"""

import pytest

from apps.partage.tests.parcours import (
    POSITION,
    POSITION_DANS_LA_PAGE,
    STATUTS_INVALIDES,
    STATUTS_VALIDES,
    TITRE_LIEN_INVALIDE,
    amener_au_statut,
    creer_lien_par_api,
    terminer_trajet,
    verifier_page_lien_invalide,
)
from apps.reservations.models import StatutReservation as S

pytestmark = pytest.mark.django_db


@pytest.fixture
def jeton(client_de, passager, conducteur, reservation_acceptee):
    """Lien créé par le passager, puis position transmise par le conducteur."""
    jeton = creer_lien_par_api(client_de(passager), reservation_acceptee.id)
    reponse = client_de(conducteur).post(
        f"/api/v1/trajets/{reservation_acceptee.trajet_id}/position/", POSITION
    )
    assert reponse.status_code == 200
    return jeton


def _verifier_enveloppe_404(reponse):
    corps = reponse.json()
    assert reponse.status_code == 404
    assert set(corps) == {"statut", "message", "reponse"}
    assert corps["statut"] == "failed"
    assert corps["message"].strip()
    assert corps["reponse"]["code"] == "RESSOURCE_INTROUVABLE"


@pytest.mark.parametrize("statut", STATUTS_VALIDES)
def test_ca001_1_api_publique_lisible_en_acceptee_et_en_cours(
    api_client, jeton, passager, conducteur, reservation_acceptee, statut
):
    amener_au_statut(reservation_acceptee, statut, passager, conducteur)
    vehicule = conducteur.vehicules.first()

    reponse = api_client.get(f"/api/v1/partage/{jeton}/")

    corps = reponse.json()
    assert reponse.status_code == 200
    assert set(corps) == {"statut", "message", "reponse"}
    assert corps["statut"] == "success" and corps["message"].strip()
    assert corps["reponse"]["statut"] == statut
    assert corps["reponse"]["conducteur_prenom"] == "Kodjo"
    for detail in (vehicule.modele, vehicule.couleur, vehicule.immatriculation):
        assert detail in corps["reponse"]["vehicule"]
    assert corps["reponse"]["position_lat"] == POSITION["lat"]
    assert corps["reponse"]["position_lng"] == POSITION["lng"]


@pytest.mark.parametrize("statut", STATUTS_VALIDES)
def test_ca001_1_page_affiche_trajet_conducteur_vehicule_et_position(
    api_client, jeton, passager, conducteur, reservation_acceptee, statut
):
    amener_au_statut(reservation_acceptee, statut, passager, conducteur)
    vehicule = conducteur.vehicules.first()

    reponse = api_client.get(f"/suivi/{jeton}/")

    page = reponse.content.decode()
    assert reponse.status_code == 200
    assert "Adidogomé → Grand Marché" in page
    assert "Kodjo" in page
    assert vehicule.immatriculation in page and vehicule.couleur in page
    assert vehicule.modele in page
    assert POSITION_DANS_LA_PAGE in page
    assert TITRE_LIEN_INVALIDE not in page


@pytest.mark.parametrize("statut", STATUTS_INVALIDES)
def test_ca001_3_api_publique_404_failed_hors_acceptee_et_en_cours(
    api_client, jeton, passager, conducteur, reservation_acceptee, statut
):
    amener_au_statut(reservation_acceptee, statut, passager, conducteur)

    _verifier_enveloppe_404(api_client.get(f"/api/v1/partage/{jeton}/"))


@pytest.mark.parametrize("statut", STATUTS_INVALIDES)
def test_ca001_3_page_404_lien_plus_valable_sans_donnee_personnelle(
    api_client, jeton, passager, conducteur, reservation_acceptee, statut
):
    amener_au_statut(reservation_acceptee, statut, passager, conducteur)
    vehicule = conducteur.vehicules.first()

    reponse = api_client.get(f"/suivi/{jeton}/")

    page = reponse.content.decode()
    verifier_page_lien_invalide(reponse)
    for donnee in ("Kodjo", "Afi", vehicule.immatriculation, vehicule.marque, "Adidogomé"):
        assert donnee not in page
    for trace_de_position in ("mlat=", "6.1319", "1.2228", "Voir la position"):
        assert trace_de_position not in page
    # Pas de rafraîchissement automatique d'un lien mort
    assert 'http-equiv="refresh"' not in page


def test_ca001_3_jeton_inconnu_api_et_page_404(api_client):
    _verifier_enveloppe_404(api_client.get("/api/v1/partage/jeton-inconnu/"))

    verifier_page_lien_invalide(api_client.get("/suivi/jeton-inconnu/"))


def test_ca001_3_meme_lien_valable_en_route_puis_invalide_apres_arrivee(
    api_client, jeton, passager, conducteur, reservation_acceptee
):
    amener_au_statut(reservation_acceptee, S.EN_COURS, passager, conducteur)
    en_route = api_client.get(f"/suivi/{jeton}/")
    assert en_route.status_code == 200
    assert TITRE_LIEN_INVALIDE not in en_route.content.decode()

    terminer_trajet(conducteur, reservation_acceptee)

    reservation_acceptee.refresh_from_db()
    assert reservation_acceptee.statut == S.TERMINEE
    verifier_page_lien_invalide(api_client.get(f"/suivi/{jeton}/"))
    _verifier_enveloppe_404(api_client.get(f"/api/v1/partage/{jeton}/"))
