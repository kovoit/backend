"""Code de départ à 4 chiffres (preuve que le passager est monté).

Le code n'est jamais stocké, ni en clair ni haché : il est recalculé à partir d'un sel
aléatoire propre à la réservation et de SECRET_KEY (HMAC-SHA256). Une fuite de la base
ne révèle donc aucun code. Il n'est renvoyé qu'au passager.
"""

import hashlib
import hmac
import secrets

from django.conf import settings


def nouveau_sel() -> str:
    return secrets.token_hex(16)


def calculer_code(reservation) -> str:
    message = f"{reservation.id}:{reservation.code_depart_sel}".encode()
    empreinte = hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()
    return f"{int(empreinte, 16) % 10_000:04d}"


def code_valide(reservation, code: str) -> bool:
    if not reservation.code_depart_sel:
        return False
    return hmac.compare_digest(calculer_code(reservation), code)
