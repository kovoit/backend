"""Rétention du journal : seule voie de suppression, elle-même journalisée."""

from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.repository import evenement_repository
from apps.audit.services.journal import journaliser


def purger_expires() -> int:
    """Supprime les événements plus vieux que `audit_retention_jours`."""
    from apps.parametres.services import get_param  # parametres journalise ses modifications

    jours = get_param("audit_retention_jours")
    limite = timezone.now() - timedelta(days=jours)
    with transaction.atomic():
        nombre = evenement_repository.purger(Q(enregistre_le__lt=limite))
        if nombre:
            journaliser(
                "audit.purger",
                systeme=True,
                details={"supprimes": nombre, "retention_jours": jours, "avant": limite},
            )
    return nombre


def purger_acteurs(acteur_ids) -> int:
    """Données de démonstration supprimées : leurs événements partent avec elles."""
    identifiants = [str(i) for i in acteur_ids]
    return evenement_repository.purger(
        Q(acteur_id__in=identifiants)
        | Q(ressource_type="utilisateur", ressource_id__in=identifiants)
    )
