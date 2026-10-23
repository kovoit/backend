"""PayGate Global (Togo) : encaissement Flooz et Mixx (réseau « TMONEY » chez PayGate).

API utilisée (confirmée par le guide d'intégration du compte marchand) :
  POST {PAYGATE_URL}/api/v1/pay     auth_token, phone_number, amount, description,
                                    identifier, network → { tx_reference, status }
       status : 0 transaction enregistrée, 2 jeton invalide, 4 paramètres invalides, 6 doublon
  POST {PAYGATE_URL}/api/v2/status  auth_token, identifier → { tx_reference, payment_reference,
                                    status, datetime, payment_method }
       status : 0 payé, 2 en cours, 4 expiré, 6 annulé
Callback : POST JSON (tx_reference, identifier, payment_reference, amount, datetime, …), non cru.
Le guide ne prévoit pas de versement par API : les retraits sont enregistrés en attente et
versés manuellement par Kovoit (voir le Django admin).
"""

import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

from apps.portefeuille.models import StatutTransaction as S
from apps.portefeuille.provider import PaiementIndisponible, PaiementProvider, Resultat

logger = logging.getLogger(__name__)

RESEAUX = {"flooz": "FLOOZ", "mixx": "TMONEY"}
STATUTS_PAIEMENT = {0: (S.VALIDEE, ""), 2: (S.EN_ATTENTE, ""), 4: (S.ECHOUEE, "EXPIRE"),
                    6: (S.ECHOUEE, "ANNULE")}  # fmt: skip
CODES_INITIATION = {2: "JETON_PAYGATE_INVALIDE", 4: "PARAMETRES_INVALIDES", 6: "DOUBLON"}
DELAI_S = 15


def _appeler(chemin: str, donnees: dict) -> dict:
    """POST JSON vers PayGate. Le jeton d'authentification n'est jamais journalisé."""
    corps = json.dumps({"auth_token": settings.PAYGATE_AUTH_TOKEN, **donnees}).encode()
    requete = urllib.request.Request(
        f"{settings.PAYGATE_URL.rstrip('/')}{chemin}",
        data=corps,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(requete, timeout=DELAI_S) as reponse:  # noqa: S310 — URL de config
            return json.load(reponse)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        logger.warning("PayGate injoignable (%s) : %s", chemin, type(exc).__name__)
        raise PaiementIndisponible() from exc


class PayGateProvider(PaiementProvider):
    asynchrone = True
    versement_automatique = False

    def collecter(self, utilisateur, montant, moyen, telephone, identifiant) -> Resultat:
        reponse = _appeler(
            "/api/v1/pay",
            {
                "phone_number": telephone,
                "amount": montant,
                "description": "Recharge du portefeuille Kovoit",
                "identifier": identifiant,
                "network": RESEAUX[moyen],
            },
        )
        statut = reponse.get("status")
        if statut != 0:
            code = CODES_INITIATION.get(statut, "REFUS_PAYGATE")
            logger.warning("PayGate a refusé l'initiation (%s)", code)
            raise PaiementIndisponible(code=code)
        return Resultat(str(reponse.get("tx_reference", "")), S.EN_ATTENTE)

    def verifier(self, identifiant, reference) -> Resultat:
        reponse = _appeler("/api/v2/status", {"identifier": identifiant})
        statut, code = STATUTS_PAIEMENT.get(reponse.get("status"), (S.EN_ATTENTE, ""))
        operateur = str(reponse.get("payment_reference") or "")
        return Resultat(str(reponse.get("tx_reference") or reference), statut, code, operateur)

    def verser(self, utilisateur, montant, moyen, telephone) -> Resultat:
        return Resultat("", S.EN_ATTENTE, "VERSEMENT_MANUEL")
