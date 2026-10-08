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
    from apps.kyc.services import peut_publier

    if mode == ModeActif.CONDUCTEUR and not peut_publier(utilisateur):
        raise ModeConducteurIndisponible()
    return user_repository.update(utilisateur, mode_actif=mode)


def lister_utilisateurs(recherche: str | None = None, statut: str | None = None):
    return user_repository.lister(recherche, statut)


def get_utilisateur(utilisateur_id) -> User:
    return user_repository.get_by_id(utilisateur_id)
