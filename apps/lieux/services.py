"""Lieux connus de Lomé proposés à la saisie du départ et de l'arrivée."""

from apps.lieux.repository import lieu_repository

LIMITE = 20
LONGUEUR_MIN = 2


def rechercher_lieux(terme: str = ""):
    """Lieux actifs dont le libellé ou le quartier contient `terme` (2 caractères min.)."""
    terme = terme.strip()
    return lieu_repository.rechercher(terme if len(terme) >= LONGUEUR_MIN else "", LIMITE)
