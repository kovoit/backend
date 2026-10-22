"""Accès, intégrité du journal, incidents techniques et filtre des données sensibles."""

from unittest.mock import patch

import pytest
from django.db import connection, transaction
from django.db.utils import DatabaseError

from apps.audit.models import Categorie, EvenementAudit, Gravite, Resultat
from apps.audit.securite import MASQUE, changements, nettoyer
from apps.audit.services import journaliser
from apps.audit.tests.aides import un_evenement

pytestmark = pytest.mark.django_db

URL = "/api/v1/admin/audit/evenements/"


def test_api_reservee_aux_administrateurs(client_utilisateur, api_client):
    """Scénario 4 : refus, et la tentative est elle-même journalisée (sécurité)."""
    for route in (URL, "/api/v1/admin/audit/flux/", "/api/v1/admin/audit/statistiques/"):
        assert client_utilisateur.get(route).status_code == 403
        assert api_client.get(route).status_code == 401
    refus = EvenementAudit.objects.filter(action="api.acces_refuse")
    assert refus.count() == 3
    assert {e.categorie for e in refus} == {Categorie.SECURITE}
    assert {e.gravite for e in refus} == {Gravite.AVERTISSEMENT}
    assert EvenementAudit.objects.filter(action="api.non_authentifie").count() == 3


def test_api_en_lecture_seule(client_admin):
    """Scénario 10 : aucune route ne modifie ni ne supprime le journal."""
    evenement = journaliser("audit.purger", systeme=True)
    for methode in ("post", "put", "patch", "delete"):
        assert getattr(client_admin, methode)(URL).status_code == 405
        assert getattr(client_admin, methode)(f"{URL}{evenement.id}/").status_code == 405


def test_modele_en_ajout_seul():
    evenement = journaliser("audit.purger", systeme=True)
    evenement.action = "compte.creer"
    with pytest.raises(PermissionError):
        evenement.save()
    with pytest.raises(PermissionError):
        evenement.delete()


@pytest.mark.skipif(connection.vendor != "postgresql", reason="trigger PostgreSQL")
def test_trigger_refuse_modification_et_suppression_directes():
    evenement = journaliser("audit.purger", systeme=True)
    for requete in (
        "UPDATE audit_evenementaudit SET action = 'x' WHERE id = %s",
        "DELETE FROM audit_evenementaudit WHERE id = %s",
    ):
        with (
            pytest.raises(DatabaseError, match="ajout seul"),
            transaction.atomic(),
            connection.cursor() as curseur,
        ):
            curseur.execute(requete, [evenement.id])
    assert EvenementAudit.objects.filter(id=evenement.id, action="audit.purger").exists()


def test_erreur_interne_journalisee_sans_details(client_de, passager):
    with patch(
        "apps.portefeuille.api.views.services.solde",
        side_effect=RuntimeError("secret interne"),
    ):
        reponse = client_de(passager).get("/api/v1/portefeuille/")

    assert reponse.status_code == 500
    incident = un_evenement("api.erreur_interne")
    assert (incident.categorie, incident.resultat) == (Categorie.TECHNIQUE, Resultat.ECHEC)
    assert incident.gravite == Gravite.CRITIQUE
    assert incident.request_id == reponse["X-Request-ID"]
    assert "secret interne" not in str(incident.details)


def test_echec_d_ecriture_du_journal_annule_l_operation(client_de, passager):
    """Pas de succès sans trace : si le journal ne peut pas écrire, l'opération est annulée."""
    with patch(
        "apps.portefeuille.services.mobile_money.journaliser",
        side_effect=RuntimeError("base indisponible"),
    ):
        reponse = client_de(passager).post(
            "/api/v1/portefeuille/recharger/", {"montant": 1000, "moyen": "flooz"}, format="json"
        )

    assert reponse.status_code == 500
    solde = client_de(passager).get("/api/v1/portefeuille/").json()["reponse"]
    assert solde["total"] == 5000  # la recharge n'a pas été enregistrée


def test_identifiant_de_correlation_repris_s_il_est_bien_forme(client_utilisateur):
    recu = "0123456789abcdef0123456789abcdef"
    assert client_utilisateur.get("/api/v1/moi/", HTTP_X_REQUEST_ID=recu)["X-Request-ID"] == recu
    injecte = client_utilisateur.get("/api/v1/moi/", HTTP_X_REQUEST_ID="<script>")
    assert injecte["X-Request-ID"] != "<script>"


def test_filtre_des_donnees_sensibles():
    propre = nettoyer(
        {
            "mot_de_passe": "x",
            "access": "jwt",
            "refresh_token": "jwt",
            "code": "1234",
            "code_depart": "1234",
            "fichier": "piece.png",
            "montant": 300,
            "texte": "a" * 500,
        }
    )
    sensibles = ("mot_de_passe", "access", "refresh_token", "code", "code_depart", "fichier")
    assert all(propre[cle] == MASQUE for cle in sensibles)
    assert propre["montant"] == 300
    assert len(propre["texte"]) == 301
    assert changements({"a": 1, "b": 2}, {"a": 1, "b": 3}) == {"b": [2, 3]}
