from datetime import timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.kyc.tests.factories import verifier_kyc
from apps.notifications.push import FakePushSender
from apps.portefeuille import services as portefeuille
from apps.reservations import services as reservations
from apps.trajets import services as trajets
from apps.vehicules.tests.factories import VehiculeFactory
from kovoit.celery import app as celery_app

# Lieux de Lomé utilisés dans les tests
ADIDOGOME = {"lat": 6.1745, "lng": 1.1690}
CARREFOUR_ADIDOGOME = {"lat": 6.1750, "lng": 1.1700, "libelle": "Carrefour Adidogomé"}
GRAND_MARCHE = {"lat": 6.1300, "lng": 1.2220}


@pytest.fixture(autouse=True)
def reglages_de_test(settings, tmp_path):
    """Cache en mémoire, hachage rapide, Celery synchrone, services externes simulés."""
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.PRIVATE_MEDIA_ROOT = str(tmp_path / "prive")
    settings.MEDIA_ROOT = str(tmp_path / "media")
    settings.ROUTAGE_PROVIDER = "apps.routage.providers.FakeRoutingProvider"
    settings.NOTIFICATIONS_PUSH_SENDER = "apps.notifications.push.FakePushSender"
    # Namespace « CELERY » : les clés de configuration portent le préfixe
    celery_app.conf.update(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    FakePushSender.envoyes = []
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def client_de():
    """Fabrique : client API authentifié pour un utilisateur donné."""

    def fabriquer(utilisateur):
        client = APIClient()
        client.force_authenticate(utilisateur)
        return client

    return fabriquer


@pytest.fixture
def utilisateur(db):
    return UserFactory()


@pytest.fixture
def admin(db):
    return UserFactory(is_staff=True, prenom="Admin")


@pytest.fixture
def client_utilisateur(client_de, utilisateur):
    return client_de(utilisateur)


@pytest.fixture
def client_admin(client_de, admin):
    return client_de(admin)


@pytest.fixture
def passager(db):
    """Passager KYC vérifié avec 5 000 F sur son portefeuille."""
    utilisateur = UserFactory(prenom="Afi")
    verifier_kyc(utilisateur, "passager")
    portefeuille.recharger(utilisateur, 5000, "flooz")
    return utilisateur


@pytest.fixture
def conducteur(db):
    """Conducteur KYC vérifié avec une voiture de 5 places."""
    utilisateur = UserFactory(prenom="Kodjo")
    verifier_kyc(utilisateur, "conducteur")
    VehiculeFactory(proprietaire=utilisateur, nb_places=5)
    return utilisateur


def publier_trajet(conducteur, depart_dans=timedelta(hours=2), places=3):
    return trajets.publier(
        conducteur,
        vehicule_id=conducteur.vehicules.first().id,
        depart_lat=ADIDOGOME["lat"],
        depart_lng=ADIDOGOME["lng"],
        depart_libelle="Adidogomé",
        arrivee_lat=GRAND_MARCHE["lat"],
        arrivee_lng=GRAND_MARCHE["lng"],
        arrivee_libelle="Grand Marché",
        depart_le=timezone.now() + depart_dans,
        places=places,
        points=[CARREFOUR_ADIDOGOME],
    )


def demander(passager, trajet):
    return reservations.demander_place(
        passager,
        trajet_id=trajet.id,
        point_id=trajet.points.first().id,
        arrivee_lat=GRAND_MARCHE["lat"] + 0.001,
        arrivee_lng=GRAND_MARCHE["lng"],
        arrivee_libelle="Grand Marché",
    )


@pytest.fixture
def trajet(conducteur):
    return publier_trajet(conducteur)


@pytest.fixture
def reservation(passager, trajet):
    """Réservation « demandée »."""
    return demander(passager, trajet)


@pytest.fixture
def reservation_acceptee(conducteur, reservation):
    return reservations.accepter(conducteur, reservation.id)
