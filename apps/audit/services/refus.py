"""Refus et incidents renvoyés par l'API, journalisés depuis le gestionnaire d'exceptions.

Le refus porte le nom de l'action tentée (catalogue.ROUTES) : « Demande de réservation —
refusée (PLUS_DE_PLACE) » se lit à côté des succès de la même action. Pour limiter le bruit,
seules les routes d'écriture auditées produisent des refus métier ; les erreurs de saisie
(validation des champs) et les jetons expirés de l'app mobile ne sont pas journalisés.
"""

from apps.audit import contexte
from apps.audit.catalogue import ROUTES
from apps.audit.models import Categorie, Resultat
from apps.audit.services.journal import journaliser_sans_bloquer

CODES_SECURITE = {
    "IDENTIFIANTS_INVALIDES",
    "COMPTE_NON_ADMIN",
    "COMPTE_DESACTIVE",
    "CODE_OTP_INVALIDE",
    "CODE_DEPART_BLOQUE",
    "SESSION_EXPIREE",
    "ACCES_REFUSE",
    "TROP_DE_REQUETES",
}
CODES_AUTHENTIFICATION = {"NON_AUTHENTIFIE", "AUTHENTIFICATION_ECHOUEE"}
PREFIXE_ADMIN = "/api/v1/admin/"


def journaliser_erreur_api(code: str, http_status: int, metier: bool) -> None:
    """`metier` : erreur levée par un service ou une permission (pas une erreur de saisie)."""
    route = contexte.route_courante()
    if route is None:
        if http_status >= 500 and contexte.requete_courante() is not None:
            journaliser_sans_bloquer("api.erreur_interne", resultat=Resultat.ECHEC, code_motif=code)
        return
    nom, methode, parametres = route
    action = ROUTES.get((nom, methode))
    ressource_id = parametres.get("pk")
    lieu = {"route": nom, "methode": methode}

    if http_status >= 500:
        journaliser_sans_bloquer(
            "api.erreur_interne", resultat=Resultat.ECHEC, code_motif=code, details=lieu
        )
    elif code == "TROP_DE_REQUETES":
        journaliser_sans_bloquer(
            "api.trop_de_requetes", resultat=Resultat.REFUS, code_motif=code, details=lieu
        )
    elif code in CODES_AUTHENTIFICATION:
        if contexte.requete_courante().path.startswith(PREFIXE_ADMIN):
            journaliser_sans_bloquer(
                "api.non_authentifie", resultat=Resultat.REFUS, code_motif=code, details=lieu
            )
    elif action is not None and metier:
        journaliser_sans_bloquer(
            action,
            ressource_id=ressource_id,
            resultat=Resultat.REFUS,
            code_motif=code,
            categorie=Categorie.SECURITE if code in CODES_SECURITE else None,
        )
    elif code == "ACCES_REFUSE":
        journaliser_sans_bloquer(
            "api.acces_refuse", resultat=Resultat.REFUS, code_motif=code, details=lieu
        )
