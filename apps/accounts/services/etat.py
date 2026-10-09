"""État du profil pour l'écran « Profil » et les tableaux de bord.

Le KYC ne bloque pas l'inscription : il se fait depuis le profil. Tant qu'il n'est pas validé,
`acces` indique ce qui est verrouillé et `badge_kyc` déclenche le macaron orange.
"""

from apps.accounts.models import User
from apps.accounts.services.profil import est_suspendu

MESSAGES_KYC = {
    "passager": {
        "non_verifie": "Vérifiez votre identité dans votre profil pour pouvoir réserver.",
        "en_attente": "Votre identité est en cours de vérification par l'équipe Kovoit.",
        "rejete": "Votre dossier passager a été rejeté : corrigez-le dans votre profil.",
    },
    "conducteur": {
        "en_attente": "Votre dossier conducteur est en cours de vérification.",
        "rejete": "Votre dossier conducteur a été rejeté : corrigez-le dans votre profil.",
    },
}
# Statuts qui demandent une action de l'utilisateur (macaron orange)
STATUTS_A_TRAITER = {"non_verifie", "rejete"}


def _alerte(code: str, message: str, action_requise: bool) -> dict:
    return {"code": code, "message": message, "action_requise": action_requise}


def etat_profil(utilisateur: User) -> dict:
    from apps.kyc.services import statuts_kyc
    from apps.vehicules.repository import vehicule_repository

    statuts = statuts_kyc(utilisateur)
    suspendu = est_suspendu(utilisateur)
    passager_verifie = statuts["passager"] == "verifie"
    conducteur_verifie = statuts["conducteur"] == "verifie"
    vehicule_declare = vehicule_repository.exists(proprietaire=utilisateur)

    alertes = []
    if suspendu:
        alertes.append(
            _alerte(
                "COMPTE_SUSPENDU",
                "Compte suspendu : réservation et publication impossibles.",
                False,
            )
        )
    if not utilisateur.profil_complet:
        alertes.append(
            _alerte("PROFIL_INCOMPLET", "Complétez votre nom, prénom et téléphone.", True)
        )
    for type_dossier, messages in MESSAGES_KYC.items():
        statut = statuts[type_dossier]
        if statut in messages:
            code = f"KYC_{type_dossier.upper()}_{statut.upper()}"
            alertes.append(_alerte(code, messages[statut], statut in STATUTS_A_TRAITER))
    if conducteur_verifie and not vehicule_declare:
        alertes.append(
            _alerte(
                "VEHICULE_A_DECLARER", "Déclarez votre véhicule pour proposer des trajets.", True
            )
        )

    return {
        "badge_kyc": statuts["passager"] in STATUTS_A_TRAITER or statuts["conducteur"] == "rejete",
        "acces": {
            "peut_rechercher": utilisateur.email_verifie,
            "peut_reserver": passager_verifie and not suspendu,
            "peut_publier": conducteur_verifie and vehicule_declare and not suspendu,
        },
        "mode_conducteur": {
            "disponible": conducteur_verifie and vehicule_declare,
            "kyc_conducteur_verifie": conducteur_verifie,
            "vehicule_declare": vehicule_declare,
        },
        "alertes": alertes,
    }
