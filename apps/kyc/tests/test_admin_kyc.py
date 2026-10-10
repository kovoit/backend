import pytest
from freezegun import freeze_time

from apps.accounts.tests.factories import UserFactory
from apps.kyc import services
from apps.kyc.models import KycConsultation
from apps.kyc.tests.factories import fichier_png
from apps.vehicules.tests.factories import VehiculeFactory

pytestmark = pytest.mark.django_db

URL = "/api/v1/admin/kyc/"


def _soumettre(utilisateur, type_dossier="passager"):
    pieces = ["identite", "selfie"]
    if type_dossier == "conducteur":
        pieces += ["permis", "carte_grise", "photo_vehicule"]
    for piece in pieces:
        services.ajouter_piece(utilisateur, type_dossier, piece, fichier_png())
    return services.soumettre(utilisateur, type_dossier)


def test_file_d_attente_plus_anciens_d_abord(client_admin):
    with freeze_time("2026-10-02 09:00"):
        recent = _soumettre(UserFactory(nom="Recent"))
    with freeze_time("2026-10-01 09:00"):
        ancien = _soumettre(UserFactory(nom="Ancien"))

    lignes = client_admin.get(URL, {"statut": "en_attente"}).json()["reponse"]["results"]

    assert [ligne["id"] for ligne in lignes] == [str(ancien.id), str(recent.id)]


@pytest.mark.parametrize("terme", ["lawson", "+22890000042", "afi.lawson"])
def test_recherche_sur_le_demandeur(client_admin, terme):
    cible = UserFactory(prenom="Afi", nom="Lawson", email="afi.lawson@exemple.tg")
    cible.telephone = "+22890000042"
    cible.save()
    _soumettre(cible)
    _soumettre(UserFactory())

    lignes = client_admin.get(URL, {"recherche": terme}).json()["reponse"]["results"]

    assert [ligne["utilisateur"]["id"] for ligne in lignes] == [str(cible.id)]


def test_detail_conducteur_avec_vehicule_et_admin(client_admin, admin):
    conducteur = UserFactory()
    VehiculeFactory(proprietaire=conducteur, nb_places=5)
    dossier = _soumettre(conducteur, "conducteur")
    services.valider(dossier.id, admin)

    detail = client_admin.get(f"{URL}{dossier.id}/").json()["reponse"]

    assert detail["traite_par"] == {"id": str(admin.id), "nom": admin.nom, "prenom": "Admin"}
    assert detail["vehicule"]["nb_places"] == 5
    assert len(detail["pieces"]) == 5


def test_detail_passager_sans_vehicule(client_admin):
    dossier = _soumettre(UserFactory())

    detail = client_admin.get(f"{URL}{dossier.id}/").json()["reponse"]

    assert detail["vehicule"] is None
    assert detail["traite_par"] is None


def test_rejet_motif_trop_court(client_admin):
    dossier = _soumettre(UserFactory())

    reponse = client_admin.post(f"{URL}{dossier.id}/rejeter/", {"motif": "Flou"}, format="json")

    assert reponse.status_code == 400
    assert "motif" in reponse.json()["reponse"]["erreurs"]


def test_fichier_de_piece_jamais_mis_en_cache(client_admin, admin):
    dossier = _soumettre(UserFactory())
    piece = dossier.pieces.first()

    reponse = client_admin.get(f"{URL}pieces/{piece.id}/fichier/")

    assert reponse.status_code == 200
    assert reponse["Cache-Control"] == "no-store, private"
    assert reponse["X-Content-Type-Options"] == "nosniff"
    assert reponse["Content-Type"] == "image/png"
    assert KycConsultation.objects.filter(piece=piece, admin=admin).count() == 1
