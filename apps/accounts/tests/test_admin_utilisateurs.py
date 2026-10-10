import pytest

from apps.accounts.models import StatutCompte
from apps.accounts.services import suspendre
from apps.confiance import services as confiance
from apps.kyc.models import KycDossier
from apps.reservations import services as reservations
from apps.reservations.code_depart import calculer_code
from apps.reservations.models import StatutReservation
from apps.trajets.services import terminer

pytestmark = pytest.mark.django_db

URL = "/api/v1/admin/utilisateurs/"
MOTIF = "Comportement dangereux signalé par deux passagers."


def _fiche(client, utilisateur):
    return client.get(f"{URL}{utilisateur.id}/").json()["reponse"]


def test_liste_avec_kyc_et_fiabilite(client_admin, passager, conducteur, reservation):
    lignes = client_admin.get(URL).json()["reponse"]["results"]
    par_id = {ligne["id"]: ligne for ligne in lignes}

    ligne = par_id[str(passager.id)]
    assert ligne["kyc"] == {"passager": "verifie", "conducteur": "non_verifie"}
    assert ligne["fiabilite_pct"] == 100
    assert "is_staff" not in ligne
    # Sans aucune réservation sur la période : rien à mesurer
    sans_reservation = next(ligne for ligne in lignes if ligne["prenom"] == "Admin")
    assert sans_reservation["fiabilite_pct"] is None


def test_liste_filtre_recherche_et_statut(client_admin, passager, conducteur):
    suspendre(passager, 7, MOTIF)

    suspendus = client_admin.get(URL, {"statut": "suspendu"}).json()["reponse"]
    trouves = client_admin.get(URL, {"recherche": conducteur.telephone}).json()["reponse"]

    assert [u["id"] for u in suspendus["results"]] == [str(passager.id)]
    assert [u["id"] for u in trouves["results"]] == [str(conducteur.id)]


def test_fiche_complete(client_admin, passager, conducteur, reservation_acceptee):
    reservations.saisir_code(
        conducteur, reservation_acceptee.id, calculer_code(reservation_acceptee)
    )
    terminer(conducteur, reservation_acceptee.trajet_id)
    reservations.confirmer_arrivee(passager, reservation_acceptee.id)
    confiance.noter(passager, reservation_acceptee.id, 4, "Conduite prudente.")
    nb_dossiers = KycDossier.objects.count()

    fiche = _fiche(client_admin, conducteur)

    assert fiche["fiabilite"] == {
        "pct": 100,
        "periode_j": 30,
        "reservations": 1,
        "annulations_tardives": 0,
        "absences": 0,
    }
    assert fiche["note_moyenne"] == 4.0
    assert fiche["nombre_notes"] == 1
    assert fiche["notes_recues"][0]["auteur"] == {"prenom": "Afi", "nom": "Amegah"}
    assert fiche["notes_recues"][0]["commentaire"] == "Conduite prudente."
    assert [d["type"] for d in fiche["dossiers_kyc"]] == ["conducteur"]
    assert fiche["vehicule"]["immatriculation"]
    # La consultation ne crée pas de dossier KYC vide
    assert KycDossier.objects.count() == nb_dossiers


def test_suspension_motif_obligatoire(client_admin, passager):
    reponse = client_admin.post(f"{URL}{passager.id}/suspendre/", {"jours": 7}, format="json")

    assert reponse.status_code == 400
    assert "motif" in reponse.json()["reponse"]["erreurs"]


def test_suspension_annule_et_compte_les_reservations(client_admin, passager, reservation):
    reponse = client_admin.post(
        f"{URL}{passager.id}/suspendre/", {"motif": MOTIF, "jours": None}, format="json"
    )

    corps = reponse.json()["reponse"]
    assert reponse.status_code == 200
    assert corps["reservations_annulees"] == 1
    assert corps["utilisateur"]["statut_compte"] == "suspendu"
    assert corps["utilisateur"]["motif_suspension"] == MOTIF
    assert corps["utilisateur"]["suspendu_jusqu_au"] is None
    reservation.refresh_from_db()
    assert reservation.statut == StatutReservation.ANNULEE


def test_suspension_conducteur_compte_les_reservations_de_ses_trajets(
    client_admin, conducteur, reservation_acceptee
):
    reponse = client_admin.post(
        f"{URL}{conducteur.id}/suspendre/", {"motif": MOTIF, "jours": 30}, format="json"
    )

    assert reponse.json()["reponse"]["reservations_annulees"] == 1


def test_suspension_deja_suspendu(client_admin, passager):
    suspendre(passager, 7, MOTIF)

    reponse = client_admin.post(f"{URL}{passager.id}/suspendre/", {"motif": MOTIF}, format="json")

    assert reponse.status_code == 409
    assert reponse.json()["reponse"]["code"] == "DEJA_SUSPENDU"


def test_reactivation_efface_le_motif(client_admin, passager):
    suspendre(passager, 7, MOTIF)

    fiche = client_admin.post(f"{URL}{passager.id}/reactiver/").json()["reponse"]

    assert fiche["statut_compte"] == StatutCompte.ACTIF
    assert fiche["motif_suspension"] == ""
    assert fiche["suspendu_jusqu_au"] is None


def test_reactivation_compte_deja_actif(client_admin, passager):
    reponse = client_admin.post(f"{URL}{passager.id}/reactiver/")

    assert reponse.status_code == 409
    assert reponse.json()["reponse"]["code"] == "DEJA_ACTIF"


def test_suspension_automatique_porte_un_motif(passager, monkeypatch):
    from apps.reservations.repository import reservation_repository

    monkeypatch.setattr(reservation_repository, "compter_incidents", lambda *args: 3)

    assert confiance.enregistrer_incident(passager) is True
    passager.refresh_from_db()
    assert passager.motif_suspension.startswith("Suspension automatique : 3 incidents")


def test_reserve_aux_admins(client_utilisateur, passager):
    assert client_utilisateur.get(URL).status_code == 403
    assert client_utilisateur.get(f"{URL}{passager.id}/").status_code == 403
