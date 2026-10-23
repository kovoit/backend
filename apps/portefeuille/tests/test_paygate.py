"""Paiement Mobile Money via PayGate (faux PayGate : aucun appel réseau dans les tests)."""

from datetime import timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from apps.audit.models import EvenementAudit
from apps.portefeuille import services
from apps.portefeuille.models import Transaction
from conftest import demander

pytestmark = pytest.mark.django_db

CALLBACK = "/api/v1/paiements/paygate/callback/"


class FauxPayGate:
    """Remplace paygate._appeler : enregistre les appels, répond selon `statut_paiement`."""

    def __init__(self):
        self.appels = []
        self.statut_paiement = 2  # en cours
        self.statut_initiation = 0

    def __call__(self, chemin, donnees):
        self.appels.append((chemin, donnees))
        if chemin == "/api/v1/pay":
            return {"tx_reference": "PG-123", "status": self.statut_initiation}
        return {
            "tx_reference": "PG-123",
            "payment_reference": "FLZ-789",
            "status": self.statut_paiement,
        }


@pytest.fixture
def paygate(settings, monkeypatch):
    settings.PAIEMENT_PROVIDER = "apps.portefeuille.paygate.PayGateProvider"
    settings.PAYGATE_AUTH_TOKEN = "jeton-marchand-secret"
    settings.PAYGATE_CALLBACK_SECRET = "cle-callback"
    faux = FauxPayGate()
    monkeypatch.setattr("apps.portefeuille.paygate._appeler", faux)
    return faux


def test_recharge_en_attente_puis_confirmee(utilisateur, paygate):
    ligne = services.recharger(utilisateur, 2000, "mixx", "+22890000001")

    assert ligne.statut == "en_attente"
    assert services.solde(utilisateur).total == 0  # rien n'est crédité avant confirmation
    chemin, envoye = paygate.appels[0]
    assert chemin == "/api/v1/pay"
    assert envoye == {
        "phone_number": "90000001",
        "amount": 2000,
        "description": "Recharge du portefeuille Kovoit",
        "identifier": str(ligne.id),
        "network": "TMONEY",  # Mixx s'appelle encore TMONEY chez PayGate
    }

    paygate.statut_paiement = 0
    assert services.verifier_paiement(utilisateur, ligne.id).statut == "validee"
    assert services.solde(utilisateur).total == 2000
    assert (
        EvenementAudit.objects.filter(action="paiement.confirmer", resultat="succes").count() == 1
    )


def test_le_callback_ne_suffit_pas_a_crediter(api_client, utilisateur, paygate):
    """Un faux callback « payé » est ignoré tant que PayGate ne confirme pas le paiement."""
    ligne = services.recharger(utilisateur, 2000, "flooz")

    api_client.post(f"{CALLBACK}?cle=cle-callback", {"identifier": str(ligne.id), "status": 0})
    assert Transaction.objects.get(id=ligne.id).statut == "en_attente"

    paygate.statut_paiement = 0
    reponse = api_client.post(f"{CALLBACK}?cle=cle-callback", {"identifier": str(ligne.id)})
    assert reponse.status_code == 200
    validee = Transaction.objects.get(id=ligne.id)
    assert (validee.statut, validee.reference_operateur) == ("validee", "FLZ-789")
    # Second callback : pas de double crédit
    api_client.post(f"{CALLBACK}?cle=cle-callback", {"identifier": str(ligne.id)})
    assert services.solde(utilisateur).total == 2000


def test_callback_sans_la_bonne_cle_ignore(api_client, utilisateur, paygate):
    ligne = services.recharger(utilisateur, 2000, "flooz")
    paygate.statut_paiement = 0

    api_client.post(f"{CALLBACK}?cle=mauvaise", {"identifier": str(ligne.id)})

    assert Transaction.objects.get(id=ligne.id).statut == "en_attente"


