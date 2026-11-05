"""F-053 : une recharge déjà traitée par un callback n'est jamais réécrite (abandon, recharger)."""

from datetime import timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from apps.audit.models import EvenementAudit
from apps.portefeuille import services
from apps.portefeuille.models import Transaction
from apps.portefeuille.paygate import PayGateProvider
from apps.portefeuille.provider import PaiementIndisponible, Resultat
from apps.portefeuille.services import mobile_money

pytestmark = pytest.mark.django_db


def _recharge_ancienne(utilisateur):
    """Recharge en attente depuis plus que `paiement_attente_max_min` (60 min)."""
    with freeze_time(timezone.now() - timedelta(hours=2)):
        return services.recharger(utilisateur, 2000, "flooz")


def _evenements(action="paiement.confirmer", **filtres):
    return EvenementAudit.objects.filter(action=action, **filtres)


def _statut(ligne):
    return Transaction.objects.get(id=ligne.id).statut


def test_callback_entre_derniere_verification_et_abandon_garde_la_recharge(
    utilisateur, paygate, monkeypatch
):
    ligne = _recharge_ancienne(utilisateur)
    original = mobile_money._actualiser

    def verification_puis_callback(transaction_id, systeme):
        perimee = original(transaction_id, systeme)  # PayGate : « en cours »
        paygate.statut_paiement = 0
        original(transaction_id, systeme=True)  # le callback valide la ligne entre-temps
        return perimee  # copie périmée, encore en attente

    monkeypatch.setattr(mobile_money, "_actualiser", verification_puis_callback)
    services.verifier_paiements_en_attente()

    assert _statut(ligne) == "validee"
    assert services.solde(utilisateur).total == 2000
    assert _evenements(resultat="succes").count() == 1
    assert not _evenements(code_motif="DELAI_DEPASSE").exists()


def test_recharge_expiree_toujours_en_cours_est_abandonnee(utilisateur, paygate):
    ligne = _recharge_ancienne(utilisateur)
    paygate.statut_paiement = 2

    services.verifier_paiements_en_attente()

    assert _statut(ligne) == "echouee"
    assert services.solde(utilisateur).total == 0
    abandon = _evenements().get()
    assert (abandon.resultat, abandon.code_motif) == ("echec", "DELAI_DEPASSE")
    assert (abandon.acteur_id, abandon.acteur_role) == (None, "systeme")


def test_recharge_expiree_payee_est_validee_par_la_derniere_verification(utilisateur, paygate):
    ligne = _recharge_ancienne(utilisateur)
    paygate.statut_paiement = 0

    services.verifier_paiements_en_attente()

    assert _statut(ligne) == "validee"
    assert services.solde(utilisateur).total == 2000
    assert _evenements(resultat="succes").count() == 1
    assert not _evenements(code_motif="DELAI_DEPASSE").exists()


def test_second_passage_apres_abandon_ne_change_rien(utilisateur, paygate):
    ligne = _recharge_ancienne(utilisateur)
    services.verifier_paiements_en_attente()
    appels = len(paygate.appels)

    services.verifier_paiements_en_attente()

    assert _statut(ligne) == "echouee"
    assert _evenements(code_motif="DELAI_DEPASSE").count() == 1
    assert len(paygate.appels) == appels  # la ligne échouée n'est plus interrogée


def test_second_passage_apres_validation_tardive_ne_journalise_rien(utilisateur, paygate):
    ligne = _recharge_ancienne(utilisateur)
    paygate.statut_paiement = 0
    services.verifier_paiements_en_attente()
    evenements = EvenementAudit.objects.count()

    services.verifier_paiements_en_attente()

    assert _statut(ligne) == "validee"
    assert EvenementAudit.objects.count() == evenements
    assert services.solde(utilisateur).total == 2000


def _callback_pendant_l_appel(monkeypatch, paygate, panne=False):
    """`collecter` : PayGate enregistre la demande, le callback valide la ligne, puis la
    réponse arrive en retard (référence différente) ou se perd (PaiementIndisponible)."""
    original = PayGateProvider.collecter

    def collecter(self, utilisateur, montant, moyen, telephone, identifiant):
        original(self, utilisateur, montant, moyen, telephone, identifiant)
        paygate.statut_paiement = 0
        mobile_money._actualiser(identifiant, systeme=True)
        if panne:
            raise PaiementIndisponible()
        return Resultat("PG-REPONSE-TARDIVE", "en_attente")

    monkeypatch.setattr(PayGateProvider, "collecter", collecter)


def test_recharger_n_ecrase_pas_une_ligne_validee_par_callback(utilisateur, paygate, monkeypatch):
    _callback_pendant_l_appel(monkeypatch, paygate)

    ligne = services.recharger(utilisateur, 2000, "flooz")

    en_base = Transaction.objects.get(id=ligne.id)
    assert (ligne.statut, en_base.statut) == ("validee", "validee")
    assert en_base.reference_externe == "PG-123"  # pas la référence de la réponse tardive
    assert services.solde(utilisateur).total == 2000
    assert _evenements(resultat="succes").count() == 1
    assert not _evenements("paiement.initier").exists()
    assert not _evenements("portefeuille.recharger").exists()


def test_recharger_reponse_perdue_mais_callback_traite_renvoie_la_ligne_validee(
    utilisateur, paygate, monkeypatch
):
    _callback_pendant_l_appel(monkeypatch, paygate, panne=True)

    ligne = services.recharger(utilisateur, 2000, "flooz")  # aucune erreur relevée

    en_base = Transaction.objects.get(id=ligne.id)
    assert (ligne.statut, en_base.statut) == ("validee", "validee")
    assert en_base.reference_externe == "PG-123"
    assert services.solde(utilisateur).total == 2000
    assert not _evenements("paiement.initier").exists()
    assert _evenements().count() == 1  # seule la confirmation du callback


def test_recharger_paygate_injoignable_sans_callback_echoue_et_releve_l_erreur(
    utilisateur, paygate, monkeypatch
):
    def panne(self, *args):
        raise PaiementIndisponible()

    monkeypatch.setattr(PayGateProvider, "collecter", panne)

    with pytest.raises(PaiementIndisponible):
        services.recharger(utilisateur, 2000, "flooz")

    assert Transaction.objects.get().statut == "echouee"
    echec = _evenements("paiement.initier").get()
    assert (echec.resultat, echec.code_motif) == ("echec", "PAIEMENT_INDISPONIBLE")
    assert services.solde(utilisateur).total == 0
