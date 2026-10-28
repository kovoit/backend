"""F-003 (D-51, D-62, D-64) : lecture des numéros togolais, seule règle du backend.

Accepté : mobile togolais à 8 chiffres commençant par 7 ou 9, préfixe +228 / 00228 / 228
facultatif, séparateurs (espaces, insécables compris, tirets, points, parenthèses) retirés ;
D-65 : tirets Unicode, marques bidirectionnelles et largeur nulle d'un copier-coller aussi.
Forme du profil : +228XXXXXXXX ; forme Mobile Money : 8 chiffres."""

import pytest

from apps.core.exceptions import DonneesInvalides
from apps.core.telephone import (
    MESSAGE_TELEPHONE_INVALIDE,
    TelephoneInvalide,
    chiffres_locaux,
    lire_chiffres,
    normaliser_telephone,
)

VALIDES = [
    ("90 11 22 33", "+22890112233"),  # CA-003-2
    ("90-11-22-33", "+22890112233"),
    ("(228) 90.11.22.33", "+22890112233"),
    ("+228 70 11 22 33", "+22870112233"),
    ("0022890112233", "+22890112233"),
    ("22890112233", "+22890112233"),
    ("+22890112233", "+22890112233"),  # forme enregistrée : relue à l'identique
    ("90112233", "+22890112233"),
    ("79112233", "+22879112233"),
    ("90\u00a011\u00a022\u00a033", "+22890112233"),  # espace insécable
    ("+228\u202f90\u202f11\u202f22\u202f33", "+22890112233"),  # espace fine insécable
    ("90" + " " * 24 + "112233", "+22890112233"),  # 32 caractères : limite incluse
]

INVALIDES = [
    pytest.param("22 11 22 33", id="fixe"),
    pytest.param("+228 22 11 22 33", id="fixe_avec_indicatif"),
    pytest.param("12345", id="incomplet_ca_003_2"),
    pytest.param("abc", id="lettres"),
    pytest.param("+90112233", id="plus_sans_indicatif"),
    pytest.param("90/11/22/33", id="barre_oblique"),
    pytest.param("90" + " " * 25 + "112233", id="33_caracteres"),
    pytest.param("9011223", id="7_chiffres"),
    pytest.param("901122334", id="9_chiffres"),
    pytest.param("+33612345678", id="etranger"),
    pytest.param("80112233", id="commence_par_8"),
    pytest.param("٩٠١١٢٢٣٣", id="chiffres_arabes_indiens"),
    pytest.param("+228 ٩٠١١٢٢٣٣", id="chiffres_arabes_indiens_avec_indicatif"),
    pytest.param("90_11_22_33", id="soulignes"),
    pytest.param("90112233a", id="lettre_finale"),
    pytest.param("", id="vide"),
    pytest.param("   ", id="espaces_seuls"),
]


@pytest.mark.parametrize(("saisie", "attendu"), VALIDES)
def test_normaliser_telephone_valide(saisie, attendu):
    assert normaliser_telephone(saisie) == attendu


@pytest.mark.parametrize(("saisie", "attendu"), VALIDES)
def test_chiffres_locaux_valide_8_chiffres(saisie, attendu):
    assert chiffres_locaux(saisie) == attendu.removeprefix("+228")


@pytest.mark.parametrize(("saisie", "attendu"), VALIDES)
def test_lire_chiffres_valide(saisie, attendu):
    assert lire_chiffres(saisie) == attendu.removeprefix("+228")


@pytest.mark.parametrize("saisie", INVALIDES)
def test_normaliser_telephone_refuse(saisie):
    with pytest.raises(TelephoneInvalide) as exc:
        normaliser_telephone(saisie)

    assert exc.value.code == "TELEPHONE_INVALIDE"
    assert exc.value.http_status == 400
    assert exc.value.erreurs == {"telephone": [MESSAGE_TELEPHONE_INVALIDE]}


