"""Rôles du back-office (F-058, D-36) : chaque admin n'accède qu'à ses domaines ; un admin sans
rôle n'a que le tableau de bord et la consultation des paramètres ; le superutilisateur a tout."""

import pytest
from django.contrib.auth.models import Group

from apps.accounts.tests.factories import AdminFactory
from apps.accounts.tests.routes_admin import routes_par_role
from apps.audit.models import Resultat
from apps.audit.tests.aides import un_evenement, vider_journal
from apps.parametres.services import get_param

pytestmark = pytest.mark.django_db

ROUTES = {
    "moderation": "/api/v1/admin/kyc/",
    "finance": "/api/v1/admin/transactions/",
    "audit": "/api/v1/admin/audit/evenements/",
}
MOI = "/api/v1/auth/admin/moi/"
TABLEAU_DE_BORD = "/api/v1/admin/tableau-de-bord/"
PARAMETRES = "/api/v1/admin/parametres/"
RECHARGE_MIN = f"{PARAMETRES}recharge_min/"
REFUS = "ROLE_ADMIN_INSUFFISANT"


def admin_avec(*roles):
    return AdminFactory(roles=roles)


def _refus_de_role(reponse):
    corps = reponse.json()
    assert reponse.status_code == 403
    assert corps["statut"] == "failed" and corps["message"]
    assert corps["reponse"]["code"] == REFUS
    assert "erreurs" in corps["reponse"]


def test_les_groupes_existent():
    assert set(Group.objects.values_list("name", flat=True)) >= {
        "moderation",
        "finance",
        "audit",
        "parametres",
    }


@pytest.mark.parametrize("role", ["moderation", "finance", "audit"])
def test_ca1_un_role_ouvre_son_domaine_et_ferme_les_autres(client_de, role):
    client = client_de(admin_avec(role))

    for domaine, url in ROUTES.items():
        attendu = 200 if domaine == role else 403
        assert client.get(url).status_code == attendu, (role, domaine)


def test_ca2_parametres_consultables_par_tous_modifiables_par_le_role(client_de):
    moderation = client_de(admin_avec("moderation"))

    assert moderation.get(PARAMETRES).status_code == 200
    assert moderation.patch(RECHARGE_MIN, {"valeur": 600}, format="json").status_code == 403
    parametres = client_de(admin_avec("parametres"))
    assert parametres.patch(RECHARGE_MIN, {"valeur": 600}, format="json").status_code == 200
    assert get_param("recharge_min") == 600


def test_tableau_de_bord_pour_tous_les_admins(client_de):
    assert client_de(admin_avec("audit")).get(TABLEAU_DE_BORD).status_code == 200


def test_ca5_admin_sans_role_n_a_que_tableau_de_bord_et_parametres(client_admin_sans_role):
    moi = client_admin_sans_role.get(MOI)

    assert moi.status_code == 200
    assert moi.json()["reponse"]["roles"] == []
    assert client_admin_sans_role.get(TABLEAU_DE_BORD).status_code == 200
    assert client_admin_sans_role.get(PARAMETRES).status_code == 200
    for url in ROUTES.values():
        _refus_de_role(client_admin_sans_role.get(url))


def test_ca5_admin_sans_role_ne_modifie_pas_un_parametre(client_admin_sans_role):
    avant = get_param("recharge_min")

    reponse = client_admin_sans_role.patch(RECHARGE_MIN, {"valeur": avant + 100}, format="json")

    _refus_de_role(reponse)
    assert get_param("recharge_min") == avant


@pytest.mark.parametrize(("methode", "url"), routes_par_role())
def test_ca5_admin_sans_role_refuse_sur_toute_route_de_domaine(
    client_admin_sans_role, methode, url
):
    _refus_de_role(getattr(client_admin_sans_role, methode)(url, {}, format="json"))


def test_les_routes_de_domaine_sont_toutes_inventoriees():
    """Garde-fou du test paramétré : l'inventaire automatique couvre bien les quatre domaines."""
    routes = set(routes_par_role())

    assert len(routes) >= 25
    assert {
        ("get", "/api/v1/admin/kyc/"),
        ("get", "/api/v1/admin/transactions/"),
        ("get", "/api/v1/admin/audit/export/"),
        ("patch", "/api/v1/admin/parametres/recharge_min/"),
    } <= routes


def test_ca5_superutilisateur_sans_groupe_a_tout(client_de, superutilisateur):
    client = client_de(superutilisateur)

    assert superutilisateur.groups.count() == 0
    roles = client.get(MOI).json()["reponse"]["roles"]
    assert roles == ["audit", "finance", "moderation", "parametres"]
    for url in [*ROUTES.values(), TABLEAU_DE_BORD, PARAMETRES]:
        assert client.get(url).status_code == 200, url
    assert client.patch(RECHARGE_MIN, {"valeur": 700}, format="json").status_code == 200
    assert get_param("recharge_min") == 700


def test_non_staff_avec_le_groupe_finance_refuse(client_de):
    compte = AdminFactory(is_staff=False, roles=["finance"])

    assert client_de(compte).get(ROUTES["finance"]).status_code == 403


def test_superutilisateur_sans_is_staff_refuse(client_de):
    compte = AdminFactory(is_staff=False, is_superuser=True, roles=[])

    assert client_de(compte).get(ROUTES["audit"]).status_code == 403


def test_un_non_admin_n_a_aucun_role(client_de, utilisateur):
    assert client_de(utilisateur).get(ROUTES["finance"]).status_code == 403


def test_ca7_role_ajoute_pris_en_compte_immediatement(client_admin_sans_role, admin_sans_role):
    _refus_de_role(client_admin_sans_role.get(ROUTES["audit"]))

    admin_sans_role.groups.add(Group.objects.get(name="audit"))

    assert client_admin_sans_role.get(MOI).json()["reponse"]["roles"] == ["audit"]
    assert client_admin_sans_role.get(ROUTES["audit"]).status_code == 200
    _refus_de_role(client_admin_sans_role.get(ROUTES["finance"]))


def test_patch_refuse_journalise(client_admin_sans_role, admin_sans_role):
    vider_journal()

    client_admin_sans_role.patch(RECHARGE_MIN, {"valeur": 900}, format="json")

    refus = un_evenement("parametre.modifier")
    assert refus.resultat == Resultat.REFUS
    assert refus.code_motif == REFUS
    assert refus.acteur_id == admin_sans_role.id
