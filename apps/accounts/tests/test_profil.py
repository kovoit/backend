"""Écran Profil : KYC non bloquant à l'inscription, badge orange, accès et bascule de mode."""

import pytest

from apps.accounts.services import etat_profil, suspendre
from apps.kyc.models import KycDossier
from apps.kyc.tests.factories import verifier_kyc
from apps.vehicules.tests.factories import VehiculeFactory

pytestmark = pytest.mark.django_db


def codes(etat: dict) -> set[str]:
    return {alerte["code"] for alerte in etat["alertes"]}


def test_nouvel_inscrit_peut_chercher_mais_ni_reserver_ni_publier(utilisateur):
    etat = etat_profil(utilisateur)

    assert etat["badge_kyc"] is True
    assert etat["acces"] == {"peut_rechercher": True, "peut_reserver": False, "peut_publier": False}
    assert "KYC_PASSAGER_NON_VERIFIE" in codes(etat)


def test_kyc_en_attente_pas_de_badge_mais_toujours_bloque(utilisateur):
    KycDossier.objects.create(utilisateur=utilisateur, type="passager", statut="en_attente")

    etat = etat_profil(utilisateur)

    assert etat["badge_kyc"] is False
    assert etat["acces"]["peut_reserver"] is False
    assert "KYC_PASSAGER_EN_ATTENTE" in codes(etat)


def test_kyc_rejete_affiche_le_badge(utilisateur):
    verifier_kyc(utilisateur, "passager")
    KycDossier.objects.create(utilisateur=utilisateur, type="conducteur", statut="rejete")

    etat = etat_profil(utilisateur)

    assert etat["badge_kyc"] is True
    assert "KYC_CONDUCTEUR_REJETE" in codes(etat)


def test_conducteur_complet(conducteur):
    verifier_kyc(conducteur, "passager")

    etat = etat_profil(conducteur)

    assert etat["badge_kyc"] is False
    assert etat["alertes"] == []
    assert etat["acces"]["peut_publier"] is True
    assert etat["mode_conducteur"] == {
        "disponible": True,
        "kyc_conducteur_verifie": True,
        "vehicule_declare": True,
    }


def test_suspension_coupe_les_acces(passager):
    suspendre(passager, 7)

    etat = etat_profil(passager)

    assert etat["acces"]["peut_reserver"] is False
    assert "COMPTE_SUSPENDU" in codes(etat)


def test_profil_incomplet(utilisateur):
    utilisateur.telephone = ""

    assert "PROFIL_INCOMPLET" in codes(etat_profil(utilisateur))


def test_api_moi_expose_l_etat(client_utilisateur):
    etat = client_utilisateur.get("/api/v1/moi/").json()["reponse"]["etat"]

    assert etat["badge_kyc"] is True
    assert etat["alertes"][0]["action_requise"] is True


@pytest.mark.parametrize(
    ("kyc_conducteur", "vehicule", "code_attendu"),
    [(False, False, "KYC_CONDUCTEUR_REQUIS"), (True, False, "VEHICULE_REQUIS")],
)
def test_passer_en_mode_conducteur_indique_ce_qui_manque(
    client_utilisateur, utilisateur, kyc_conducteur, vehicule, code_attendu
):
    if kyc_conducteur:
        verifier_kyc(utilisateur, "conducteur")
    if vehicule:
        VehiculeFactory(proprietaire=utilisateur)

    reponse = client_utilisateur.patch(
        "/api/v1/moi/mode/", {"mode_actif": "conducteur"}, format="json"
    )

    assert reponse.status_code == 403
    assert reponse.json()["reponse"]["code"] == code_attendu


def test_retour_en_mode_passager_toujours_possible(client_de, conducteur):
    client = client_de(conducteur)
    client.patch("/api/v1/moi/mode/", {"mode_actif": "conducteur"}, format="json")

    reponse = client.patch("/api/v1/moi/mode/", {"mode_actif": "passager"}, format="json")

    assert reponse.json()["reponse"]["mode_actif"] == "passager"