@pytest.mark.parametrize("saisie", INVALIDES)
def test_lire_chiffres_renvoie_none_sans_erreur(saisie):
    assert lire_chiffres(saisie) is None


@pytest.mark.parametrize("saisie", [None, 90112233, b"90112233"])
def test_saisie_qui_n_est_pas_une_chaine(saisie):
    assert lire_chiffres(saisie) is None
    with pytest.raises(TelephoneInvalide):
        normaliser_telephone(saisie)


def test_chiffres_locaux_message_personnalise_dans_message_et_erreurs():
    with pytest.raises(TelephoneInvalide) as exc:
        chiffres_locaux("22 11 22 33", "Numéro Mobile Money invalide.")

    assert exc.value.message == "Numéro Mobile Money invalide."
    assert exc.value.erreurs == {"telephone": ["Numéro Mobile Money invalide."]}


def test_telephone_invalide_est_une_donnee_invalide():
    """L'API l'enveloppe donc en 400 failed, comme toute DonneesInvalides."""
    assert issubclass(TelephoneInvalide, DonneesInvalides)
    assert TelephoneInvalide().message == MESSAGE_TELEPHONE_INVALIDE


# D-65 : caractères d'un copier-coller (Contacts, messageries), tolérés puis retirés
TIRETS_UNICODE = ["‐", "‑", "‒", "–", "—", "―", "−"]
MARQUES_BIDI = ["‎", "‏", "‪", "‫", "‬", "‭", "‮"]
MARQUES_BIDI += ["⁦", "⁧", "⁨", "⁩"]
LARGEUR_NULLE = ["​", "‌", "‍", "⁠", "﻿"]
COPIER_COLLER = [
    pytest.param(c, id=f"U+{ord(c):04X}") for c in TIRETS_UNICODE + MARQUES_BIDI + LARGEUR_NULLE
]


@pytest.mark.parametrize("caractere", COPIER_COLLER)
def test_d65_caractere_de_copier_coller_retire(caractere):
    c = caractere
    saisie = f"{c}+228{c}90{c}11{c}22{c}33{c}"

    assert normaliser_telephone(saisie) == "+22890112233"


@pytest.mark.parametrize(
    "saisie",
    [
        pytest.param("+228 90–11–22–33", id="tirets_demi_cadratin"),
        pytest.param("‪+228 90 11 22 33‬", id="enchassement_bidi"),
        pytest.param("90​112233", id="espace_largeur_nulle"),
        pytest.param("⁨−228 90‑11‑22‑33⁩", id="melange"),
    ],
)
def test_d65_exemples_de_copier_coller(saisie):
    assert normaliser_telephone(saisie) == "+22890112233"


@pytest.mark.parametrize(
    "saisie",
    [
        pytest.param("‪٩٠١١٢٢٣٣‬", id="arabes"),
        pytest.param("⁦+228 ۹۰۱۱۲۲۳۳", id="persans"),
        pytest.param("90‖11‖22‖33", id="U+2016_hors_liste"),
        pytest.param("90∓11∓22∓33", id="U+2213_hors_liste"),
        pytest.param("90⁡112233", id="U+2061_hors_liste"),
        pytest.param("90⁪112233", id="U+206A_hors_liste"),
        pytest.param("90­112233", id="U+00AD_trait_d_union_conditionnel"),
    ],
)
def test_d65_chiffres_non_ascii_et_caracteres_voisins_toujours_refuses(saisie):
    with pytest.raises(TelephoneInvalide):
        normaliser_telephone(saisie)


def test_d65_plus_de_32_caracteres_surtout_invisibles_refuse_avant_nettoyage():
    saisie = "90112233" + "​" * 25  # 33 caractères, 8 chiffres une fois nettoyés

    assert lire_chiffres(saisie) is None
    with pytest.raises(TelephoneInvalide):
        normaliser_telephone(saisie)


def test_d65_32_caracteres_dont_invisibles_accepte():
    assert normaliser_telephone("90112233" + "﻿" * 24) == "+22890112233"