@pytest.mark.parametrize(("statut", "code"), [(4, "EXPIRE"), (6, "ANNULE")])
def test_paiement_expire_ou_annule(utilisateur, paygate, statut, code):
    ligne = services.recharger(utilisateur, 2000, "flooz")
    paygate.statut_paiement = statut

    assert services.verifier_paiement(utilisateur, ligne.id).statut == "echouee"
    assert services.solde(utilisateur).total == 0
    echec = EvenementAudit.objects.get(action="paiement.confirmer")
    assert (echec.resultat, echec.code_motif) == ("echec", code)


def test_paygate_injoignable(client_de, utilisateur, paygate, monkeypatch):
    from apps.portefeuille.provider import PaiementIndisponible

    def panne(chemin, donnees):
        raise PaiementIndisponible()

    monkeypatch.setattr("apps.portefeuille.paygate._appeler", panne)
    reponse = client_de(utilisateur).post(
        "/api/v1/portefeuille/recharger/", {"montant": 2000, "moyen": "flooz"}
    )

    assert reponse.status_code == 503
    assert Transaction.objects.get().statut == "echouee"


def test_tache_rattrape_les_callbacks_perdus_et_abandonne_apres_le_delai(utilisateur, paygate):
    recente = services.recharger(utilisateur, 1000, "flooz")
    with freeze_time(timezone.now() - timedelta(hours=2)):
        ancienne = services.recharger(utilisateur, 2000, "flooz")

    paygate.statut_paiement = 2
    services.verifier_paiements_en_attente()

    assert Transaction.objects.get(id=recente.id).statut == "en_attente"
    assert Transaction.objects.get(id=ancienne.id).statut == "echouee"
    paygate.statut_paiement = 0
    services.verifier_paiements_en_attente()
    assert Transaction.objects.get(id=recente.id).statut == "validee"


def test_reservation_demande_de_recharger_le_complement(utilisateur, trajet, paygate):
    from apps.kyc.tests.factories import verifier_kyc

    verifier_kyc(utilisateur, "passager")
    with pytest.raises(services.SoldeInsuffisant) as exc:
        demander(utilisateur, trajet)

    assert exc.value.erreurs["recharge_requise"] is True
    assert exc.value.erreurs["complement_a_payer"] == 300
    assert paygate.appels == []  # rien n'est encaissé pendant la réservation


def test_retrait_en_attente_retenu_puis_verse_ou_refuse(passager, admin, paygate):
    ligne = services.retirer(passager, 1000, "flooz")

    assert ligne.statut == "en_attente"
    assert services.solde(passager).disponible == 4000  # retenu : pas de double dépense
    services.traiter_retrait(admin, ligne.id, verse=False)
    assert services.solde(passager).disponible == 5000

    autre = services.retirer(passager, 1000, "mixx")
    services.traiter_retrait(admin, autre.id, verse=True, reference="FLOOZ-VIR-42")
    assert services.solde(passager).total == 4000
    assert EvenementAudit.objects.filter(action="portefeuille.verser").count() == 2
    with pytest.raises(services.SoldeInsuffisant.__mro__[1]):  # Conflit : déjà traité
        services.traiter_retrait(admin, autre.id, verse=True)


def test_le_jeton_marchand_n_est_jamais_journalise(utilisateur, paygate):
    services.recharger(utilisateur, 2000, "flooz")
    paygate.statut_paiement = 0
    services.verifier_paiements_en_attente()

    journal = str(list(EvenementAudit.objects.values()))
    assert "jeton-marchand-secret" not in journal


def test_message_du_retrait_en_attente(client_de, passager, paygate):
    reponse = client_de(passager).post(
        "/api/v1/portefeuille/retirer/", {"montant": 1000, "moyen": "flooz"}
    )

    assert reponse.status_code == 202
    assert "Kovoit effectue le versement" in reponse.json()["message"]


def test_callback_ignore_sans_secret_configure(api_client, utilisateur, paygate, settings):
    settings.PAYGATE_CALLBACK_SECRET = ""
    ligne = services.recharger(utilisateur, 2000, "flooz")
    paygate.statut_paiement = 0

    api_client.post(f"{CALLBACK}?cle=", {"identifier": str(ligne.id)})

    assert Transaction.objects.get(id=ligne.id).statut == "en_attente"
