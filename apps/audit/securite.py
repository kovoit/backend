"""Filtre des données jointes à un événement : rien de secret ni de volumineux n'est conservé.

Les appelants passent des champs choisis un par un (jamais le corps d'une requête). Ce filtre
est un second rempart : toute clé dont le nom évoque un secret est remplacée, les valeurs sont
converties en types JSON simples et tronquées.
"""

import re
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

MASQUE = "[masqué]"
MAX_CLES = 20
MAX_LONGUEUR = 300
_CLE_SENSIBLE = re.compile(
    r"pass|mot_de_passe|token|jeton|secret|access|refresh|authorization|cookie|otp|"
    r"code_depart|^code$|fichier|file|piece_contenu|iban|carte",
    re.IGNORECASE,
)


def _valeur(valeur):
    if valeur is None or isinstance(valeur, bool | int | float):
        return valeur
    if isinstance(valeur, Decimal):
        return float(valeur)
    if isinstance(valeur, datetime | date):
        return valeur.isoformat()
    if isinstance(valeur, UUID):
        return str(valeur)
    if isinstance(valeur, list | tuple | set):
        return [_valeur(v) for v in list(valeur)[:MAX_CLES]]
    if isinstance(valeur, dict):
        return nettoyer(valeur)
    texte = str(valeur)
    return texte if len(texte) <= MAX_LONGUEUR else f"{texte[:MAX_LONGUEUR]}…"


def nettoyer(donnees: dict | None) -> dict:
    propre = {}
    for cle, valeur in list((donnees or {}).items())[:MAX_CLES]:
        cle = str(cle)
        propre[cle] = MASQUE if _CLE_SENSIBLE.search(cle) else _valeur(valeur)
    return propre


def changements(avant: dict, apres: dict) -> dict:
    """{champ: [ancienne, nouvelle]} pour les seuls champs qui ont changé."""
    return nettoyer(
        {
            champ: [avant.get(champ), apres.get(champ)]
            for champ in apres
            if avant.get(champ) != apres.get(champ)
        }
    )
