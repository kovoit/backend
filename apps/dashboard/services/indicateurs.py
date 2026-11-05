"""Économies du conducteur (le tableau de bord administrateur est dans tableau_de_bord.py)."""

from django.utils import timezone

from apps.portefeuille.repository import transaction_repository


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
