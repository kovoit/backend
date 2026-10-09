"""Paiement simulé : aucun argent réel. Un vrai agrégateur (FedaPay, CinetPay…) le remplacera."""

import uuid


class SimulationPaiementProvider:
    def collecter(self, utilisateur, montant: int, moyen: str) -> str:
        """Encaissement Mobile Money simulé (Flooz ou Mixx). Renvoie la référence."""
        return f"SIM-{moyen.upper()}-{uuid.uuid4().hex[:12].upper()}"

    def verser(self, utilisateur, montant: int, moyen: str) -> str:
        """Versement vers Mobile Money (simulé)."""
        return f"SIM-{moyen.upper()}-RET-{uuid.uuid4().hex[:8].upper()}"


provider = SimulationPaiementProvider()
