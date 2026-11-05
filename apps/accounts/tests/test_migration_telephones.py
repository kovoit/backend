"""Migration de données accounts/0007 (F-003, D-63) : les numéros lisibles passent à la forme
+228XXXXXXXX ; fixes, illisibles et vides restent intacts (aucune perte) et sont comptés."""

from importlib import import_module

import pytest
from django.apps import apps as registre
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.accounts.models import User
from apps.accounts.tests.factories import UserFactory

migration = import_module("apps.accounts.migrations.0007_telephones_format_togolais")

AVANT = ("accounts", "0006_roles_admins_existants")
APRES = ("accounts", "0007_telephones_format_togolais")

# Anciennes saisies (16 caractères au plus : longueur de la colonne)
CONVERTIS = {
    "90112233": "+22890112233",
    "90 11 22 33": "+22890112233",
    "90-11-22-33": "+22890112233",
    "+228 70 11 22 33": "+22870112233",
    "0022890112233": "+22890112233",
    "22879112233": "+22879112233",
    "(228)90.11.22.33": "+22890112233",
    "90\u00a011\u00a022\u00a033": "+22890112233",
}
# D-65 : saisies copiées-collées (tirets Unicode, marques bidirectionnelles, largeur nulle)
COPIES_COLLEES = {
    "90\u201311\u201322\u201333": "+22890112233",
    "\u202a90 11 22 33\u202c": "+22890112233",
    "\u2066+228\u221270112233\u2069": "+22870112233",
    "\ufeff90\u200b112233\u200e": "+22890112233",
    "\u2068\u0669\u0660\u0661\u0661\u0662\u0662\u0663\u0663\u2069": None,  # reste intact
}
INTACTS = ["22112233", "+22822112233", "+33612345678", "12345", "90/11/22/33", ""]


def migrer():
    migration.convertir_telephones(registre, None)


def comptes(telephones) -> dict:
    """Comptes créés tels quels (sans passer par create_user, qui normalise)."""
    return {UserFactory(telephone=numero).pk: numero for numero in telephones}


def telephone(pk) -> str:
    return User.objects.values_list("telephone", flat=True).get(pk=pk)


@pytest.mark.django_db
def test_numeros_lisibles_convertis():
    crees = comptes(CONVERTIS)

    migrer()

    for pk, ancien in crees.items():
        assert telephone(pk) == CONVERTIS[ancien], ancien


@pytest.mark.django_db
def test_d65_saisies_copiees_collees_converties():
    crees = comptes(COPIES_COLLEES)

    migrer()

    for pk, ancien in crees.items():
        assert telephone(pk) == (COPIES_COLLEES[ancien] or ancien), repr(ancien)


@pytest.mark.django_db
def test_fixes_illisibles_et_vides_laisses_intacts():
    crees = comptes(INTACTS)

    migrer()

    for pk, ancien in crees.items():
        assert telephone(pk) == ancien


@pytest.mark.django_db
def test_forme_deja_internationale_inchangee_et_non_comptee(capsys):
    (pk,) = comptes(["+22890112233"])

    migrer()

    assert telephone(pk) == "+22890112233"
    assert capsys.readouterr().out == ""  # rien à signaler


@pytest.mark.django_db
def test_message_compte_convertis_et_illisibles(capsys):
    comptes(["90 11 22 33", "70-11-22-33", "+22890000001", "22112233", "abc", ""])

    migrer()

    sortie = capsys.readouterr().out
    assert "2 convertis au format +228XXXXXXXX" in sortie
    assert "2 illisibles laissés inchangés" in sortie  # le vide n'est pas compté


@pytest.mark.django_db
def test_migration_idempotente(capsys):
    crees = comptes([*CONVERTIS, *INTACTS])
    migrer()
    apres_premier_passage = {pk: telephone(pk) for pk in crees}
    capsys.readouterr()

    migrer()

    assert {pk: telephone(pk) for pk in crees} == apres_premier_passage
    assert "0 convertis" in capsys.readouterr().out


def test_regle_figee_de_la_migration():
    """Valeurs figées comparées à des littéraux : une évolution de apps/core/telephone.py ne
    doit pas pousser à modifier une migration déjà appliquée (claude.md §9)."""
    assert migration.FORMAT.pattern == r"(?:\+228|00228|228)?([79][0-9]{7})"
    assert migration.SEPARATEURS.pattern == (
        r"[\s\-.()\u2010-\u2015\u2212\u200b-\u200f\u202a-\u202e\u2066-\u2069\u2060\ufeff]"
    )
    assert migration.lire("90" + " " * 25 + "112233") is None  # plus de 32 caractères


def test_pas_de_retour_arriere_destructeur():
    (operation,) = migration.Migration.operations
    assert operation.reverse_code.__name__ == "noop"


@pytest.mark.django_db(transaction=True, serialized_rollback=True)
def test_de_bout_en_bout_0006_vers_0007():
    executor = MigrationExecutor(connection)
    try:
        executor.migrate([AVANT])
        ancien = executor.loader.project_state([AVANT]).apps.get_model("accounts", "User")
        saisies = {
            "lisible": "90 11 22 33",
            "indicatif": "00228 70112233",
            "fixe": "22112233",
            "deja": "+22890000002",
            "vide": "",
        }
        pk = {
            cle: ancien.objects.create(email=f"{cle}@kovoit.tg", telephone=numero).pk
            for cle, numero in saisies.items()
        }

        executor = MigrationExecutor(connection)
        executor.migrate([APRES])

        nouveau = executor.loader.project_state([APRES]).apps.get_model("accounts", "User")
        resultat = {cle: nouveau.objects.get(pk=pk[cle]).telephone for cle in saisies}
        assert resultat == {
            "lisible": "+22890112233",
            "indicatif": "+22870112233",
            "fixe": "22112233",
            "deja": "+22890000002",
            "vide": "",
        }
    finally:
        # Revenir au dernier état de toutes les apps : migrate([AVANT]) a annulé tous les
        # descendants de accounts/0006, et une exception a pu survenir entre les deux migrate
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
