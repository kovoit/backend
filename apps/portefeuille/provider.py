"""Fournisseurs Mobile Money (Flooz, Mixx), choisis par le réglage `PAIEMENT_PROVIDER`.

Un encaissement renvoie un `Resultat` : validé tout de suite (simulation) ou en attente de la
confirmation du client sur son téléphone (PayGate). Un paiement en attente est ensuite vérifié
auprès du fournisseur (`verifier`), jamais confirmé sur la seule foi d'un callback.
"""

import uuid
from dataclasses import dataclass

from django.conf import settings
from django.utils.module_loading import import_string

from apps.core.exceptions import ErreurMetier
from apps.portefeuille.models import StatutTransaction as S


class PaiementIndisponible(ErreurMetier):
    code = "PAIEMENT_INDISPONIBLE"
    message = "Le paiement Mobile Money est momentanément indisponible. Réessayez plus tard."
    http_status = 503


@dataclass(frozen=True)
class Resultat:
    reference: str
    statut: str  # S.VALIDEE | S.EN_ATTENTE | S.ECHOUEE
    code: str = ""  # motif d'échec du fournisseur (ex. EXPIRE, ANNULE)
    reference_operateur: str = ""  # référence Flooz / Mixx du paiement (support, réclamations)


class PaiementProvider:
    #: True : l'encaissement attend la validation du client (pas de paiement immédiat)
    asynchrone = False
    #: True : les retraits sont versés automatiquement ; False : versement manuel par Kovoit
    versement_automatique = True

    def collecter(self, utilisateur, montant: int, moyen: str, telephone: str, identifiant: str):
        raise NotImplementedError

    def verifier(self, identifiant: str, reference: str) -> Resultat:
        raise NotImplementedError

    def verser(self, utilisateur, montant: int, moyen: str, telephone: str) -> Resultat:
        raise NotImplementedError


class SimulationPaiementProvider(PaiementProvider):
    """Aucun argent réel : tout est validé immédiatement (développement, tests, démo)."""

    def collecter(self, utilisateur, montant, moyen, telephone, identifiant) -> Resultat:
        return Resultat(f"SIM-{moyen.upper()}-{uuid.uuid4().hex[:12].upper()}", S.VALIDEE)

    def verifier(self, identifiant, reference) -> Resultat:
        return Resultat(reference, S.VALIDEE)

    def verser(self, utilisateur, montant, moyen, telephone) -> Resultat:
        return Resultat(f"SIM-{moyen.upper()}-RET-{uuid.uuid4().hex[:8].upper()}", S.VALIDEE)


def get_provider() -> PaiementProvider:
    return import_string(settings.PAIEMENT_PROVIDER)()
