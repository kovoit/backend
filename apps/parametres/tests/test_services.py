import pytest

from apps.parametres import services
from apps.parametres.defauts import PARAMETRES_PAR_DEFAUT
from apps.parametres.models import Parametre
from apps.parametres.services import ParametreIntrouvable, ValeurParametreInvalide

pytestmark = pytest.mark.django_db


@pytest.fixture
def parametres_initialises():
    services.initialiser_parametres()


def test_initialiser_cree_tous_les_parametres_une_seule_fois():
    assert services.initialiser_parametres() == len(PARAMETRES_PAR_DEFAUT)
    assert services.initialiser_parametres() == 0
    assert Parametre.objects.count() == len(PARAMETRES_PAR_DEFAUT)


def test_initialiser_n_ecrase_pas_une_valeur_modifiee(parametres_initialises):
    services.modifier_param("prix_simulation", 400)

    services.initialiser_parametres()

    assert Parametre.objects.get(cle="prix_simulation").valeur == 400


def test_get_param_lit_la_valeur_en_base(parametres_initialises):
    assert services.get_param("rayon_depart_km") == 1.5
    assert services.get_param("delai_annulation_min") == 30


def test_get_param_reflete_une_modification_malgre_le_cache(parametres_initialises):
    assert services.get_param("prix_simulation") == 300

    services.modifier_param("prix_simulation", 350)

    assert services.get_param("prix_simulation") == 350


def test_get_param_absent_en_base_renvoie_la_valeur_de_depart():
    assert services.get_param("fenetre_horaire_min") == 15


def test_get_param_inconnu_leve_une_erreur():
    with pytest.raises(ParametreIntrouvable):
        services.get_param("cle_inexistante")


def test_modifier_enregistre_l_auteur(parametres_initialises, admin):
    parametre = services.modifier_param("frais_service", 50, par=admin)

    assert parametre.valeur == 50
    assert parametre.modifie_par == admin


def test_modifier_cree_le_parametre_s_il_n_est_pas_encore_en_base():
    services.modifier_param("seuil_incidents", 4)

    assert Parametre.objects.get(cle="seuil_incidents").valeur == 4


@pytest.mark.parametrize(
    ("cle", "valeur"),
    [
        ("prix_simulation", 300.5),  # entier attendu
        ("prix_simulation", -10),  # négatif
        ("prix_simulation", "300"),  # texte
        ("prix_simulation", True),  # booléen
        ("rayon_depart_km", None),
    ],
)
def test_modifier_refuse_une_valeur_invalide(parametres_initialises, cle, valeur):
    with pytest.raises(ValeurParametreInvalide):
        services.modifier_param(cle, valeur)


@pytest.mark.parametrize("valeur", [2, 2.5])
def test_un_parametre_decimal_accepte_entier_et_decimal(parametres_initialises, valeur):
    assert services.modifier_param("rayon_arrivee_km", valeur).valeur == valeur


def test_modifier_une_cle_inconnue_leve_une_erreur():
    with pytest.raises(ParametreIntrouvable):
        services.modifier_param("cle_inexistante", 1)
