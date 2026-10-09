"""Paiement à la réservation : portefeuille d'abord, complément par Flooz ou Mixx."""

import pytest

from apps.kyc.tests.factories import verifier_kyc
from apps.parametres.services import modifier_param
from apps.portefeuille import services as portefeuille
from apps.reservations import services
from conftest import GRAND_MARCHE, demander

pytestmark = pytest.mark.django_db


@pytest.fixture
def passager_sans_argent(utilisateur):
    """Passager KYC vérifié dont le portefeuille est vide."""
    verifier_kyc(utilisateur, "passager")
    return utilisateur


def corps_demande(trajet, **extra) -> dict:
    return {
        "trajet_id": str(trajet.id),
        "point_id": str(trajet.points.first().id),
        "arrivee_lat": GRAND_MARCHE["lat"],
        "arrivee_lng": GRAND_MARCHE["lng"],
        **extra,
    }


def test_solde_suffisant_aucun_complement(reservation):
    assert reservation.complement_paye == 0
    assert reservation.moyen_paiement == ""


def test_sans_solde_ni_moyen_indique_le_complement(passager_sans_argent, trajet):
    with pytest.raises(portefeuille.SoldeInsuffisant) as exc:
        demander(passager_sans_argent, trajet)

    assert exc.value.erreurs == {"complement_a_payer": 300, "moyens_paiement": ["flooz", "mixx"]}


def test_complement_total_paye_par_mixx(passager_sans_argent, trajet):
    reservation = services.demander_place(
        passager_sans_argent,
        trajet_id=trajet.id,
        point_id=trajet.points.first().id,
        arrivee_lat=GRAND_MARCHE["lat"],
        arrivee_lng=GRAND_MARCHE["lng"],
        moyen_paiement="mixx",
    )

    assert (reservation.moyen_paiement, reservation.complement_paye) == ("mixx", 300)
    solde = portefeuille.solde(passager_sans_argent)
    assert (solde.total, solde.bloque, solde.disponible) == (300, 300, 0)


def test_annulation_rend_le_complement_au_portefeuille(passager_sans_argent, trajet):
    reservation = services.demander_place(
        passager_sans_argent, **corps_demande(trajet, moyen_paiement="flooz")
    )

    services.annuler(passager_sans_argent, reservation.id)

    assert portefeuille.solde(passager_sans_argent).disponible == 300


def test_complement_partiel_via_api(client_de, passager_sans_argent, trajet):
    modifier_param("recharge_min", 100)
    portefeuille.recharger(passager_sans_argent, 100, "flooz")  # il manque 200 F
    client = client_de(passager_sans_argent)

    detail = client.get(f"/api/v1/trajets/{trajet.id}/").json()["reponse"]
    assert detail["paiement"]["solde_disponible"] == 100
    assert detail["paiement"]["complement_a_payer"] == 200

    refus = client.post("/api/v1/reservations/", corps_demande(trajet), format="json")
    assert refus.status_code == 409
    assert refus.json()["reponse"]["erreurs"]["complement_a_payer"] == 200

    reponse = client.post(
        "/api/v1/reservations/", corps_demande(trajet, moyen_paiement="flooz"), format="json"
    )
    assert reponse.status_code == 201
    assert reponse.json()["reponse"]["complement_paye"] == 200
    assert reponse.json()["reponse"]["moyen_paiement"] == "flooz"


def test_moyen_de_paiement_invalide(client_de, passager_sans_argent, trajet):
    reponse = client_de(passager_sans_argent).post(
        "/api/v1/reservations/", corps_demande(trajet, moyen_paiement="tmoney"), format="json"
    )

    assert reponse.status_code == 400
    assert "moyen_paiement" in reponse.json()["reponse"]["erreurs"]
