"""F-003 (D-62) : le fournisseur Mobile Money reçoit toujours 8 chiffres, quelle que soit la
saisie ou la forme du profil (+228XXXXXXXX) ; la ligne du journal aussi. Un numéro non mobile
est refusé (400 TELEPHONE_INVALIDE) sans appel au fournisseur."""

import pytest

from apps.accounts.models import User
from apps.accounts.tests.factories import UserFactory
from apps.kyc.tests.factories import verifier_kyc
from apps.portefeuille.models import Transaction
from apps.portefeuille.provider import SimulationPaiementProvider
from apps.portefeuille.services.commun import ecrire
from apps.reservations.models import StatutReservation
from conftest import GRAND_MARCHE

pytestmark = pytest.mark.django_db

RECHARGER = "/api/v1/portefeuille/recharger/"
RETIRER = "/api/v1/portefeuille/retirer/"


@pytest.fixture
def afi():
    return UserFactory(prenom="Afi", telephone="+22890112233")


def _poster(client_de, compte, chemin=RECHARGER, **extra):
    return client_de(compte).post(chemin, {"montant": 2000, "moyen": "flooz", **extra})


def _numeros_envoyes(paygate) -> list[str]:
    return [
        donnees["phone_number"] for chemin, donnees in paygate.appels if chemin == "/api/v1/pay"
    ]


def test_recharge_sans_saisie_envoie_les_8_chiffres_du_profil(client_de, afi, paygate):
    reponse = _poster(client_de, afi)

    assert reponse.status_code == 202
    assert _numeros_envoyes(paygate) == ["90112233"]
    assert Transaction.objects.get(utilisateur=afi).telephone == "90112233"


@pytest.mark.parametrize("saisie", ["70-11-22-33", "+228 70 11 22 33", "(228) 70.11.22.33"])
def test_recharge_avec_saisie_libre_acceptee(client_de, afi, paygate, saisie):
    reponse = _poster(client_de, afi, telephone=saisie)

    assert reponse.status_code == 202
    assert _numeros_envoyes(paygate) == ["70112233"]
    assert Transaction.objects.get(utilisateur=afi).telephone == "70112233"


@pytest.mark.parametrize("chemin", [RECHARGER, RETIRER])
def test_numero_fixe_refuse_sans_appel_ni_ligne(client_de, afi, paygate, chemin):
    ecrire(afi, "recharge", 3000, reference="SIM-AVANT")

    reponse = _poster(client_de, afi, chemin, telephone="22 11 22 33")

    assert reponse.status_code == 400
    corps = reponse.json()
    assert (corps["statut"], corps["reponse"]["code"]) == ("failed", "TELEPHONE_INVALIDE")
    assert corps["message"] and corps["reponse"]["erreurs"]["telephone"] == [corps["message"]]
    assert paygate.appels == []
    assert Transaction.objects.filter(utilisateur=afi).count() == 1  # la recharge initiale


def test_profil_illisible_et_aucune_saisie_refuse(client_de, afi, paygate):
    User.objects.filter(pk=afi.pk).update(telephone="22112233")
    afi.refresh_from_db()

    reponse = _poster(client_de, afi)

    assert (reponse.status_code, reponse.json()["reponse"]["code"]) == (400, "TELEPHONE_INVALIDE")
    assert paygate.appels == []


def test_retrait_enregistre_les_8_chiffres(client_de, afi, paygate):
    ecrire(afi, "recharge", 3000, reference="SIM-AVANT")

    reponse = _poster(client_de, afi, RETIRER, telephone="90-11-22-33")

    assert reponse.status_code == 202
    assert Transaction.objects.get(utilisateur=afi, type="retrait").telephone == "90112233"


def test_retrait_simule_verse_aux_8_chiffres_du_profil(client_de, afi, settings, monkeypatch):
    settings.PAIEMENT_PROVIDER = "apps.portefeuille.provider.SimulationPaiementProvider"
    ecrire(afi, "recharge", 3000, reference="SIM-AVANT")
    numeros = []
    original = SimulationPaiementProvider.verser

    def verser(self, utilisateur, montant, moyen, telephone):
        numeros.append(telephone)
        return original(self, utilisateur, montant, moyen, telephone)

    monkeypatch.setattr(SimulationPaiementProvider, "verser", verser)

    assert _poster(client_de, afi, RETIRER).status_code == 201
    assert numeros == ["90112233"]
    assert Transaction.objects.get(utilisateur=afi, type="retrait").telephone == "90112233"


# Réservation : complément payé par Flooz pendant la demande (simulation, paiement immédiat)


@pytest.fixture
def numeros_collectes(settings, monkeypatch):
    settings.PAIEMENT_PROVIDER = "apps.portefeuille.provider.SimulationPaiementProvider"
    numeros = []
    original = SimulationPaiementProvider.collecter

    def collecter(self, utilisateur, montant, moyen, telephone, identifiant):
        numeros.append(telephone)
        return original(self, utilisateur, montant, moyen, telephone, identifiant)

    monkeypatch.setattr(SimulationPaiementProvider, "collecter", collecter)
    return numeros


def _reserver(passager, trajet):
    from apps.reservations import services as reservations

    return reservations.demander_place(
        passager,
        trajet_id=trajet.id,
        point_id=trajet.points.first().id,
        arrivee_lat=GRAND_MARCHE["lat"],
        arrivee_lng=GRAND_MARCHE["lng"],
        moyen_paiement="flooz",
    )


def test_reservation_le_fournisseur_recoit_8_chiffres(afi, trajet, numeros_collectes):
    verifier_kyc(afi, "passager")

    reservation = _reserver(afi, trajet)

    assert reservation.complement_paye > 0
    assert numeros_collectes == ["90112233"]


@pytest.mark.parametrize("ancien", ["22112233", "+33612345678", ""])
def test_reservation_avec_profil_illisible_n_echoue_pas(afi, trajet, numeros_collectes, ancien):
    User.objects.filter(pk=afi.pk).update(telephone=ancien)
    afi.refresh_from_db()
    verifier_kyc(afi, "passager")

    reservation = _reserver(afi, trajet)

    assert reservation.statut == StatutReservation.DEMANDEE
    assert numeros_collectes == [ancien]  # transmis tel quel, sans erreur
