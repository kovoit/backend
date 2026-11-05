"""Tracé de la route d'un trajet exposé à l'API (affichage sur la carte, jamais dans le prix)."""

from rest_framework import serializers


class TraceSerializer(serializers.Serializer):
    source = serializers.ChoiceField(
        choices=["routage", "estimation"],
        help_text="routage : itinéraire par la route ; estimation : service indisponible, "
        "segments droits départ → points de prise en charge → arrivée",
    )
    points = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField(), min_length=2, max_length=2),
        min_length=2,
        help_text="Paires [lat, lng] (5 décimales), du départ à l'arrivée via les points de "
        "prise en charge dans l'ordre",
    )
