"""F-003 (D-51, D-62) : le téléphone du profil est normalisé (+228XXXXXXXX) ou refusé (400
TELEPHONE_INVALIDE) à chaque écriture : PATCH /moi/, create_user, seed_demo."""

import pytest
from django.core.management import call_command

from apps.accounts.models import User
from apps.accounts.services import modifier_profil
from apps.audit.models import EvenementAudit
from apps.core.telephone import TelephoneInvalide

pytestmark = pytest.mark.django_db

MOI = "/api/v1/moi/"


def _patch(client, **corps):
    return client.patch(MOI, corps, format="json")


def _assert_refus_telephone(reponse):
    assert reponse.status_code == 400
    corps = reponse.json()
    assert corps["statut"] == "failed"
    assert corps["message"]
    assert corps["reponse"]["code"] == "TELEPHONE_INVALIDE"
    erreurs = corps["reponse"]["erreurs"]["telephone"]
    assert isinstance(erreurs, list) and erreurs and all(erreurs)


def test_ca003_2_numero_avec_espaces_enregistre_au_format_international(
    client_utilisateur, utilisateur
):
    reponse = _patch(client_utilisateur, telephone="90 11 22 33")

    assert reponse.status_code == 200
    corps = reponse.json()
    assert (corps["statut"], corps["reponse"]["telephone"]) == ("success", "+22890112233")
    assert corps["message"]
    utilisateur.refresh_from_db()
    assert utilisateur.telephone == "+22890112233"


@pytest.mark.parametrize(
    ("saisie", "attendu"),
    [("(228) 90.11.22.33", "+22890112233"), ("+228 70-11-22-33", "+22870112233")],
)
def test_separateurs_et_indicatif_normalises(client_utilisateur, utilisateur, saisie, attendu):
    assert _patch(client_utilisateur, telephone=saisie).status_code == 200

    utilisateur.refresh_from_db()
    assert utilisateur.telephone == attendu


def test_d65_saisie_copiee_collee_depuis_les_contacts_enregistree(client_utilisateur, utilisateur):
    # Enchâssement bidi (U+202A…U+202C), espace insécable, tirets insécables (U+2011)
    saisie = "\u202a+228\u00a090\u201111\u201122\u201133\u202c"

    reponse = _patch(client_utilisateur, telephone=saisie)

    assert reponse.status_code == 200
    corps = reponse.json()
    assert (corps["statut"], corps["reponse"]["telephone"]) == ("success", "+22890112233")
    utilisateur.refresh_from_db()
    assert utilisateur.telephone == "+22890112233"


def test_ca003_2_numero_incomplet_refuse_avec_l_enveloppe(client_utilisateur, utilisateur):
    avant = utilisateur.telephone

    reponse = _patch(client_utilisateur, telephone="12345")

    _assert_refus_telephone(reponse)
    utilisateur.refresh_from_db()
    assert utilisateur.telephone == avant


@pytest.mark.parametrize(
    "saisie",
    [
        pytest.param("22 11 22 33", id="fixe"),
        pytest.param("abc", id="lettres"),
        pytest.param("90/11/22/33", id="barre_oblique"),
        pytest.param("90" + " " * 25 + "112233", id="33_caracteres"),
    ],
)
def test_fixe_lettres_separateur_inconnu_et_saisie_trop_longue_refuses(client_utilisateur, saisie):
    _assert_refus_telephone(_patch(client_utilisateur, telephone=saisie))


def test_chaine_vide_refusee(client_utilisateur, utilisateur):
    """Comportement actuel : le téléphone étant obligatoire au profil, une chaîne vide ne
    l'efface pas ; elle est refusée comme toute saisie illisible (400 TELEPHONE_INVALIDE)."""
    avant = utilisateur.telephone

    _assert_refus_telephone(_patch(client_utilisateur, telephone=""))

    utilisateur.refresh_from_db()
    assert utilisateur.telephone == avant


def test_refus_du_telephone_n_enregistre_aucun_autre_champ(client_utilisateur, utilisateur):
    reponse = _patch(client_utilisateur, prenom="Edem", telephone="12345", accepter_cgu=True)

    _assert_refus_telephone(reponse)
    utilisateur.refresh_from_db()
    assert utilisateur.prenom != "Edem"
    assert not utilisateur.cgu_version
    # Seule trace : le refus, journalisé par le gestionnaire d'exceptions, sans le numéro saisi
    (evenement,) = EvenementAudit.objects.filter(action="profil.modifier")
    assert (evenement.resultat, evenement.code_motif) == ("refus", "TELEPHONE_INVALIDE")
    assert "12345" not in str(evenement.details) + str(evenement.changements)


def test_patch_sans_telephone_ne_touche_pas_a_un_ancien_numero_illisible(
    client_utilisateur, utilisateur
):
    User.objects.filter(pk=utilisateur.pk).update(telephone="22112233")

    assert _patch(client_utilisateur, prenom="Edem").status_code == 200

    utilisateur.refresh_from_db()
    assert (utilisateur.prenom, utilisateur.telephone) == ("Edem", "22112233")


def test_service_modifier_profil_normalise(utilisateur):
    assert modifier_profil(utilisateur, telephone="0022890112233").telephone == "+22890112233"


def test_create_user_normalise_le_telephone():
    compte = User.objects.create_user("Ama@Exemple.tg", telephone="90-11-22-33")

    compte.refresh_from_db()
    assert compte.telephone == "+22890112233"


def test_create_superuser_normalise_le_telephone():
    compte = User.objects.create_superuser("chef@kovoit.tg", "Mdp-2026!", telephone="70 11 22 33")

    assert compte.telephone == "+22870112233"


@pytest.mark.parametrize("saisie", ["22 11 22 33", "12345"])
def test_create_user_refuse_un_numero_invalide(saisie):
    with pytest.raises(TelephoneInvalide):
        User.objects.create_user("ama@exemple.tg", telephone=saisie)

    assert not User.objects.filter(email="ama@exemple.tg").exists()


def test_create_user_sans_telephone_reste_possible():
    assert User.objects.create_user("ama@exemple.tg").telephone == ""


def test_seed_demo_enregistre_les_telephones_au_format_international(settings):
    settings.DEBUG = True

    call_command("seed_demo")

    demo = User.objects.filter(email__endswith="demo@kovoit.tg")
    assert sorted(demo.values_list("telephone", flat=True)) == ["+22890111111", "+22890222222"]
