"""Export CSV du journal : volume limité, colonnes fixes, export lui-même journalisé."""

import csv
import io
import json

from apps.audit.catalogue import ACTIONS
from apps.audit.repository import evenement_repository
from apps.audit.services.consultation import _conditions
from apps.audit.services.journal import journaliser

LIMITE_EXPORT = 10_000
COLONNES = [
    "enregistre_le",
    "survenu_le",
    "action",
    "libelle",
    "categorie",
    "resultat",
    "gravite",
    "canal",
    "acteur_id",
    "acteur_role",
    "ressource_type",
    "ressource_id",
    "code_motif",
    "request_id",
    "details",
    "changements",
]


def exporter_csv(filtres: dict) -> tuple[str, int, bool]:
    """(contenu CSV, nombre de lignes, tronqué ?). Les détails sont déjà filtrés à l'écriture."""
    evenements = list(evenement_repository.lister(*_conditions(filtres))[: LIMITE_EXPORT + 1])
    tronque = len(evenements) > LIMITE_EXPORT
    evenements = evenements[:LIMITE_EXPORT]
    tampon = io.StringIO()
    ecrivain = csv.writer(tampon, delimiter=";")
    ecrivain.writerow(COLONNES)
    for e in evenements:
        definition = ACTIONS.get(e.action)
        ecrivain.writerow(
            [
                e.enregistre_le.isoformat(),
                e.survenu_le.isoformat(),
                e.action,
                definition.libelle if definition else e.action,
                e.categorie,
                e.resultat,
                e.gravite,
                e.canal,
                e.acteur_id or "",
                e.acteur_role,
                e.ressource_type,
                e.ressource_id,
                e.code_motif,
                e.request_id,
                json.dumps(e.details, ensure_ascii=False),
                json.dumps(e.changements, ensure_ascii=False),
            ]
        )
    journaliser(
        "audit.exporter",
        details={"lignes": len(evenements), "tronque": tronque, "filtres": filtres},
    )
    return tampon.getvalue(), len(evenements), tronque
