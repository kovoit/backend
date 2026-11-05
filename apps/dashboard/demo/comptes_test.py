"""Quatre comptes de test `@kovoit.test` remis à l'état voulu (commande `seed_comptes_test`).

Tout passe par les services métier (profil, véhicule, dépôt et soumission KYC, validation
par un admin). Seul retour en arrière sans service : un dossier vérifié qu'il faut remettre
« en attente » repasse d'abord à « non vérifié » par le repository (comme `seed_demo`).
"""

from dataclasses import dataclass

from apps.accounts import services as comptes
from apps.accounts.models import StatutCompte
from apps.accounts.repository import user_repository
from apps.dashboard.demo import DEMO_MOT_DE_PASSE
from apps.dashboard.demo.personnes import image_fictive, soumettre_dossier
from apps.kyc import services as kyc
from apps.kyc.models import StatutKyc, TypeDossier
from apps.kyc.repository import dossier_repository
from apps.vehicules import services as vehicules

DOMAINE = "kovoit.test"
VERIFIE, EN_ATTENTE = StatutKyc.VERIFIE, StatutKyc.EN_ATTENTE


@dataclass(frozen=True)
class CompteTest:
    email: str
    prenom: str
    nom: str
    telephone: str
    kyc: dict  # type de dossier → statut voulu
    vehicule: tuple[str, str, str, str] | None  # marque, modèle, couleur, immatriculation
    debloque: str


COMPTES = [
    CompteTest(
        f"conducteur.verifie@{DOMAINE}",
        "Kodjo",
        "Test",
        "+22890000101",
        {TypeDossier.PASSAGER: VERIFIE, TypeDossier.CONDUCTEUR: VERIFIE},
        ("Toyota", "Corolla", "Gris", "TG 9101 TA"),
        "réserver et publier un trajet",
    ),
    CompteTest(
        f"conducteur.attente@{DOMAINE}",
        "Edem",
        "Test",
        "+22890000102",
        {TypeDossier.PASSAGER: EN_ATTENTE, TypeDossier.CONDUCTEUR: EN_ATTENTE},
        ("Kia", "Picanto", "Blanc", "TG 9102 TB"),
        "rechercher ; 2 dossiers dans « KYC à traiter »",
    ),
    CompteTest(
        f"passager.verifie@{DOMAINE}",
        "Afi",
        "Test",
        "+22890000103",
        {TypeDossier.PASSAGER: VERIFIE},
        None,
        "rechercher et réserver",
    ),
    CompteTest(
        f"passager.attente@{DOMAINE}",
        "Yawa",
        "Test",
        "+22890000104",
        {TypeDossier.PASSAGER: EN_ATTENTE},
        None,
        "rechercher ; 1 dossier dans « KYC à traiter »",
    ),
]


def admin_acteur():
    """Superutilisateur (le plus ancien) ; à défaut un autre admin ; sinon None."""
    return (
        user_repository.filter(is_staff=True, is_active=True)
        .order_by("-is_superuser", "cree_le")
        .first()
    )


def _compte(donnees: CompteTest):
    utilisateur, _ = user_repository.get_ou_creer(donnees.email)
    utilisateur = user_repository.changer_mot_de_passe(
        utilisateur,
        DEMO_MOT_DE_PASSE,
        email_verifie=True,
        is_active=True,
        statut_compte=StatutCompte.ACTIF,
        suspendu_jusqu_au=None,
    )
    champs = {"prenom": donnees.prenom, "nom": donnees.nom, "telephone": donnees.telephone}
    if not utilisateur.photo:
        titulaire = f"{donnees.prenom} {donnees.nom}"
        champs["photo"] = image_fictive("Photo de profil", titulaire)
    return comptes.modifier_profil(utilisateur, accepter_cgu=True, **champs)


def _vehicule(utilisateur, donnees: CompteTest) -> None:
    marque, modele, couleur, immatriculation = donnees.vehicule
    photo = image_fictive(f"{marque} {modele}", immatriculation)
    existant = vehicules.mes_vehicules(utilisateur).first()
    if existant is None:
        vehicules.declarer(
            utilisateur,
            type_vehicule="voiture",
            marque=marque,
            modele=modele,
            couleur=couleur,
            immatriculation=immatriculation,
            nb_places=5,
            photo=photo,
        )
    elif not existant.photo:
        vehicules.modifier(utilisateur, existant.id, photo=photo)


def _dossier(utilisateur, type_dossier: str, voulu: str, admin) -> str:
    dossier = dossier_repository.get_ou_creer(utilisateur, type_dossier)
    complet = not kyc.pieces_manquantes(dossier)
    if dossier.statut == voulu and complet:
        return voulu
    if dossier.statut in (VERIFIE, EN_ATTENTE):
        dossier = dossier_repository.update(dossier, statut=StatutKyc.NON_VERIFIE)
    if dossier.statut != EN_ATTENTE:
        dossier = soumettre_dossier(utilisateur, type_dossier)
    if voulu == VERIFIE:
        dossier = kyc.valider(dossier.id, admin)
    return dossier.statut


def preparer(donnees: CompteTest, admin) -> dict:
    """Crée ou remet le compte à l'état voulu ; renvoie la ligne du tableau récapitulatif."""
    utilisateur = _compte(donnees)
    if donnees.vehicule:
        _vehicule(utilisateur, donnees)
    statuts = {
        type_dossier: _dossier(utilisateur, type_dossier, voulu, admin)
        for type_dossier, voulu in donnees.kyc.items()
    }
    etat = comptes.etat_profil(utilisateur)["acces"]
    return {"utilisateur": utilisateur, "kyc": statuts, "acces": etat, "debloque": donnees.debloque}
