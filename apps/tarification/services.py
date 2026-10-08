"""Tarification — algorithme définitif à décider plus tard (PRD §7).

En attendant, le prix par place est le paramètre `prix_simulation`. Seules ces fonctions
seront remplacées : les autres apps ne connaissent pas la formule.
"""

from decimal import Decimal

from apps.parametres.services import get_param


def prix_par_place(distance_km: Decimal | None = None) -> int:
    return int(get_param("prix_simulation"))


def frais_service() -> int:
    return int(get_param("frais_service"))
