from django.utils import timezone

from apps.accounts.models import ModeActif, StatutCompte, User
from apps.accounts.repository import user_repository
from apps.core.exceptions import ActionInterdite

CHAMPS_MODIFIABLES = {"nom", "prenom", "telephone", "photo"}


class ModeConducteurIndisponible(ActionInterdite):
    code = "MODE_CONDUCTEUR_INDISPONIBLE"
    message = "Le mode conducteur nécessite un KYC conducteur vérifié et un véhicule déclaré."


def est_suspendu(utilisateur: User) -> bool:
    if utilisateur.statut_compte != StatutCompte.SUSPENDU:
        return False
    fin = utilisateur.suspendu_jusqu_au
    return fin is None or fin > timezone.now()


def modifier_profil(utilisateur: User, **champs) -> User:
    donnees = {cle: valeur for cle, valeur in champs.items() if cle in CHAMPS_MODIFIABLES}
    if not donnees:
        return utilisateur
    return user_repository.update(utilisateur, **donnees)


def changer_mode(utilisateur: User, mode: str) -> User:
    """Bouton « Passer en mode conducteur / passager » de l'écran Profil.

    Le retour en mode passager est toujours possible. Le mode conducteur exige un KYC
    conducteur vérifié puis un véhicule déclaré : le code d'erreur dit lequel manque.
    """
    from apps.kyc.models import TypeDossier
    from apps.kyc.services import est_verifie
    from apps.vehicules.repository import vehicule_repository

    if mode == ModeActif.CONDUCTEUR:
        if not est_verifie(utilisateur, TypeDossier.CONDUCTEUR):
            raise ModeConducteurIndisponible(
                "Faites vérifier votre identité conducteur (KYC) depuis votre profil.",
                code="KYC_CONDUCTEUR_REQUIS",
            )
        if not vehicule_repository.exists(proprietaire=utilisateur):
            raise ModeConducteurIndisponible(
                "Déclarez votre véhicule pour passer en mode conducteur.",
                code="VEHICULE_REQUIS",
            )
    return user_repository.update(utilisateur, mode_actif=mode)


def lister_utilisateurs(recherche: str | None = None, statut: str | None = None):
    return user_repository.lister(recherche, statut)


def get_utilisateur(utilisateur_id) -> User:
    return user_repository.get_by_id(utilisateur_id)
