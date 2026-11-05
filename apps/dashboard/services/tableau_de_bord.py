"""Tableau de bord du back-office : indicateurs sur une période, files de travail, évolution."""

from datetime import datetime, timedelta

from django.utils import timezone

from apps.accounts.repository import user_repository
from apps.confiance.services import compter_signalements_ouverts
from apps.dashboard.demo import COMPTES_DEMO
from apps.kyc.models import StatutKyc, TypeDossier
from apps.kyc.repository import dossier_repository
from apps.portefeuille.repository import transaction_repository
from apps.reservations.models import StatutReservation
from apps.reservations.repository import reservation_repository
from apps.trajets.repository import trajet_repository

PERIODES = {"7j": "7 derniers jours", "30j": "30 derniers jours", "mois": "Mois en cours"}


def bornes(periode: str, maintenant: datetime | None = None) -> tuple[datetime, datetime]:
    """Du premier jour à minuit (heure de Lomé) jusqu'à maintenant. Le jour courant est inclus."""
    maintenant = timezone.localtime(maintenant or timezone.now())
    minuit = maintenant.replace(hour=0, minute=0, second=0, microsecond=0)
    if periode == "mois":
        return minuit.replace(day=1), maintenant
    return minuit - timedelta(days=int(periode.removesuffix("j")) - 1), maintenant


def tableau_de_bord(periode: str) -> dict:
    debut, fin = bornes(periode)
    trajets = trajet_repository.termines_par_jour(debut, fin)
    passagers = reservation_repository.transportes_par_jour(debut, fin)
    jours = [debut.date() + timedelta(days=n) for n in range((fin.date() - debut.date()).days + 1)]
    par_statut = reservation_repository.compter_par_statut(debut, fin)

    return {
        "periode": {"code": periode, "debut": debut.date(), "fin": fin.date()},
        # Comptes créés par seed_demo / seed_backoffice : les chiffres incluent leur activité
        "donnees_demo": user_repository.exists(COMPTES_DEMO),
        "indicateurs": {
            "trajets_publies": trajet_repository.compter(cree_le__range=(debut, fin)),
            "trajets_termines": sum(trajets.values()),
            "passagers_transportes": sum(passagers.values()),
            "economies_realisees": transaction_repository.total_credits(depuis=debut),
            "commissions_kovoit": transaction_repository.total_commissions(depuis=debut),
            "utilisateurs_verifies": dossier_repository.compter_utilisateurs_verifies(),
            "conducteurs_verifies": dossier_repository.compter_verifies(TypeDossier.CONDUCTEUR),
        },
        "a_traiter": {
            "kyc_en_attente": dossier_repository.compter(statut=StatutKyc.EN_ATTENTE),
            "signalements_ouverts": compter_signalements_ouverts(),
            "litiges": reservation_repository.compter(statut=StatutReservation.LITIGE),
            "retraits_en_attente": transaction_repository.compter_retraits_en_attente(),
        },
        "evolution": [
            {"date": jour, "trajets": trajets.get(jour, 0), "passagers": passagers.get(jour, 0)}
            for jour in jours
        ],
        "reservations_par_statut": {
            statut: par_statut.get(statut, 0) for statut in StatutReservation.values
        },
    }
