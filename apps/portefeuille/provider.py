"""Paiement simulé : aucun argent réel. Un vrai agrégateur (FedaPay, CinetPay…) le remplacera."""

import uuid


class SimulationPaiementProvider:
    def collecter(self, utilisateur, montant: int) -> str:
        """Recharge (Mobile Money simulé). Renvoie la référence de l'opération."""
        return f"SIM-RCH-{uuid.uuid4().hex[:12].upper()}"

    def verser(self, utilisateur, montant: int) -> str:
        """Retrait vers Mobile Money (simulé)."""
        return f"SIM-RET-{uuid.uuid4().hex[:12].upper()}"


provider = SimulationPaiementProvider()
