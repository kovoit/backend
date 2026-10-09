"""Indicateurs : économies du conducteur et tableau de bord administrateur."""

from django.utils import timezone

from apps.accounts.repository import user_repository
from apps.kyc.models import TypeDossier
from apps.kyc.repository import dossier_repository
from apps.portefeuille.repository import transaction_repository
from apps.reservations.repository import reservation_repository
from apps.trajets.models import StatutTrajet
from apps.trajets.repository import trajet_repository


def _debut_du_mois():
    return timezone.localtime().replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def economies_conducteur(conducteur) -> dict:
    """Somme payée par les passagers : par trajet et cumul du mois en cours."""
    par_trajet = [
        {
            "trajet_id": ligne["reservation__trajet_id"],
            "depart_le": ligne["reservation__trajet__depart_le"],
            "depart": ligne["reservation__trajet__depart_libelle"],
            "arrivee": ligne["reservation__trajet__arrivee_libelle"],
            "montant": ligne["montant"],
        }
        for ligne in transaction_repository.credits_par_trajet(conducteur)
    ]
    return {
        "mois_en_cours": transaction_repository.total_credits(conducteur, _debut_du_mois()),
        "total": transaction_repository.total_credits(conducteur),
        "par_trajet": par_trajet,
    }


def indicateurs() -> dict:
    return {
        "utilisateurs": user_repository.compter(),
        "passagers_verifies": dossier_repository.compter_verifies(TypeDossier.PASSAGER),
        "conducteurs_verifies": dossier_repository.compter_verifies(TypeDossier.CONDUCTEUR),
        "trajets_publies": trajet_repository.compter(),
        "trajets_termines": trajet_repository.compter(statut=StatutTrajet.TERMINE),
        "passagers_transportes": reservation_repository.compter_transportes(),
        "economies_realisees": transaction_repository.total_credits(),
    }
