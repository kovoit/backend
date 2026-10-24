"""Migration 0002 : anciennes valeurs de départ remplacées, valeurs d'un admin conservées."""

from importlib import import_module

import pytest
from django.apps import apps

from apps.parametres.models import Parametre

pytestmark = pytest.mark.django_db

migration = import_module("apps.parametres.migrations.0002_tarification_validee")


def _poser(cle, valeur):
    Parametre.objects.update_or_create(cle=cle, defaults={"valeur": valeur})


def test_anciennes_valeurs_remplacees_valeurs_modifiees_conservees():
    _poser("consommation_voiture_l_100km", 7.0)
    _poser("consommation_moto_l_100km", "2.5")
    _poser("cout_horaire_conducteur", 0)
    _poser("entretien_voiture_par_km", 20)  # changée par un administrateur
    Parametre.objects.filter(cle="entretien_moto_par_km").delete()  # absente : rien créé

    migration.appliquer(apps, None)

    valeur = {p.cle: p.valeur for p in Parametre.objects.all()}
    assert valeur["consommation_voiture_l_100km"] == 8.0
    assert valeur["consommation_moto_l_100km"] == 3.0
    assert valeur["cout_horaire_conducteur"] == 300
    assert valeur["entretien_voiture_par_km"] == 20
    assert "entretien_moto_par_km" not in valeur
