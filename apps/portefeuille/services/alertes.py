"""Alerte quotidienne à l'équipe Finance : retraits à verser depuis plus de 24 h."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.portefeuille.repository import transaction_repository

ATTENTE_MAX = timedelta(hours=24)


def alerter_retraits_en_attente() -> int:
    """Email aux admins Finance (rôle finance, ou admin sans rôle). Renvoie le nombre."""
    from apps.accounts.repository import user_repository
    from apps.accounts.roles import FINANCE, roles_de
    from apps.notifications.services import envoyer_email

    retraits = list(transaction_repository.retraits_en_attente_avant(timezone.now() - ATTENTE_MAX))
    if not retraits:
        return 0
    total = sum(r.montant for r in retraits)
    lien = f"{settings.BACKOFFICE_URL.rstrip('/')}/admin/transactions"
    for admin in user_repository.admins_actifs():
        if FINANCE in roles_de(admin):
            envoyer_email(
                admin.email,
                f"Kovoit — {len(retraits)} retrait(s) à verser depuis plus de 24 h",
                f"{len(retraits)} retrait(s) attendent leur versement Flooz / Mixx depuis plus de "
                f"24 h, pour {total} F CFA au total.\n\nÀ traiter dans le back-office : {lien}",
            )
    return len(retraits)
