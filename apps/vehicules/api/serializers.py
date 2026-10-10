from rest_framework import serializers

from apps.vehicules.models import Vehicule


class VehiculeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicule
        fields = [
            "id",
            "type_vehicule",
            "marque",
            "modele",
            "couleur",
            "immatriculation",
            "nb_places",
            "photo",
            "cree_le",
        ]
        read_only_fields = ["id", "cree_le"]
        # L'unicité est vérifiée par le service (message et code d'erreur métier)
        extra_kwargs = {"immatriculation": {"validators": []}}


class VehiculeResumeSerializer(serializers.ModelSerializer):
    """Véhicule tel que vu par un passager (photo et immatriculation visibles avant la prise)."""

    class Meta:
        model = Vehicule
        fields = [
            "id",
            "type_vehicule",
            "marque",
            "modele",
            "couleur",
            "immatriculation",
            "nb_places",
            "photo",
        ]
