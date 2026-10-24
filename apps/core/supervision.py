"""Supervision : état des composants (/api/v1/sante/) et battement de cœur de celery beat.

Une sonde externe (UptimeRobot, etc.) interroge /api/v1/sante/ : 503 dès qu'un composant est
en panne, avec son nom (jamais d'information sensible).
"""

from django.core.cache import cache
from django.db import connection
from django.utils import timezone

CLE_BATTEMENT = "supervision:battement_celery"
BATTEMENT_MAX_S = 15 * 60  # tâche toutes les 5 min : 15 min sans battement = planificateur arrêté


def battre() -> None:
    """Appelée par celery beat toutes les 5 min (preuve que beat et le worker tournent)."""
    cache.set(CLE_BATTEMENT, timezone.now().isoformat(), timeout=None)


def _base() -> bool:
    try:
        with connection.cursor() as curseur:
            curseur.execute("SELECT 1")
        return True
    except Exception:  # noqa: BLE001
        return False


def _cache() -> bool:
    try:
        cache.set("supervision:sonde", "ok", timeout=30)
        return cache.get("supervision:sonde") == "ok"
    except Exception:  # noqa: BLE001
        return False


def _celery() -> bool:
    try:
        dernier = cache.get(CLE_BATTEMENT)
    except Exception:  # noqa: BLE001
        return False
    if not dernier:
        return False
    ecart = timezone.now() - timezone.datetime.fromisoformat(dernier)
    return ecart.total_seconds() <= BATTEMENT_MAX_S


def etat() -> dict[str, bool]:
    return {"base_de_donnees": _base(), "cache": _cache(), "taches_planifiees": _celery()}
