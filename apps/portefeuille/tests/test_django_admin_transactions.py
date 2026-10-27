"""Django admin des transactions (F-050, D-38) : consultation seule, réservée au rôle Finance
avec la permission Django `view_transaction`. Versement et refus des retraits : API du
back-office uniquement (non-régression dans test_admin_transactions.py,
test_verser_un_retrait_avec_sa_reference et test_refuser_un_retrait_avec_un_motif)."""

import pytest
from django.contrib.auth.models import Permission

from apps.accounts.roles import FINANCE, MODERATION
from apps.accounts.tests.aides_django_admin import ADMIN
from apps.accounts.tests.factories import AdminFactory
from apps.audit.models import EvenementAudit
from apps.portefeuille import services
from apps.portefeuille.models import Transaction

pytestmark = pytest.mark.django_db

LISTE = f"{ADMIN}/portefeuille/transaction/"
ACTIONS_RETIREES = ["marquer_verse", "refuser_retrait"]


def fiche(ligne, vue="change") -> str:
    return f"{LISTE}{ligne.pk}/{vue}/"


def staff(roles, voir=True):
    compte = AdminFactory(roles=roles)
    if voir:
        compte.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="portefeuille", codename="view_transaction"
            )
        )
    return compte


@pytest.fixture
def retrait(passager, settings):
    """Retrait de 1 500 F en attente de versement manuel (PayGate configuré)."""
    settings.PAIEMENT_PROVIDER = "apps.portefeuille.paygate.PayGateProvider"
    settings.PAYGATE_CALLBACK_SECRET = "cle-callback"
    return services.retirer(passager, 1500, "mixx")


@pytest.fixture
def finance():
    """Staff au seul rôle Finance, avec la permission Django de consultation."""
    return staff([FINANCE])


def _modules(client) -> set[str]:
    reponse = client.get(f"{ADMIN}/")
    assert reponse.status_code == 200
    return {app["app_label"] for app in reponse.context["app_list"]}


def _sans_aucune_action(reponse):
    assert reponse.status_code == 200
    assert reponse.context["action_form"] is None
    contenu = reponse.content.decode()
    for nom in [*ACTIONS_RETIREES, "delete_selected", "Retrait versé", "Refuser le retrait"]:
        assert nom not in contenu


def _fiche_en_lecture_seule(reponse):
    assert reponse.status_code == 200
    assert reponse.context["has_change_permission"] is False
    assert reponse.context["has_delete_permission"] is False
    fiche_admin = reponse.context["adminform"]
    assert {"statut", "montant", "reference_externe"} <= set(fiche_admin.readonly_fields)
    assert 'name="_save"' not in reponse.content.decode()


# --- Accès ---


def test_staff_sans_finance_avec_view_transaction_refuse(client, retrait):
    client.force_login(staff([MODERATION]))

    assert client.get(LISTE).status_code == 403
    assert client.get(fiche(retrait)).status_code == 403
    assert "portefeuille" not in _modules(client)


def test_staff_finance_sans_view_transaction_refuse(client, retrait):
    client.force_login(staff([FINANCE], voir=False))

    assert client.get(LISTE).status_code == 403
    assert client.get(fiche(retrait)).status_code == 403
    assert "portefeuille" not in _modules(client)


def test_staff_finance_avec_view_transaction_consulte_sans_action(client, finance, retrait):
    client.force_login(finance)

    assert "portefeuille" in _modules(client)
    liste = client.get(LISTE)
    _sans_aucune_action(liste)
    assert retrait in liste.context["cl"].result_list
    _fiche_en_lecture_seule(client.get(fiche(retrait)))


@pytest.mark.parametrize("vue", ["change", "delete"])
def test_staff_finance_ne_modifie_ni_ne_supprime(client, finance, retrait, vue):
    client.force_login(finance)

    reponse = client.post(fiche(retrait, vue), {"statut": "validee", "post": "yes"})

    assert reponse.status_code == 403
    retrait.refresh_from_db()
    assert retrait.statut == "en_attente"


def test_ajout_impossible_meme_pour_un_superutilisateur(client, superutilisateur):
    client.force_login(superutilisateur)

    assert client.get(f"{LISTE}add/").status_code == 403


# --- POST forgé d'une action retirée ---


@pytest.mark.parametrize("action", ACTIONS_RETIREES)
@pytest.mark.parametrize("compte", ["finance", "superutilisateur"])
def test_action_forgee_sans_effet(client, request, retrait, action, compte):
    client.force_login(request.getfixturevalue(compte))
    lignes_avant = list(Transaction.objects.order_by("pk").values())
    audit_avant = EvenementAudit.objects.count()

    reponse = client.post(
        LISTE, {"action": action, "_selected_action": [retrait.pk], "index": "0", "post": "yes"}
    )

    assert reponse.status_code in {200, 302}
    retrait.refresh_from_db()
    assert retrait.statut == "en_attente"
    assert list(Transaction.objects.order_by("pk").values()) == lignes_avant
    assert EvenementAudit.objects.count() == audit_avant


# --- Superutilisateur et CA-050-2 ---


def test_superutilisateur_consulte_sans_action(client, superutilisateur, retrait):
    client.force_login(superutilisateur)

    _sans_aucune_action(client.get(LISTE))
    _fiche_en_lecture_seule(client.get(fiche(retrait)))


def test_ca_050_2_lecture_seule_dans_django_admin_versement_par_l_api(
    client, client_de, superutilisateur, retrait
):
    client.force_login(superutilisateur)
    liste = client.get(LISTE, {"statut": "en_attente", "type": "retrait"})
    assert list(liste.context["cl"].result_list) == [retrait]
    _sans_aucune_action(liste)
    _fiche_en_lecture_seule(client.get(fiche(retrait)))

    api = client_de(AdminFactory(roles=[FINANCE]))
    reponse = api.post(
        f"/api/v1/admin/transactions/{retrait.pk}/verser/",
        {"reference": "MIXX-778899"},
        format="json",
    )

    assert reponse.status_code == 200
    retrait.refresh_from_db()
    assert (retrait.statut, retrait.reference_externe) == ("validee", "MIXX-778899")
    evenement = EvenementAudit.objects.get(action="portefeuille.verser")
    assert evenement.resultat == "succes"
