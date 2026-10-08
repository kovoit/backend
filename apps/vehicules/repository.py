from apps.core.repository import BaseRepository
from apps.vehicules.models import Vehicule


class VehiculeRepository(BaseRepository[Vehicule]):
    model = Vehicule
    message_introuvable = "Véhicule introuvable."

    def de(self, proprietaire):
        return self.filter(proprietaire=proprietaire).order_by("cree_le")

    def get_de(self, proprietaire, vehicule_id) -> Vehicule:
        """Véhicule appartenant à `proprietaire`, sinon 404 (pas de fuite d'information)."""
        return self._get(self.queryset(), pk=vehicule_id, proprietaire=proprietaire)

    def immatriculation_prise(self, immatriculation: str, sauf_id=None) -> bool:
        return self.filter(immatriculation=immatriculation).exclude(pk=sauf_id).exists()

    def a_des_trajets(self, vehicule: Vehicule) -> bool:
        return vehicule.trajets.exists()


vehicule_repository = VehiculeRepository()
