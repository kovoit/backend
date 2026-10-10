import pytest
from django.core.management import call_command
from rest_framework import status

from apps.parametres import services
from apps.parametres.defauts import PARAMETRES_PAR_DEFAUT

URL_LISTE = "/api/v1/admin/parametres/"


def url_detail(cle: str) -> str:
    return f"{URL_LISTE}{cle}/"


@pytest.fixture
def parametres_initialises(db):
    services.initialiser_parametres()


def test_admin_liste_les_parametres(client_admin, parametres_initialises):
    reponse = client_admin.get(URL_LISTE)

    assert reponse.status_code == status.HTTP_200_OK
    corps = reponse.json()
    assert corps["statut"] == "success"
    assert len(corps["reponse"]) == len(PARAMETRES_PAR_DEFAUT)
    prix = next(p for p in corps["reponse"] if p["cle"] == "prix_simulation")
    assert prix["valeur"] == 300
    assert prix["type_valeur"] == "entier"


def test_admin_modifie_un_parametre(client_admin, admin, parametres_initialises):
    reponse = client_admin.patch(url_detail("rayon_depart_km"), {"valeur": 2}, format="json")

    assert reponse.status_code == status.HTTP_200_OK
    corps = reponse.json()
    assert corps == {
        "statut": "success",
        "message": "Paramètre modifié.",
        "reponse": corps["reponse"],
    }
    assert corps["reponse"]["valeur"] == 2
    assert corps["reponse"]["modifie_par"] == {
        "id": str(admin.id),
        "nom": admin.nom,
        "prenom": admin.prenom,
    }
    assert services.get_param("rayon_depart_km") == 2


def test_valeur_invalide_renvoie_400(client_admin, parametres_initialises):
    reponse = client_admin.patch(url_detail("prix_simulation"), {"valeur": -5}, format="json")

    assert reponse.status_code == status.HTTP_400_BAD_REQUEST
    assert reponse.json()["statut"] == "failed"
    assert reponse.json()["reponse"]["code"] == "VALEUR_PARAMETRE_INVALIDE"


def test_cle_inconnue_renvoie_404(client_admin, parametres_initialises):
    reponse = client_admin.patch(url_detail("inexistant"), {"valeur": 1}, format="json")

    assert reponse.status_code == status.HTTP_404_NOT_FOUND
    assert reponse.json()["reponse"]["code"] == "PARAMETRE_INTROUVABLE"


def test_utilisateur_non_admin_ne_peut_pas_modifier(client_utilisateur, parametres_initialises):
    reponse = client_utilisateur.patch(url_detail("prix_simulation"), {"valeur": 1}, format="json")

    assert reponse.status_code == status.HTTP_403_FORBIDDEN
    assert services.get_param("prix_simulation") == 300


@pytest.mark.django_db
def test_commande_seed_parametres(capsys):
    call_command("seed_parametres")
    call_command("seed_parametres")

    sortie = capsys.readouterr().out
    assert f"{len(PARAMETRES_PAR_DEFAUT)} paramètre(s) créé(s)." in sortie
    assert "0 paramètre(s) créé(s)." in sortie
