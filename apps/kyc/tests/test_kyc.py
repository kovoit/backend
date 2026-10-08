import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.exceptions import ActionInterdite, DonneesInvalides
from apps.kyc import services
from apps.kyc.models import KycConsultation, StatutKyc
from apps.kyc.tests.factories import fichier_png

pytestmark = pytest.mark.django_db


def deposer(utilisateur, type_dossier, *pieces):
    for piece in pieces:
        services.ajouter_piece(utilisateur, type_dossier, piece, fichier_png())


def test_mes_dossiers_cree_les_deux_dossiers(utilisateur):
    dossiers = services.mes_dossiers(utilisateur)

    assert {d.type for d in dossiers} == {"passager", "conducteur"}
    assert all(d.statut == StatutKyc.NON_VERIFIE for d in dossiers)


def test_soumission_passager_complete(utilisateur):
    deposer(utilisateur, "passager", "identite", "selfie")

    dossier = services.soumettre(utilisateur, "passager")

    assert dossier.statut == StatutKyc.EN_ATTENTE
    assert dossier.soumis_le is not None


def test_soumission_incomplete_liste_les_pieces_manquantes(utilisateur):
    deposer(utilisateur, "conducteur", "identite")

    with pytest.raises(services.DossierIncomplet) as exc:
        services.soumettre(utilisateur, "conducteur")

    manquantes = exc.value.erreurs["pieces_manquantes"]
    assert "permis" in manquantes and "carte_grise_ou_assurance" in manquantes


def test_conducteur_carte_grise_ou_assurance_suffit(utilisateur):
    deposer(
        utilisateur, "conducteur", "identite", "selfie", "permis", "photo_vehicule", "assurance"
    )

    assert services.soumettre(utilisateur, "conducteur").statut == StatutKyc.EN_ATTENTE


def test_profil_incomplet_bloque_la_soumission(utilisateur):
    utilisateur.telephone = ""
    deposer(utilisateur, "passager", "identite", "selfie")

    with pytest.raises(ActionInterdite):
        services.soumettre(utilisateur, "passager")


@pytest.mark.parametrize(
    ("type_piece", "fichier"),
    [
        ("permis", fichier_png()),  # pas demandé pour un passager
        ("identite", fichier_png(taille=6 * 1024 * 1024)),  # trop gros
        ("identite", SimpleUploadedFile("x.gif", b"GIF89a", content_type="image/gif")),
    ],
)
def test_piece_refusee(utilisateur, type_piece, fichier):
    with pytest.raises(DonneesInvalides):
        services.ajouter_piece(utilisateur, "passager", type_piece, fichier)


def test_type_de_dossier_inconnu(utilisateur):
    with pytest.raises(DonneesInvalides):
        services.ajouter_piece(utilisateur, "pilote", "identite", fichier_png())


def test_dossier_en_attente_non_modifiable(utilisateur):
    deposer(utilisateur, "passager", "identite", "selfie")
    services.soumettre(utilisateur, "passager")

    with pytest.raises(services.DossierNonModifiable):
        deposer(utilisateur, "passager", "selfie")


def test_validation_et_rejet_par_l_admin(utilisateur, admin):
    deposer(utilisateur, "passager", "identite", "selfie")
    dossier = services.soumettre(utilisateur, "passager")

    with pytest.raises(DonneesInvalides):
        services.rejeter(dossier.id, admin, "  ")
    rejete = services.rejeter(dossier.id, admin, "Selfie flou")
    assert rejete.statut == StatutKyc.REJETE and rejete.motif_rejet == "Selfie flou"

    deposer(utilisateur, "passager", "selfie")  # un dossier rejeté peut être corrigé
    services.soumettre(utilisateur, "passager")
    valide = services.valider(dossier.id, admin)
    assert valide.statut == StatutKyc.VERIFIE
    assert services.est_verifie(utilisateur, "passager")


def test_api_parcours_kyc(client_utilisateur, client_admin, utilisateur):
    for piece in ("identite", "selfie"):
        reponse = client_utilisateur.post(
            "/api/v1/kyc/passager/pieces/",
            {"type_piece": piece, "fichier": fichier_png()},
            format="multipart",
        )
        assert reponse.status_code == 201
    reponse = client_utilisateur.post("/api/v1/kyc/passager/soumettre/")
    assert reponse.json()["reponse"]["statut"] == "en_attente"
    dossier_id = reponse.json()["reponse"]["id"]

    liste = client_admin.get("/api/v1/admin/kyc/", {"statut": "en_attente"}).json()
    assert liste["reponse"]["count"] == 1
    detail = client_admin.get(f"/api/v1/admin/kyc/{dossier_id}/").json()["reponse"]
    piece_id = detail["pieces"][0]["id"]

    fichier = client_admin.get(f"/api/v1/admin/kyc/pieces/{piece_id}/fichier/")
    assert fichier.status_code == 200
    assert KycConsultation.objects.filter(piece_id=piece_id).count() == 1

    reponse = client_admin.post(f"/api/v1/admin/kyc/{dossier_id}/valider/")
    assert reponse.json()["reponse"]["statut"] == "verifie"
    statuts = client_utilisateur.get("/api/v1/moi/").json()["reponse"]["kyc"]
    assert statuts == {"passager": "verifie", "conducteur": "non_verifie"}


def test_une_piece_n_a_pas_d_url_publique(utilisateur):
    dossier = services.ajouter_piece(utilisateur, "passager", "identite", fichier_png())
    piece = dossier.pieces.get()

    with pytest.raises(ValueError):
        _ = piece.fichier.url


def test_utilisateur_non_admin_ne_voit_pas_les_pieces(client_utilisateur, utilisateur):
    dossier = services.ajouter_piece(utilisateur, "passager", "identite", fichier_png())

    reponse = client_utilisateur.get(f"/api/v1/admin/kyc/pieces/{dossier.pieces.get().id}/fichier/")

    assert reponse.status_code == 403
