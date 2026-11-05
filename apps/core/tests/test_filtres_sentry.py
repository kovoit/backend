"""Masquage des secrets avant envoi à Sentry : événement factice, sans réseau ni DSN."""

from kovoit.filtres_sentry import ARGUMENTS_RETIRES, avant_envoi, creer_masqueur

MASQUE = "[Filtered]"


def _evenement() -> dict:
    return {
        "request": {
            "data": {
                "email": "ama.mensah@exemple.tg",
                "mot_de_passe": "Lome-Kovoit-26",
                "nouveau_mot_de_passe": "Nouveau-Kovoit-27",
                "code": "123456",
                "refresh": "eyJ.refresh",
                "telephone": "+22890112233",
                "prenom": "Ama",
            },
            "headers": {"Authorization": "Bearer eyJ.access"},
        },
        "extra": {
            "celery-job": {
                "task_name": "envoyer_email_tache",
                "args": ["ama.mensah@exemple.tg", "Votre code : 123456"],
                "kwargs": {"code": "123456"},
            }
        },
        "exception": {
            "values": [
                {
                    "stacktrace": {
                        "frames": [
                            {"vars": {"donnees": {"mot_de_passe": "x", "access": "y"}, "n": 1}}
                        ]
                    }
                }
            ]
        },
    }


def _filtrer(evenement: dict) -> dict:
    creer_masqueur().scrub_event(evenement)  # appliqué par le SDK avant before_send
    return avant_envoi(evenement, {})


def _valeur(champ) -> str:
    return getattr(champ, "value", champ)


def test_corps_de_requete_et_entetes_masques():
    evenement = _filtrer(_evenement())

    donnees = evenement["request"]["data"]
    for cle in ("email", "mot_de_passe", "nouveau_mot_de_passe", "code", "refresh", "telephone"):
        assert _valeur(donnees[cle]) == MASQUE, cle
    assert donnees["prenom"] == "Ama"
    assert _valeur(evenement["request"]["headers"]["Authorization"]) == MASQUE


def test_arguments_celery_vides():
    tache = _filtrer(_evenement())["extra"]["celery-job"]

    assert tache["args"] == tache["kwargs"] == ARGUMENTS_RETIRES
    assert tache["task_name"] == "envoyer_email_tache"


def test_variables_locales_imbriquees_masquees():
    evenement = _filtrer(_evenement())

    variables = evenement["exception"]["values"][0]["stacktrace"]["frames"][0]["vars"]
    assert _valeur(variables["donnees"]["mot_de_passe"]) == MASQUE
    assert _valeur(variables["donnees"]["access"]) == MASQUE
    assert variables["n"] == 1


def test_evenement_sans_extra_inchange():
    assert avant_envoi({"message": "ok"}, {}) == {"message": "ok"}


def test_fils_d_ariane_celery_masques():
    """Journal « Task … received » (celery.worker.strategy) : extra={'data': {'args': …}}."""
    donnees = {
        "name": "apps.notifications.tasks.envoyer_email_tache",
        "args": "('ama@exemple.tg', 'Code', 'Votre code : 123456')",
        "kwargs": "{'lien': '/reinitialiser/MQ/jeton-secret/'}",
    }
    evenement = {
        "breadcrumbs": {"values": [{"category": "celery", "data": {"data": donnees}}]},
        "extra": {"celery-job": {"args": ["ama@exemple.tg"], "kwargs": {}}},
    }

    filtre = _filtrer(evenement)["breadcrumbs"]["values"][0]["data"]["data"]
    assert _valeur(filtre["args"]) == _valeur(filtre["kwargs"]) == MASQUE
    assert filtre["name"] == "apps.notifications.tasks.envoyer_email_tache"
    assert "ama@exemple.tg" not in repr(evenement)
    assert "123456" not in repr(evenement) and "jeton-secret" not in repr(evenement)
