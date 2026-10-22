"""Lecture du journal pour le back-office : liste filtrée, flux temps réel, statistiques."""

from datetime import datetime, timedelta

from django.db.models import Q

from apps.accounts.repository import user_repository
from apps.audit.models import Role
from apps.audit.repository import evenement_repository

# Le flux relit les dernières secondes déjà vues : un événement écrit dans une transaction
# longue peut être validé après un événement plus récent. Le client dédoublonne par id.
MARGE_FLUX = timedelta(seconds=30)
LIMITE_FLUX = 200
FILTRES_EXACTS = {
    "acteur": "acteur_id",
    "role": "acteur_role",
    "categorie": "categorie",
    "action": "action",
    "resultat": "resultat",
    "canal": "canal",
    "ressource_type": "ressource_type",
    "ressource_id": "ressource_id",
    "gravite": "gravite",
    "correlation": "request_id",
}


def _conditions(filtres: dict) -> list[Q]:
    conditions = [
        Q(**{champ: filtres[cle]}) for cle, champ in FILTRES_EXACTS.items() if filtres.get(cle)
    ]
    if filtres.get("debut"):
        conditions.append(Q(enregistre_le__gte=filtres["debut"]))
    if filtres.get("fin"):
        conditions.append(Q(enregistre_le__lte=filtres["fin"]))
    if filtres.get("utilisateur"):
        # Fiche d'un utilisateur : ses actions et celles qui portent sur son compte
        identifiant = filtres["utilisateur"]
        conditions.append(
            Q(acteur_id=identifiant)
            | Q(ressource_type="utilisateur", ressource_id=str(identifiant))
        )
    if filtres.get("recherche"):
        terme = filtres["recherche"]
        conditions.append(
            Q(action__icontains=terme)
            | Q(code_motif__icontains=terme)
            | Q(ressource_id__icontains=terme)
            | Q(request_id__icontains=terme)
        )
    return conditions


def lister_evenements(filtres: dict):
    return evenement_repository.lister(*_conditions(filtres))


def get_evenement(evenement_id):
    return evenement_repository.get_by_id(evenement_id)


def flux_depuis(depuis: datetime, filtres: dict | None = None) -> dict:
    """Mêmes filtres que la liste : le direct n'affiche que ce que la liste montrerait."""
    evenements = list(
        evenement_repository.recents_depuis(
            depuis - MARGE_FLUX, LIMITE_FLUX + 1, *_conditions(filtres or {})
        )
    )
    return {"evenements": evenements[:LIMITE_FLUX], "tronque": len(evenements) > LIMITE_FLUX}


def acteurs(evenements) -> dict:
    """{id: utilisateur} pour une page d'événements, en une requête (comptes encore présents)."""
    identifiants = {e.acteur_id for e in evenements if e.acteur_id}
    return {u.id: u for u in user_repository.filter(id__in=identifiants)}


def statistiques(debut: datetime, fin: datetime) -> dict:
    chiffres = evenement_repository.statistiques(debut, fin, [Role.PASSAGER, Role.CONDUCTEUR])
    chiffres["derniere_activite"] = evenement_repository.derniere_activite()
    return chiffres
