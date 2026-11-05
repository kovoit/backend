"""F-053 : abandon (délai dépassé) et confirmation PayGate en même temps sur la même recharge.

Les deux chemins verrouillent la ligne (select_for_update) et ne la modifient que si elle est
encore en attente : une seule issue, jamais « validée » puis « échouée ».
"""

import threading

import pytest
from django.db import connection

from apps.audit.models import EvenementAudit
from apps.portefeuille import services
from apps.portefeuille.models import Transaction
from apps.portefeuille.services import mobile_money

pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)


def _en_parallele(*fonctions):
    barriere = threading.Barrier(len(fonctions))
    erreurs = []

    def lancer(fonction):
        try:
            barriere.wait(timeout=10)
            fonction()
        except Exception as exc:  # remonté au test principal
            erreurs.append(exc)
        finally:
            connection.close()  # chaque thread a sa propre connexion PostgreSQL

    threads = [threading.Thread(target=lancer, args=(f,)) for f in fonctions]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert not any(thread.is_alive() for thread in threads)
    return erreurs


@pytest.mark.parametrize("essai", range(5))
def test_abandon_et_confirmation_simultanes_une_seule_issue(utilisateur, paygate, essai):
    ligne = services.recharger(utilisateur, 2000, "flooz")
    paygate.statut_paiement = 0  # PayGate confirme le paiement pendant l'abandon

    erreurs = _en_parallele(
        lambda: mobile_money._abandonner(ligne.id),
        lambda: mobile_money._actualiser(ligne.id, systeme=True),
    )

    assert erreurs == []
    confirmation = EvenementAudit.objects.get(action="paiement.confirmer")  # une seule
    statut = Transaction.objects.get(id=ligne.id).statut
    if statut == "validee":  # la confirmation a gagné : l'abandon n'a rien réécrit
        assert (confirmation.resultat, confirmation.code_motif) == ("succes", "")
        assert services.solde(utilisateur).total == 2000
    else:  # l'abandon a gagné : la confirmation tardive n'a rien crédité
        assert statut == "echouee"
        assert (confirmation.resultat, confirmation.code_motif) == ("echec", "DELAI_DEPASSE")
        assert services.solde(utilisateur).total == 0
