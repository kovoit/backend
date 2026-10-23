"""Détail du prix d'un trajet (instantané de apps/tarification/calcul.py) exposé à l'API.

Montants des postes de coût : chaînes décimales (2 décimales) ; prix et montants payés :
entiers en F CFA. Seule source de vérité : le backend.
"""

from rest_framework import serializers

DECIMAL = {"max_digits": 12, "decimal_places": 3, "coerce_to_string": True}


class ParametresTarifSerializer(serializers.Serializer):
    prix_carburant_litre = serializers.DecimalField(**DECIMAL)
    consommation_l_100km = serializers.DecimalField(**DECIMAL)
    source_consommation = serializers.CharField(help_text="vehicule ou reference_<type>")
    majoration_charge_par_passager_pct = serializers.DecimalField(**DECIMAL)
    cout_horaire_conducteur = serializers.DecimalField(**DECIMAL)
    entretien_par_km = serializers.DecimalField(**DECIMAL)
    taux_commission_pct = serializers.DecimalField(**DECIMAL)
    arrondi_prix_fcfa = serializers.IntegerField()
    prix_minimum_place = serializers.IntegerField()


class TarificationSerializer(serializers.Serializer):
    formule_version = serializers.CharField()
    type_vehicule = serializers.CharField()
    distance_km = serializers.DecimalField(**DECIMAL)
    duree_min = serializers.IntegerField()
    source_itineraire = serializers.CharField(help_text="routage ou estimation")
    passagers_prevus = serializers.IntegerField(help_text="Base du partage : places proposées")
    consommation_retenue_l_100km = serializers.DecimalField(**DECIMAL)
    carburant_litres = serializers.DecimalField(**DECIMAL)
    cout_carburant = serializers.DecimalField(**DECIMAL)
    cout_temps = serializers.DecimalField(**DECIMAL)
    cout_entretien = serializers.DecimalField(**DECIMAL)
    cout_total = serializers.DecimalField(**DECIMAL)
    part_conducteur = serializers.DecimalField(**DECIMAL)
    contribution_passagers = serializers.DecimalField(**DECIMAL)
    montant_brut_passagers = serializers.DecimalField(**DECIMAL)
    prix_place = serializers.IntegerField()
    commission_place = serializers.IntegerField()
    net_conducteur_place = serializers.IntegerField()
    total_paye_passagers = serializers.IntegerField(help_text="Si toutes les places sont prises")
    commission_kovoit = serializers.IntegerField(help_text="Si toutes les places sont prises")
    net_conducteur = serializers.IntegerField(help_text="Si toutes les places sont prises")
    parametres = ParametresTarifSerializer()
