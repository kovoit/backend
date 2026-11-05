import pytest
from django.core import mail
from django.core.management import CommandError, call_command

from apps.accounts.cgu import CGU_VERSION
from apps.accounts.models import User
from apps.accounts.tests.aides_auth import MOI, connecter
from apps.dashboard.demo import DEMO_MOT_DE_PASSE
from apps.kyc.models import KycDossier
from apps.vehicules.models import Vehicule

pytestmark = pytest.mark.django_db

ACCES = {  # adresse → (peut_reserver, peut_publier)
    "conducteur.verifie@kovoit.test": (True, True),
    "conducteur.attente@kovoit.test": (False, False),
    "passager.verifie@kovoit.test": (True, False),
    "passager.attente@kovoit.test": (False, False),
}
STATUTS = {
    "conducteur.verifie@kovoit.test": {"passager": "verifie", "conducteur": "verifie"},
    "conducteur.attente@kovoit.test": {"passager": "en_attente", "conducteur": "en_attente"},
    "passager.verifie@kovoit.test": {"passager": "verifie"},
    "passager.attente@kovoit.test": {"passager": "en_attente"},
}


def _statuts(email: str) -> dict:
    dossiers = KycDossier.objects.filter(utilisateur__email=email).exclude(statut="non_verifie")
    return {dossier.type: dossier.statut for dossier in dossiers}


def test_seed_comptes_test_etats_connexion_et_back_office(
    settings, capsys, superutilisateur, client_de
):
    settings.DEBUG = True
    mail.outbox.clear()

    call_command("seed_comptes_test")

    sortie = capsys.readouterr().out
    assert all(email in sortie for email in ACCES) and DEMO_MOT_DE_PASSE in sortie
    assert superutilisateur.email in sortie
    assert not mail.outbox  # aucun e-mail réel vers les adresses fictives
    for numero, (email, (reserve, publie)) in enumerate(ACCES.items()):
        compte = User.objects.get(email=email)
        assert compte.email_verifie and compte.cgu_version == CGU_VERSION
        assert compte.photo and compte.profil_complet and compte.telephone.startswith("+228")
        assert _statuts(email) == STATUTS[email]
        reponse = connecter(email, DEMO_MOT_DE_PASSE, ip=f"10.0.1.{numero}")
        assert reponse.status_code == 200
        acces = client_de(compte).get(MOI).json()["reponse"]["etat"]["acces"]
        assert (acces["peut_reserver"], acces["peut_publier"]) == (reserve, publie)
    for email in ("conducteur.verifie@kovoit.test", "conducteur.attente@kovoit.test"):
        assert Vehicule.objects.get(proprietaire__email=email).photo

    liste = client_de(superutilisateur).get("/api/v1/admin/kyc/", {"statut": "en_attente"})
    dossiers = liste.json()["reponse"]["results"]
    en_attente = {(d["utilisateur"]["email"], d["type"]) for d in dossiers}
    assert en_attente == {
        ("conducteur.attente@kovoit.test", "passager"),
        ("conducteur.attente@kovoit.test", "conducteur"),
        ("passager.attente@kovoit.test", "passager"),
    }
    utilisateurs = client_de(superutilisateur).get("/api/v1/admin/utilisateurs/").json()
    emails = {u["email"] for u in utilisateurs["reponse"]["results"]}
    assert set(ACCES) <= emails


def test_seed_comptes_test_relance_sans_doublon_et_remet_l_etat(settings, superutilisateur):
    settings.DEBUG = True
    call_command("seed_comptes_test")
    compte = User.objects.get(email="passager.attente@kovoit.test")
    compte.set_password("autre-chose-123")
    compte.save()
    KycDossier.objects.filter(utilisateur=compte).update(statut="verifie")
    photo = compte.photo.name

    call_command("seed_comptes_test")

    assert User.objects.filter(email__endswith="@kovoit.test").count() == 4
    assert KycDossier.objects.filter(utilisateur__email__endswith="@kovoit.test").count() == 6
    assert Vehicule.objects.filter(proprietaire__email__endswith="@kovoit.test").count() == 2
    compte.refresh_from_db()
    assert compte.check_password(DEMO_MOT_DE_PASSE) and compte.photo.name == photo
    assert _statuts(compte.email) == {"passager": "en_attente"}


def test_seed_comptes_test_refuse_hors_developpement(settings):
    settings.DEBUG = False

    with pytest.raises(CommandError):
        call_command("seed_comptes_test")
