"""Consultation par le back-office : filtres, flux temps réel, statistiques, rétention."""

from datetime import timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from apps.accounts.tests.factories import UserFactory
from apps.audit.models import EvenementAudit
from apps.audit.services import journaliser, purger_expires
from apps.audit.tests.aides import un_evenement, vider_journal
from apps.parametres.services import modifier_param

pytestmark = pytest.mark.django_db

BASE = "/api/v1/admin/audit/"


def _reponse(client, route, **params):
    reponse = client.get(f"{BASE}{route}", params)
    assert reponse.status_code == 200, reponse.json()
    return reponse.json()["reponse"]


def test_journal_vide(client_admin):
    """Scénario 8 : aucun faux résultat quand il n'y a rien."""
    vider_journal()
    assert _reponse(client_admin, "evenements/")["count"] == 0
    stats = _reponse(client_admin, "statistiques/")
    assert stats["total"] == 0 and stats["derniere_activite"] is None
    assert _reponse(client_admin, "flux/", depuis=timezone.now().isoformat())["evenements"] == []


def test_filtres_combines_et_fiche_utilisateur(client_admin, passager, conducteur):
    vider_journal()
    journaliser("profil.modifier", ressource=passager, acteur=passager, details={"champs": ["nom"]})
    journaliser("trajet.publier", ressource_id="t1", acteur=conducteur, role="conducteur")
    journaliser("compte.suspendre", ressource=passager, systeme=True)

    def actions(**filtres):
        return [e["action"] for e in _reponse(client_admin, "evenements/", **filtres)["results"]]

    assert actions(acteur=passager.id) == ["profil.modifier"]
    assert actions(role="conducteur", categorie="metier") == ["trajet.publier"]
    assert actions(role="systeme", resultat="succes") == ["compte.suspendre"]
    assert set(actions(utilisateur=passager.id)) == {"profil.modifier", "compte.suspendre"}
    assert actions(recherche="publier") == ["trajet.publier"]
    assert actions(role="conducteur", canal="mobile") == []


def test_filtres_invalides(client_admin):
    assert client_admin.get(f"{BASE}evenements/", {"canal": "fax"}).status_code == 400
    debut, fin = "2026-10-10T00:00:00Z", "2026-10-01T00:00:00Z"
    assert client_admin.get(f"{BASE}evenements/", {"debut": debut, "fin": fin}).status_code == 400


def test_detail_avec_acteur(client_admin, passager):
    evenement = journaliser("profil.modifier", ressource=passager, acteur=passager)
    detail = _reponse(client_admin, f"evenements/{evenement.id}/")
    assert detail["libelle"] == "Modification du profil"
    assert detail["acteur"]["email"] == passager.email
    assert detail["acteur"]["supprime"] is False


def test_acteur_supprime_reste_dans_l_historique(client_admin):
    ephemere = UserFactory()
    evenement = journaliser("compte.creer", ressource=ephemere, acteur=ephemere)
    ephemere.delete()

    detail = _reponse(client_admin, f"evenements/{evenement.id}/")
    assert detail["acteur"] == {
        "id": str(evenement.acteur_id),
        "prenom": None,
        "nom": None,
        "email": None,
        "supprime": True,
    }


def test_flux_reprise_sans_perte_ni_doublon(client_admin, passager):
    """Scénarios 5 et 9 : après une coupure, le client reprend au dernier événement reçu.
    La marge relit quelques secondes : le client dédoublonne par identifiant."""
    with freeze_time(timezone.now() + timedelta(hours=1)) as horloge:
        premier = journaliser("profil.modifier", ressource=passager, acteur=passager)
        horloge.tick(timedelta(seconds=40))
        recu = _reponse(client_admin, "flux/", depuis=premier.enregistre_le.isoformat())
        dernier_recu = recu["evenements"][-1]["enregistre_le"]
        horloge.tick(timedelta(minutes=5))  # coupure : événements écrits pendant l'absence
        manques = [journaliser("profil.changer_mode", ressource=passager) for _ in range(3)]
        reprise = _reponse(client_admin, "flux/", depuis=dernier_recu)

    ids = [e["id"] for e in reprise["evenements"]]
    assert len(ids) == len(set(ids))
    assert {str(e.id) for e in manques} <= set(ids)
    assert ids == sorted(ids, key=lambda i: ids.index(i))  # ordre chronologique
    assert reprise["tronque"] is False


def test_flux_respecte_les_filtres(client_admin, passager):
    depuis = timezone.now()
    journaliser("profil.modifier", ressource=passager, acteur=passager)
    journaliser("api.erreur_interne", resultat="echec")

    flux = _reponse(client_admin, "flux/", depuis=depuis.isoformat(), categorie="technique")
    assert [e["action"] for e in flux["evenements"]] == ["api.erreur_interne"]


def test_flux_signale_un_volume_trop_grand(client_admin, settings):
    from apps.audit.services import consultation

    depuis = timezone.now()
    consultation.LIMITE_FLUX, ancienne = 2, consultation.LIMITE_FLUX
    try:
        for _ in range(3):
            journaliser("audit.purger", systeme=True)
        flux = _reponse(client_admin, "flux/", depuis=depuis.isoformat())
    finally:
        consultation.LIMITE_FLUX = ancienne
    assert len(flux["evenements"]) == 2 and flux["tronque"] is True


def test_statistiques_par_categorie(client_admin, passager, conducteur):
    vider_journal()
    journaliser("reservation.demander", ressource_id="r1", acteur=passager)
    journaliser("reservation.demander", ressource_id="r2", acteur=passager, resultat="refus")
    journaliser("trajet.publier", ressource_id="t1", acteur=conducteur, role="conducteur")
    journaliser("api.acces_refuse", acteur=passager, resultat="refus")
    journaliser("api.erreur_interne", resultat="echec")
    journaliser("kyc.valider", ressource_id="d1", acteur=UserFactory(is_staff=True))

    stats = _reponse(client_admin, "statistiques/", periode="7j")
    assert stats["metier_succes"] == 2
    assert stats["metier_refus"] == 1
    assert stats["securite"] == stats["securite_refus"] == 1
    assert stats["technique"] == 1
    assert stats["admin"] == 1
    assert stats["utilisateurs_actifs"] == 2
    assert stats["derniere_activite"] is not None


def test_retention_purge_controlee_et_tracee(admin):
    modifier_param("audit_retention_jours", 30, par=admin)
    with freeze_time(timezone.now() - timedelta(days=40)):
        ancien = journaliser("audit.purger", systeme=True)
    recent = journaliser("audit.purger", systeme=True)

    assert purger_expires() == 1

    assert not EvenementAudit.objects.filter(id=ancien.id).exists()
    assert EvenementAudit.objects.filter(id=recent.id).exists()
    trace = EvenementAudit.objects.filter(action="audit.purger", details__supprimes=1)
    assert trace.count() == 1
    assert un_evenement("parametre.modifier").changements == {"valeur": [365, 30]}
