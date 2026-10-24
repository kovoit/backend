"""Rôles du back-office : chaque admin n'accède qu'à ses domaines (sans rôle : à tout)."""

import pytest
from django.contrib.auth.models import Group

from apps.accounts.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

ROUTES = {
    "moderation": "/api/v1/admin/kyc/",
    "finance": "/api/v1/admin/transactions/",
    "audit": "/api/v1/admin/audit/evenements/",
}


def admin_avec(*roles):
    compte = UserFactory(is_staff=True)
    compte.groups.set(Group.objects.filter(name__in=roles))
    return compte


def test_les_groupes_existent():
    assert set(Group.objects.values_list("name", flat=True)) >= {
        "moderation",
        "finance",
        "audit",
        "parametres",
    }


@pytest.mark.parametrize("role", ["moderation", "finance", "audit"])
def test_un_role_ouvre_son_domaine_et_ferme_les_autres(client_de, role):
    client = client_de(admin_avec(role))

    for domaine, url in ROUTES.items():
        attendu = 200 if domaine == role else 403
        assert client.get(url).status_code == attendu, (role, domaine)


def test_admin_sans_role_garde_tout_et_profil_annonce_ses_roles(client_de):
    admin = admin_avec()
    client = client_de(admin)

    assert all(client.get(url).status_code == 200 for url in ROUTES.values())
    roles = client.get("/api/v1/auth/admin/moi/").json()["reponse"]["roles"]
    assert roles == ["audit", "finance", "moderation", "parametres"]


def test_parametres_consultables_par_tous_modifiables_par_le_role(client_de):
    finance = client_de(admin_avec("finance"))
    url = "/api/v1/admin/parametres/recharge_min/"

    assert finance.get("/api/v1/admin/parametres/").status_code == 200
    assert finance.patch(url, {"valeur": 600}, format="json").status_code == 403
    parametres = client_de(admin_avec("parametres"))
    assert parametres.patch(url, {"valeur": 600}, format="json").status_code == 200


def test_tableau_de_bord_pour_tous_les_admins(client_de):
    assert client_de(admin_avec("audit")).get("/api/v1/admin/tableau-de-bord/").status_code == 200


def test_un_non_admin_n_a_aucun_role(client_de, utilisateur):
    assert client_de(utilisateur).get(ROUTES["finance"]).status_code == 403
