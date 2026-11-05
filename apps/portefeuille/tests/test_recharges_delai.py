"""F-053 : borne du délai d'abandon d'une recharge, lue dans `paiement_attente_max_min`.

L'heure est figée : la recharge est créée à DEBUT, la tâche planifiée tourne N minutes plus
tard, PayGate répond toujours « en cours » (statut 2).
"""

from datetime import datetime, timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from apps.audit.models import EvenementAudit
from apps.parametres.services import get_param, modifier_param
from apps.portefeuille import services, tasks
from apps.portefeuille.models import Transaction

pytestmark = pytest.mark.django_db

DEBUT = timezone.make_aware(datetime(2026, 10, 27, 8, 0))


def _recharge_puis_tache_apres(utilisateur, paygate, minutes: int) -> Transaction:
    with freeze_time(DEBUT):
        ligne = services.recharger(utilisateur, 2000, "flooz")
    paygate.statut_paiement = 2  # PayGate : paiement toujours en cours
    with freeze_time(DEBUT + timedelta(minutes=minutes)):
        tasks.verifier_paiements()
    return Transaction.objects.get(id=ligne.id)


def _abandons():
    return EvenementAudit.objects.filter(action="paiement.confirmer", code_motif="DELAI_DEPASSE")


def test_delai_d_attente_par_defaut_est_de_60_minutes():
    assert get_param("paiement_attente_max_min") == 60


def test_recharge_de_59_minutes_reste_en_attente(utilisateur, paygate):
    ligne = _recharge_puis_tache_apres(utilisateur, paygate, 59)

    assert ligne.statut == "en_attente"
    assert not _abandons().exists()
    assert services.solde(utilisateur).total == 0


def test_recharge_d_exactement_60_minutes_reste_en_attente(utilisateur, paygate):
    """Abandon « au-delà » du délai : la borne elle-même n'est pas dépassée."""
    ligne = _recharge_puis_tache_apres(utilisateur, paygate, 60)

    assert ligne.statut == "en_attente"
    assert not _abandons().exists()


def test_recharge_de_61_minutes_est_abandonnee(utilisateur, paygate):
    ligne = _recharge_puis_tache_apres(utilisateur, paygate, 61)

    assert ligne.statut == "echouee"
    confirmation = EvenementAudit.objects.get(action="paiement.confirmer")  # exactement une
    assert (confirmation.resultat, confirmation.code_motif) == ("echec", "DELAI_DEPASSE")
    assert services.solde(utilisateur).total == 0


def test_delai_reduit_a_30_minutes_abandonne_une_recharge_de_45_minutes(utilisateur, paygate):
    modifier_param("paiement_attente_max_min", 30)

    ligne = _recharge_puis_tache_apres(utilisateur, paygate, 45)

    assert ligne.statut == "echouee"
    assert _abandons().count() == 1


def test_delai_de_60_minutes_garde_une_recharge_de_45_minutes(utilisateur, paygate):
    modifier_param("paiement_attente_max_min", 60)

    ligne = _recharge_puis_tache_apres(utilisateur, paygate, 45)

    assert ligne.statut == "en_attente"
    assert not _abandons().exists()
