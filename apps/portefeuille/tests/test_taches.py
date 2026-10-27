"""Tâche planifiée de vérification des recharges Mobile Money (celery beat)."""

import pytest

from apps.portefeuille import services, tasks
from apps.portefeuille.models import Transaction
from kovoit.celery import app


def test_verification_des_paiements_planifiee_toutes_les_deux_minutes():
    assert app.conf.beat_schedule["verification-des-paiements-mobile-money"] == {
        "task": "apps.portefeuille.tasks.verifier_paiements",
        "schedule": 120,
    }


def test_nom_de_la_tache_correspond_a_la_planification():
    assert tasks.verifier_paiements.name == "apps.portefeuille.tasks.verifier_paiements"


@pytest.mark.django_db
def test_tache_valide_une_recharge_recente_payee(utilisateur, paygate):
    ligne = services.recharger(utilisateur, 2000, "flooz")
    paygate.statut_paiement = 0

    assert tasks.verifier_paiements() == 1

    assert Transaction.objects.get(id=ligne.id).statut == "validee"
    assert services.solde(utilisateur).total == 2000


@pytest.mark.django_db
def test_tache_sans_recharge_en_attente_ne_traite_rien(utilisateur, paygate):
    assert tasks.verifier_paiements.delay().get() == 0
    assert paygate.appels == []
