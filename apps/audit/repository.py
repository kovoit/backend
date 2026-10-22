from datetime import datetime

from django.db import connection, transaction
from django.db.models import Count, Max, Q

from apps.audit.models import EvenementAudit
from apps.core.repository import BaseRepository

# Seule exception au trigger « ajout seul » : variable de session posée le temps d'une purge
VARIABLE_PURGE = "kovoit.audit_purge"


class EvenementRepository(BaseRepository[EvenementAudit]):
    model = EvenementAudit
    message_introuvable = "Événement introuvable."

    def lister(self, *conditions: Q):
        return self.filter(*conditions).order_by("-enregistre_le", "-id")

    def recents_depuis(self, depuis: datetime, limite: int, *conditions: Q):
        """Ordre chronologique : le client les ajoute en tête dans l'ordre d'arrivée."""
        recents = self.filter(*conditions, enregistre_le__gte=depuis)
        return recents.order_by("enregistre_le", "id")[:limite]

    def statistiques(self, debut: datetime, fin: datetime, roles_utilisateurs: list[str]) -> dict:
        periode = Q(enregistre_le__range=(debut, fin))
        return self.filter(periode).aggregate(
            total=Count("id"),
            metier_succes=Count("id", filter=Q(categorie="metier", resultat="succes")),
            metier_refus=Count("id", filter=Q(categorie="metier") & ~Q(resultat="succes")),
            securite=Count("id", filter=Q(categorie="securite")),
            securite_refus=Count("id", filter=Q(categorie="securite") & ~Q(resultat="succes")),
            technique=Count("id", filter=Q(categorie="technique")),
            admin=Count("id", filter=Q(categorie="admin")),
            utilisateurs_actifs=Count(
                "acteur_id", filter=Q(acteur_role__in=roles_utilisateurs), distinct=True
            ),
        )

    def derniere_activite(self):
        return self.queryset().aggregate(derniere=Max("enregistre_le"))["derniere"]

    def purger(self, *conditions: Q) -> int:
        """Suppression contrôlée (rétention, données de démo), dans une transaction dédiée."""
        with transaction.atomic():
            if connection.vendor == "postgresql":
                with connection.cursor() as curseur:
                    curseur.execute("SELECT set_config(%s, 'on', true)", [VARIABLE_PURGE])
            # QuerySet.delete() n'appelle pas EvenementAudit.delete() (réservé à l'instance)
            nombre, _ = self.filter(*conditions).delete()
        return nombre


evenement_repository = EvenementRepository()
