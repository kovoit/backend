"""Description d'un paramètre du registre (valeur de départ, type, bornes)."""

from dataclasses import dataclass

ENTIER = "entier"
DECIMAL = "decimal"


@dataclass(frozen=True)
class Defaut:
    valeur: int | float
    type_valeur: str
    description: str
    groupe: str
    unite: str = ""
    # Plus petite valeur acceptée : 0 casserait certaines règles (ex. suspension sans fin)
    minimum: int | float = 0
    # Plus grande valeur acceptée (None : pas de limite), ex. commission < 100 %
    maximum: int | float | None = None
