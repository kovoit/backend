import pytest

from apps.parametres import services
from apps.parametres.defauts import GROUPES, PARAMETRES_PAR_DEFAUT
from apps.parametres.models import Parametre

pytestmark = pytest.mark.django_db

URL = "/api/v1/admin/parametres/"
STRICTEMENT_POSITIFS = [cle for cle, d in PARAMETRES_PAR_DEFAUT.items() if d.minimum > 0]


@pytest.fixture(autouse=True)
def parametres_initialises():
    services.initialiser_parametres()


def test_tous_les_defauts_respectent_leur_minimum():
    for cle, defaut in PARAMETRES_PAR_DEFAUT.items():
        services.valider_valeur(cle, defaut.valeur)  # ne lève rien
        assert defaut.groupe in GROUPES, cle


@pytest.mark.parametrize("cle", STRICTEMENT_POSITIFS)
def test_zero_refuse_quand_il_casserait_une_regle(client_admin, cle):
    reponse = client_admin.patch(f"{URL}{cle}/", {"valeur": 0}, format="json")

    assert reponse.status_code == 400
    assert reponse.json()["reponse"]["code"] == "VALEUR_PARAMETRE_INVALIDE"
    assert "valeur" in reponse.json()["reponse"]["erreurs"]


def test_duree_de_suspension_nulle_refusee():
    """0 jour serait lu comme « sans durée » : suspension automatique sans fin."""
    with pytest.raises(services.ValeurParametreInvalide):
        services.modifier_param("duree_suspension_j", 0)
    assert services.get_param("duree_suspension_j") == 7


def test_zero_accepte_quand_il_a_un_sens(client_admin):
    # Pas de frais de service, pas de délai d'annulation tardive : choix métier possibles
    for cle in ("frais_service", "delai_annulation_min"):
        assert client_admin.patch(f"{URL}{cle}/", {"valeur": 0}, format="json").status_code == 200


def test_rayon_sous_le_minimum_decimal(client_admin):
    reponse = client_admin.patch(f"{URL}rayon_depart_km/", {"valeur": 0.05}, format="json")

    assert reponse.status_code == 400
    assert reponse.json()["reponse"]["erreurs"]["valeur"] == ["Minimum : 0,1 km."]


def test_liste_dans_l_ordre_du_registre_avec_metadonnees(client_admin):
    Parametre.objects.create(cle="ancien_parametre", valeur=1)  # retiré du registre : ignoré

    parametres = client_admin.get(URL).json()["reponse"]

    assert [p["cle"] for p in parametres] == list(PARAMETRES_PAR_DEFAUT)
    rayon = next(p for p in parametres if p["cle"] == "rayon_depart_km")
    assert rayon["groupe"] == {"code": "correspondance", "libelle": "Correspondance des trajets"}
    assert rayon["unite"] == "km"
    assert rayon["minimum"] == 0.1
    assert rayon["type_valeur"] == "decimal"
    assert rayon["modifie_par"] is None
