from django.db import transaction
from django.utils import timezone

from apps.accounts.models import ModeActif, StatutCompte, User
from apps.accounts.repository import user_repository
from apps.audit.services import journaliser
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


def modifier_profil(utilisateur: User, *, accepter_cgu: bool = False, **champs) -> User:
    """`accepter_cgu` : l'utilisateur accepte les CGU en vigueur (case cochée dans l'app)."""
    from apps.accounts.cgu import CGU_VERSION

    donnees = {cle: valeur for cle, valeur in champs.items() if cle in CHAMPS_MODIFIABLES}
    if accepter_cgu and utilisateur.cgu_version != CGU_VERSION:
        with transaction.atomic():
            utilisateur = user_repository.update(
                utilisateur, cgu_version=CGU_VERSION, cgu_acceptees_le=timezone.now()
            )
            journaliser(
                "profil.accepter_cgu", ressource=utilisateur, details={"version": CGU_VERSION}
            )
    if not donnees:
        return utilisateur
    with transaction.atomic():
        utilisateur = user_repository.update(utilisateur, **donnees)
        # Noms des champs seulement : les valeurs (téléphone, photo) restent hors du journal
        journaliser("profil.modifier", ressource=utilisateur, details={"champs": sorted(donnees)})
    return utilisateur


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
    ancien = utilisateur.mode_actif
    with transaction.atomic():
        utilisateur = user_repository.update(utilisateur, mode_actif=mode)
        journaliser(
            "profil.changer_mode", ressource=utilisateur, changements={"mode_actif": [ancien, mode]}
        )
    return utilisateur


def lister_utilisateurs(recherche: str | None = None, statut: str | None = None):
    return user_repository.lister(recherche, statut)


def get_utilisateur(utilisateur_id) -> User:
    return user_repository.get_by_id(utilisateur_id)
