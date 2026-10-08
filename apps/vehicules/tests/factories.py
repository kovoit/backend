import factory

from apps.accounts.tests.factories import UserFactory
from apps.vehicules.models import Vehicule


class VehiculeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Vehicule

    proprietaire = factory.SubFactory(UserFactory)
    type_vehicule = "voiture"
    marque = "Toyota"
    modele = "Corolla"
    couleur = "Grise"
    immatriculation = factory.Sequence(lambda n: f"TG{n:04d}AB")
    nb_places = 5
