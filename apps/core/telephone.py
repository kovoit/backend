"""Numéros de téléphone togolais (D-51, D-62, D-64) : seule règle de lecture du backend.

Accepté : un mobile togolais, 8 chiffres commençant par 7 ou 9, préfixe facultatif +228,
00228 ou 228. Séparateurs tolérés et retirés avant analyse : espaces (insécables compris),
tirets, points, parenthèses ; D-65 : tirets Unicode (U+2010 à U+2015, moins U+2212) et marques
invisibles d'un copier-coller depuis les Contacts (bidirectionnelles U+200E, U+200F, U+202A à
U+202E, U+2066 à U+2069 ; largeur nulle U+200B à U+200D, U+2060, U+FEFF). Tout autre caractère
est refusé (lettres, « / », « + » hors +228, chiffres non ASCII).
Ex. « 90 11 22 33 », « 90-11-22-33 », « (228) 90.11.22.33 », « +228 90–11–22–33 ».
Refusé : un fixe (« 22 11 22 33 »), un numéro incomplet (« 12345 »).
Forme enregistrée au profil : +228XXXXXXXX. Forme Mobile Money (PayGate) : 8 chiffres.

La migration accounts/0007 recopie cette règle (figée) : la modifier ici ne la change pas.
"""

import re

from apps.core.exceptions import DonneesInvalides

INDICATIF = "+228"
LONGUEUR_MAX_SAISIE = 32  # au-delà, inutile d'analyser : refus direct
_SEPARATEURS = re.compile(
    r"[\s\-.()"
    r"\u2010-\u2015\u2212"  # tirets Unicode, signe moins
    r"\u200b-\u200f\u202a-\u202e\u2066-\u2069"  # largeur nulle, marques bidirectionnelles
    r"\u2060\ufeff]"  # gluon de mots, espace insécable de largeur nulle (BOM)
)
_FORMAT = re.compile(r"(?:\+228|00228|228)?([79][0-9]{7})")
MESSAGE_TELEPHONE_INVALIDE = (
    "Numéro de téléphone invalide : saisissez un numéro mobile togolais à 8 chiffres "
    "commençant par 7 ou 9 (ex. 90 11 22 33), avec ou sans +228."
)


class TelephoneInvalide(DonneesInvalides):
    code = "TELEPHONE_INVALIDE"
    message = MESSAGE_TELEPHONE_INVALIDE


def lire_chiffres(saisie: str | None) -> str | None:
    """Les 8 chiffres du numéro, ou None si la saisie n'est pas un mobile togolais lisible."""
    if not isinstance(saisie, str) or len(saisie) > LONGUEUR_MAX_SAISIE:
        return None
    correspondance = _FORMAT.fullmatch(_SEPARATEURS.sub("", saisie))
    return correspondance.group(1) if correspondance else None


def chiffres_locaux(saisie: str | None, message: str = MESSAGE_TELEPHONE_INVALIDE) -> str:
    """Les 8 chiffres (ex. 90112233), sinon `TelephoneInvalide` (400 TELEPHONE_INVALIDE)."""
    chiffres = lire_chiffres(saisie)
    if chiffres is None:
        raise TelephoneInvalide(message, erreurs={"telephone": [message]})
    return chiffres


def normaliser_telephone(saisie: str | None) -> str:
    """Forme enregistrée +228XXXXXXXX, sinon `TelephoneInvalide` (400 TELEPHONE_INVALIDE)."""
    return INDICATIF + chiffres_locaux(saisie)
