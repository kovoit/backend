"""Suppression du compte par l'utilisateur : anonymisation, refus si quelque chose est en cours."""

import pytest

from apps.accounts.models import User
from apps.audit.models import EvenementAudit
from apps.kyc.models import KycPiece
from apps.kyc.tests.factories import fichier_png
from apps.notifications import services as notifications

pytestmark = pytest.mark.django_db

URL = "/api/v1/moi/supprimer/"


def test_compte_anonymise_pieces_et_notifications_effacees(client_de, utilisateur):
    from apps.kyc import services as kyc

    kyc.ajouter_piece(utilisateur, "passager", "identite", fichier_png())
    notifications.enregistrer_appareil(utilisateur, "jeton-x", "android")
    notifications.notifier(utilisateur, "Titre", "Message")
    email, telephone = utilisateur.email, utilisateur.telephone

    reponse = client_de(utilisateur).post(URL, {"confirmation": "supprimer"}, format="json")

    assert reponse.status_code == 200
    compte = User.objects.get(pk=utilisateur.pk)
    assert not compte.is_active and not compte.has_usable_password()
    assert compte.email != email and compte.email.endswith("@supprime.invalid")
    assert (compte.nom, compte.prenom, compte.telephone) == ("Compte", "supprimé", "")
    assert not KycPiece.objects.exists()
    assert not compte.notifications.exists() and not compte.appareils.exists()
    evenement = EvenementAudit.objects.get(action="compte.supprimer")
    assert email not in str(evenement.details) and telephone not in str(evenement.details)


def test_confirmation_obligatoire(client_de, utilisateur):
    reponse = client_de(utilisateur).post(URL, {"confirmation": "oui"}, format="json")

    assert reponse.status_code == 403
    assert reponse.json()["reponse"]["code"] == "CONFIRMATION_REQUISE"
    assert User.objects.get(pk=utilisateur.pk).is_active


def test_refusee_avec_une_reservation_ou_de_l_argent(client_de, passager, reservation):
    reponse = client_de(passager).post(URL, {"confirmation": "SUPPRIMER"}, format="json")

    assert reponse.status_code == 409
    raisons = reponse.json()["reponse"]["erreurs"]["raisons"]
    assert any("réservation" in r for r in raisons)
    assert any("portefeuille" in r for r in raisons)
    assert User.objects.get(pk=passager.pk).is_active


def test_refusee_avec_un_trajet_publie(client_de, conducteur, trajet):
    reponse = client_de(conducteur).post(URL, {"confirmation": "SUPPRIMER"}, format="json")

    assert reponse.status_code == 409
    assert any("trajet" in r for r in reponse.json()["reponse"]["erreurs"]["raisons"])


def test_plus_de_connexion_apres_suppression(api_client, client_de, utilisateur):
    from django.core import mail

    email = utilisateur.email
    client_de(utilisateur).post(URL, {"confirmation": "SUPPRIMER"}, format="json")

    # Le même email peut recréer un compte neuf, sans lien avec l'ancien
    api_client.post("/api/v1/auth/otp/demander/", {"email": email}, format="json")
    assert mail.outbox
    assert User.objects.filter(email=email).count() == 0


def test_un_admin_ne_se_supprime_pas_depuis_l_app(client_admin):
    reponse = client_admin.post(URL, {"confirmation": "SUPPRIMER"}, format="json")

    assert reponse.json()["reponse"]["code"] == "COMPTE_ADMIN"
