"""Lecture (avec cache) et modification des paramètres métier."""

import logging
from typing import Any

from django.core.cache import cache
from django.db import transaction

from apps.core.exceptions import DonneesInvalides, RessourceIntrouvable
from apps.parametres.defauts import ENTIER, PARAMETRES_PAR_DEFAUT, Defaut
from apps.parametres.models import Parametre
from apps.parametres.repository import parametre_repository

logger = logging.getLogger(__name__)

DUREE_CACHE_S = 300


class ParametreIntrouvable(RessourceIntrouvable):
    code = "PARAMETRE_INTROUVABLE"
    message = "Paramètre inconnu."


class ValeurParametreInvalide(DonneesInvalides):
    code = "VALEUR_PARAMETRE_INVALIDE"
    message = "Valeur de paramètre invalide."


def _cle_cache(cle: str) -> str:
    return f"parametre:{cle}"


def get_param(cle: str) -> Any:
    """Valeur courante d'un paramètre. Seul point d'accès autorisé aux paramètres métier."""
    valeur = cache.get(_cle_cache(cle))
    if valeur is not None:
        return valeur

    valeur = parametre_repository.get_valeur(cle)
    if valeur is None:
        valeur = _defaut(cle).valeur
        logger.warning("Paramètre %s absent en base : valeur de départ utilisée.", cle)

    cache.set(_cle_cache(cle), valeur, DUREE_CACHE_S)
    return valeur


def lister_parametres() -> list[Parametre]:
    """Paramètres connus, dans l'ordre du registre (celui de l'écran du back-office)."""
    ordre = {cle: rang for rang, cle in enumerate(PARAMETRES_PAR_DEFAUT)}
    connus = [p for p in parametre_repository.lister() if p.cle in ordre]
    return sorted(connus, key=lambda parametre: ordre[parametre.cle])


def valider_valeur(cle: str, valeur: Any) -> None:
    defaut = _defaut(cle)
    if isinstance(valeur, bool) or not isinstance(valeur, int | float):
        raise ValeurParametreInvalide(f"« {cle} » doit être un nombre.")
    if defaut.type_valeur == ENTIER and not isinstance(valeur, int):
        raise ValeurParametreInvalide(f"« {cle} » doit être un nombre entier.")
    if valeur < defaut.minimum:
        # Écriture française : 0,1 km
        minimum = str(defaut.minimum).replace(".", ",")
        unite = f" {defaut.unite}" if defaut.unite else ""
        raise ValeurParametreInvalide(
            f"« {cle} » doit valoir au moins {minimum}{unite}.",
            erreurs={"valeur": [f"Minimum : {minimum}{unite}."]},
        )


def modifier_param(cle: str, valeur: Any, par=None) -> Parametre:
    valider_valeur(cle, valeur)
    defaut = _defaut(cle)
    with transaction.atomic():
        parametre_repository.creer_si_absent(cle, defaut.valeur, defaut.description)
        parametre = parametre_repository.get_for_update(cle)
        parametre_repository.update(parametre, valeur=valeur, modifie_par=par)
    cache.delete(_cle_cache(cle))
    return parametre


def initialiser_parametres() -> int:
    """Crée les paramètres manquants avec leur valeur de départ. N'écrase jamais l'existant."""
    crees = 0
    for cle, defaut in PARAMETRES_PAR_DEFAUT.items():
        if parametre_repository.creer_si_absent(cle, defaut.valeur, defaut.description):
            crees += 1
    return crees


def _defaut(cle: str) -> Defaut:
    defaut = PARAMETRES_PAR_DEFAUT.get(cle)
    if defaut is None:
        raise ParametreIntrouvable(f"Paramètre inconnu : {cle}.")
    return defaut
