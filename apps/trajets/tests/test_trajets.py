from datetime import timedelta

import pytest
from django.utils import timezone

from apps.core.exceptions import Conflit, DonneesInvalides
from apps.reservations import services as reservations
from apps.trajets import services
from apps.trajets.models import StatutTrajet
from conftest import CARREFOUR_ADIDOGOME, GRAND_MARCHE, demander, publier_trajet

pytestmark = pytest.mark.django_db


def charge_publication(trajet_vehicule_id, **modifs):
    return {
        "vehicule_id": str(trajet_vehicule_id),
        "depart_lat": 6.1745,
        "depart_lng": 1.1690,
        "depart_libelle": "Adidogomé",
        "arrivee_lat": GRAND_MARCHE["lat"],
        "arrivee_lng": GRAND_MARCHE["lng"],
        "arrivee_libelle": "Grand Marché",
        "depart_le": (timezone.now() + timedelta(hours=1)).isoformat(),
        "places": 2,
        "points": [CARREFOUR_ADIDOGOME],
        **modifs,
    }


def test_publier_fixe_le_prix_et_la_distance(conducteur):
    trajet = publier_trajet(conducteur)

    assert trajet.statut == StatutTrajet.PUBLIE
    assert trajet.places_restantes == 3
    assert trajet.prix_place == 300  # paramètre prix_simulation
    assert trajet.distance_km > 0
    assert trajet.points.count() == 1


def test_publier_via_api(client_de, conducteur):
    vehicule = conducteur.vehicules.first()

    reponse = client_de(conducteur).post(
        "/api/v1/trajets/", charge_publication(vehicule.id), format="json"
    )

    assert reponse.status_code == 201
    assert reponse.json()["reponse"]["prix_place"] == 300


def test_publication_refusee_sans_kyc_conducteur(client_de, passager):
    reponse = client_de(passager).post(
        "/api/v1/trajets/",
        charge_publication("00000000-0000-0000-0000-000000000000"),
        format="json",
    )

    assert reponse.status_code == 403
    assert reponse.json()["reponse"]["code"] == "CONDUCTEUR_NON_HABILITE"


@pytest.mark.parametrize(
    "modifs",
    [{"places": 5}, {"depart_dans": timedelta(hours=-1)}],
)
def test_publication_invalide(conducteur, modifs):
    with pytest.raises(DonneesInvalides):
        publier_trajet(
            conducteur,
            depart_dans=modifs.get("depart_dans", timedelta(hours=1)),
            places=modifs.get("places", 2),
        )


def test_trop_de_points_refuse(client_de, conducteur):
    charge = charge_publication(conducteur.vehicules.first().id, points=[CARREFOUR_ADIDOGOME] * 4)

    assert client_de(conducteur).post("/api/v1/trajets/", charge, format="json").status_code == 400


def rechercher(utilisateur, date_heure, arrivee=GRAND_MARCHE):
    return services.rechercher(
        utilisateur, 6.1748, 1.1695, arrivee["lat"] + 0.002, arrivee["lng"], date_heure
    )


def test_recherche_trouve_le_trajet_correspondant(passager, trajet):
    resultats = rechercher(passager, trajet.depart_le + timedelta(minutes=10))

    assert [r.trajet.id for r in resultats] == [trajet.id]
    assert resultats[0].distance_marche_km < 1
    assert resultats[0].ecart_minutes == 10


def test_recherche_exclut_hors_fenetre_hors_rayon_et_propres_trajets(passager, conducteur, trajet):
    assert rechercher(passager, trajet.depart_le + timedelta(minutes=30)) == []
    assert rechercher(passager, trajet.depart_le, arrivee={"lat": 6.20, "lng": 1.30}) == []
    assert rechercher(conducteur, trajet.depart_le) == []


def test_recherche_exclut_les_trajets_complets(passager, conducteur):
    trajet = publier_trajet(conducteur, places=1)
    reservations.accepter(conducteur, demander(passager, trajet).id)

    assert rechercher(passager, trajet.depart_le) == []


def test_recherche_via_api_triee_par_heure(client_de, passager, conducteur):
    tard = publier_trajet(conducteur, depart_dans=timedelta(hours=2, minutes=10))
    tot = publier_trajet(conducteur, depart_dans=timedelta(hours=2))

    reponse = client_de(passager).get(
        "/api/v1/trajets/recherche/",
        {
            "depart_lat": 6.1748,
            "depart_lng": 1.1695,
            "arrivee_lat": GRAND_MARCHE["lat"],
            "arrivee_lng": GRAND_MARCHE["lng"],
            "date_heure": tot.depart_le.isoformat(),
        },
    )

    ids = [r["trajet"]["id"] for r in reponse.json()["reponse"]]
    assert ids == [str(tot.id), str(tard.id)]
    assert reponse.json()["reponse"][0]["trajet"]["conducteur"]["confiance"]["fiabilite_pct"] == 100


def test_annuler_un_trajet_annule_les_reservations(conducteur, passager, trajet):
    reservation = reservations.accepter(conducteur, demander(passager, trajet).id)

    trajet = services.annuler(conducteur, trajet.id)

    reservation.refresh_from_db()
    assert trajet.statut == StatutTrajet.ANNULE
    assert reservation.statut == "annulee"
    with pytest.raises(Conflit):
        services.annuler(conducteur, trajet.id)


def test_terminer_exige_que_les_passagers_acceptes_soient_traites(conducteur, reservation_acceptee):
    with pytest.raises(Conflit):
        services.terminer(conducteur, reservation_acceptee.trajet_id)


def test_position_et_mes_trajets(client_de, conducteur, trajet):
    client = client_de(conducteur)

    reponse = client.post(f"/api/v1/trajets/{trajet.id}/position/", {"lat": 6.17, "lng": 1.18})
    assert reponse.json()["reponse"]["position_le"] is not None
    mes_trajets = client.get("/api/v1/trajets/mes-trajets/").json()["reponse"]
    assert mes_trajets["count"] == 1


def test_trajet_d_un_autre_conducteur_introuvable(client_de, passager, trajet):
    reponse = client_de(passager).post(f"/api/v1/trajets/{trajet.id}/annuler/")

    assert reponse.status_code == 404


def test_detail_public_et_liste_admin(client_de, client_admin, passager, trajet):
    detail = client_de(passager).get(f"/api/v1/trajets/{trajet.id}/").json()["reponse"]
    assert detail["vehicule"]["immatriculation"]
    assert "email" not in detail["conducteur"]
    assert client_admin.get("/api/v1/admin/trajets/").json()["reponse"]["count"] == 1
