"""Scénarios de bout en bout : une action mobile ou web produit un événement fiable côté serveur."""

import json

import pytest

from apps.audit.models import Canal, Categorie, Resultat
from apps.audit.tests.aides import client_mobile, client_web_admin, evenements, un_evenement
from apps.kyc.models import KycDossier, StatutKyc
from conftest import CARREFOUR_ADIDOGOME, GRAND_MARCHE

pytestmark = pytest.mark.django_db


def _demande(trajet):
    return {
        "trajet_id": str(trajet.id),
        "point_id": str(trajet.points.first().id),
        "arrivee_lat": GRAND_MARCHE["lat"] + 0.001,
        "arrivee_lng": GRAND_MARCHE["lng"],
    }


def test_reservation_depuis_le_mobile(api_client, passager, trajet, client_de, admin):
    """Scénario 1 : réservation mobile → événement persisté → visible par l'administration."""
    mobile, _ = client_mobile(api_client, passager.email)

    reponse = mobile.post("/api/v1/reservations/", _demande(trajet), format="json")

    assert reponse.status_code == 201
    evenement = un_evenement("reservation.demander")
    assert evenement.canal == Canal.MOBILE
    assert evenement.acteur_id == passager.id
    assert evenement.acteur_role == "passager"
    assert evenement.resultat == Resultat.SUCCES
    assert evenement.ressource_id == reponse.json()["reponse"]["id"]
    assert evenement.request_id == reponse["X-Request-ID"]
    liste = client_de(admin).get(
        "/api/v1/admin/audit/evenements/", {"action": "reservation.demander"}
    )
    assert liste.json()["reponse"]["results"][0]["id"] == str(evenement.id)


def test_connexion_mobile_cree_le_compte_et_la_session(api_client):
    client_mobile(api_client, "nouveau@exemple.tg")

    creation = un_evenement("compte.creer")
    connexion = un_evenement("session.connecter")
    assert creation.canal == connexion.canal == Canal.MOBILE
    assert creation.acteur_id == connexion.acteur_id is not None


def test_publication_avec_le_bon_acteur_et_le_bon_canal(api_client, conducteur):
    """Scénario 2 : les conducteurs publient depuis le mobile (pas d'espace web conducteur)."""
    mobile, _ = client_mobile(api_client, conducteur.email)
    trajet = {
        "vehicule_id": str(conducteur.vehicules.first().id),
        "depart_lat": 6.1745,
        "depart_lng": 1.1690,
        "depart_libelle": "Adidogomé",
        "arrivee_lat": GRAND_MARCHE["lat"],
        "arrivee_lng": GRAND_MARCHE["lng"],
        "arrivee_libelle": "Grand Marché",
        "depart_le": "2099-01-01T07:30:00Z",
        "places": 2,
        "points": [CARREFOUR_ADIDOGOME],
    }

    assert mobile.post("/api/v1/trajets/", trajet, format="json").status_code == 201
    evenement = un_evenement("trajet.publier")
    assert (evenement.canal, evenement.acteur_id, evenement.acteur_role) == (
        Canal.MOBILE,
        conducteur.id,
        "conducteur",
    )


def test_validation_kyc_depuis_le_back_office(admin, passager):
    """Scénario 3 : action administrative avec acteur, ressource, action et résultat."""
    dossier = KycDossier.objects.create(
        utilisateur=passager, type="conducteur", statut="en_attente"
    )
    web, _ = client_web_admin(admin)

    assert web.post(f"/api/v1/admin/kyc/{dossier.id}/valider/").status_code == 200
    evenement = un_evenement("kyc.valider")
    assert evenement.canal == Canal.WEB
    assert evenement.categorie == Categorie.ADMIN
    assert evenement.acteur_id == admin.id
    assert evenement.acteur_role == "admin"
    assert (evenement.ressource_type, evenement.ressource_id) == ("dossier_kyc", str(dossier.id))
    assert evenement.changements == {"statut": [StatutKyc.EN_ATTENTE, StatutKyc.VERIFIE]}


def test_echec_metier_journalise_comme_refus(api_client, passager, trajet):
    """Scénario 6 : un refus ne doit jamais apparaître comme une réservation réussie."""
    mobile, _ = client_mobile(api_client, passager.email)
    assert mobile.post("/api/v1/reservations/", _demande(trajet), format="json").status_code == 201

    reponse = mobile.post("/api/v1/reservations/", _demande(trajet), format="json")

    assert reponse.status_code == 409
    succes = evenements("reservation.demander", resultat=Resultat.SUCCES)
    refus = un_evenement("reservation.demander", resultat=Resultat.REFUS)
    assert len(succes) == 1
    assert refus.code_motif == "DEJA_RESERVE"
    assert refus.canal == Canal.MOBILE
    assert refus.acteur_id == passager.id


def test_permission_metier_refusee(api_client, conducteur, trajet):
    """Permission métier (KYC passager manquant) : refus de l'action tentée, pas une alerte."""
    mobile, _ = client_mobile(api_client, conducteur.email)

    assert mobile.post("/api/v1/reservations/", _demande(trajet), format="json").status_code == 403
    refus = un_evenement("reservation.demander")
    assert (refus.resultat, refus.categorie) == (Resultat.REFUS, Categorie.METIER)
    assert refus.code_motif == "KYC_PASSAGER_REQUIS"


def test_le_canal_ne_vient_pas_du_client(passager, trajet, client_de):
    """Un en-tête ou un champ « source: mobile » envoyé par le client est ignoré."""
    client = client_de(passager)  # authentifié sans jeton émis par une connexion Kovoit

    client.post(
        "/api/v1/reservations/",
        {**_demande(trajet), "source": "mobile", "canal": "web"},
        format="json",
        HTTP_X_CANAL="web",
    )

    assert un_evenement("reservation.demander").canal == Canal.API


def test_aucun_secret_dans_le_journal(api_client, passager, admin, trajet):
    """Scénario 7 : ni code OTP, ni mot de passe, ni jeton, ni code de départ."""
    from apps.reservations import services as reservations
    from apps.reservations.code_depart import calculer_code

    mobile, access_mobile = client_mobile(api_client, passager.email)
    _, access_web = client_web_admin(admin, "Secret-Tres-Long-2026")
    reponse = mobile.post("/api/v1/reservations/", _demande(trajet), format="json")
    reservation = reservations.accepter(trajet.conducteur, reponse.json()["reponse"]["id"])
    code = calculer_code(reservation)

    journal = json.dumps([e.__dict__ for e in evenements()], default=str)
    for secret in (access_mobile, access_web, "Secret-Tres-Long-2026", f'"{code}"'):
        assert secret not in journal
    assert "code_hash" not in journal and "jeton" not in journal
