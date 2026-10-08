"""Toutes les réponses, succès comme erreurs, respectent { statut, message, reponse }."""

import pytest
from rest_framework import status

from apps.core.api.exceptions import gestionnaire_exceptions
from apps.core.exceptions import Conflit, TransitionInvalide


def verifier_enveloppe(donnees: dict, statut: str) -> None:
    assert set(donnees) == {"statut", "message", "reponse"}
    assert donnees["statut"] == statut
    assert isinstance(donnees["message"], str) and donnees["message"]


def test_sante_renvoie_une_enveloppe_success(api_client):
    reponse = api_client.get("/api/v1/sante/")

    assert reponse.status_code == status.HTTP_200_OK
    verifier_enveloppe(reponse.json(), "success")
    assert reponse.json()["reponse"] == {"version": "1.0.0"}


@pytest.mark.django_db
def test_non_authentifie_renvoie_401_failed(api_client):
    reponse = api_client.get("/api/v1/admin/parametres/")

    assert reponse.status_code == status.HTTP_401_UNAUTHORIZED
    verifier_enveloppe(reponse.json(), "failed")
    assert reponse.json()["reponse"] == {"code": "NON_AUTHENTIFIE", "erreurs": None}


def test_acces_refuse_renvoie_403_failed(client_utilisateur):
    reponse = client_utilisateur.get("/api/v1/admin/parametres/")

    assert reponse.status_code == status.HTTP_403_FORBIDDEN
    verifier_enveloppe(reponse.json(), "failed")
    assert reponse.json()["reponse"]["code"] == "ACCES_REFUSE"


def test_donnees_invalides_renvoie_le_detail_par_champ(client_admin):
    reponse = client_admin.patch("/api/v1/admin/parametres/prix_simulation/", {}, format="json")

    assert reponse.status_code == status.HTTP_400_BAD_REQUEST
    verifier_enveloppe(reponse.json(), "failed")
    assert reponse.json()["reponse"]["code"] == "DONNEES_INVALIDES"
    assert "valeur" in reponse.json()["reponse"]["erreurs"]


def test_methode_non_autorisee_renvoie_405_failed(api_client):
    reponse = api_client.post("/api/v1/sante/")

    assert reponse.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert reponse.json()["reponse"]["code"] == "METHODE_NON_AUTORISEE"


def test_url_inconnue_renvoie_404_failed(client):
    reponse = client.get("/n-existe-pas/")

    assert reponse.status_code == status.HTTP_404_NOT_FOUND
    verifier_enveloppe(reponse.json(), "failed")
    assert reponse.json()["reponse"]["code"] == "RESSOURCE_INTROUVABLE"


def test_erreur_metier_convertie_avec_son_code_et_son_statut():
    reponse = gestionnaire_exceptions(TransitionInvalide(), {})

    assert reponse.status_code == status.HTTP_409_CONFLICT
    verifier_enveloppe(reponse.data, "failed")
    assert reponse.data["reponse"]["code"] == "TRANSITION_INVALIDE"


def test_erreur_metier_message_personnalise():
    reponse = gestionnaire_exceptions(Conflit("Plus aucune place.", code="PLUS_DE_PLACE"), {})

    assert reponse.data["message"] == "Plus aucune place."
    assert reponse.data["reponse"]["code"] == "PLUS_DE_PLACE"


def test_erreur_inattendue_renvoie_500_sans_detail_interne():
    reponse = gestionnaire_exceptions(RuntimeError("secret interne"), {})

    assert reponse.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    verifier_enveloppe(reponse.data, "failed")
    assert reponse.data["reponse"]["code"] == "ERREUR_INTERNE"
    assert "secret" not in reponse.data["message"]


def test_schema_openapi_documente_l_enveloppe(api_client):
    reponse = api_client.get("/api/schema/", {"format": "json"})

    assert reponse.status_code == status.HTTP_200_OK
    operation = reponse.json()["paths"]["/api/v1/sante/"]["get"]
    schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert set(schema["properties"]) == {"statut", "message", "reponse"}
    assert "default" in operation["responses"]


def test_racine_redirige_vers_la_documentation(client):
    reponse = client.get("/")

    assert reponse.status_code == status.HTTP_302_FOUND
    assert reponse.url == "/api/docs/"


def test_url_d_api_inconnue_renvoie_du_json_meme_en_debug(client, settings):
    settings.DEBUG = True

    reponse = client.get("/api/v1/n-existe-pas/")

    assert reponse.status_code == status.HTTP_404_NOT_FOUND
    verifier_enveloppe(reponse.json(), "failed")
    assert reponse.json()["reponse"]["code"] == "RESSOURCE_INTROUVABLE"


@pytest.mark.django_db
def test_jeton_invalide_renvoie_un_message_en_francais(api_client):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer faux.jeton.jwt")

    reponse = api_client.get("/api/v1/admin/parametres/")

    assert reponse.status_code == status.HTTP_401_UNAUTHORIZED
    assert reponse.json()["message"] == "Session invalide ou expirée. Reconnectez-vous."


def test_json_malforme_renvoie_un_message_lisible(client_admin):
    reponse = client_admin.generic(
        "PATCH",
        "/api/v1/admin/parametres/prix_simulation/",
        "{pas du json",
        content_type="application/json",
    )

    assert reponse.status_code == status.HTTP_400_BAD_REQUEST
    assert reponse.json()["reponse"]["code"] == "REQUETE_MALFORMEE"
    assert reponse.json()["message"] == "Le corps de la requête n'est pas un JSON valide."
