"""Catalogue des actions auditées : libellé, catégorie et type de ressource.

Seule table de vérité des actions : toute action journalisée doit y figurer (vérifié par
`journaliser`). `ROUTES` relie une route d'écriture de l'API à son action, pour que les refus
renvoyés par l'API (gestionnaire d'exceptions) portent le même nom que les succès.
"""

from dataclasses import dataclass

from apps.audit.models import Categorie as C


@dataclass(frozen=True)
class Action:
    libelle: str
    categorie: str
    ressource: str = ""


ACTIONS: dict[str, Action] = {
    # Compte et session
    "compte.creer": Action("Création de compte", C.METIER, "utilisateur"),
    "session.connecter": Action("Connexion", C.SECURITE, "utilisateur"),
    "session.deconnecter": Action("Déconnexion", C.SECURITE, "utilisateur"),
    "session.rafraichir": Action("Renouvellement de session", C.SECURITE, "utilisateur"),
    "otp.demander": Action("Demande de code de connexion", C.SECURITE),
    "profil.modifier": Action("Modification du profil", C.METIER, "utilisateur"),
    "profil.changer_mode": Action("Changement de mode", C.METIER, "utilisateur"),
    "compte.suspendre": Action("Suspension de compte", C.ADMIN, "utilisateur"),
    "compte.reactiver": Action("Réactivation de compte", C.ADMIN, "utilisateur"),
    # KYC (actions et statuts seulement, jamais le contenu des pièces)
    "kyc.deposer_piece": Action("Dépôt d'une pièce KYC", C.METIER, "dossier_kyc"),
    "kyc.soumettre": Action("Soumission d'un dossier KYC", C.METIER, "dossier_kyc"),
    "kyc.valider": Action("Validation d'un dossier KYC", C.ADMIN, "dossier_kyc"),
    "kyc.rejeter": Action("Rejet d'un dossier KYC", C.ADMIN, "dossier_kyc"),
    "kyc.consulter_piece": Action("Consultation d'une pièce KYC", C.ADMIN, "piece_kyc"),
    # Véhicules et trajets
    "vehicule.declarer": Action("Déclaration d'un véhicule", C.METIER, "vehicule"),
    "vehicule.modifier": Action("Modification d'un véhicule", C.METIER, "vehicule"),
    "vehicule.supprimer": Action("Suppression d'un véhicule", C.METIER, "vehicule"),
    "trajet.publier": Action("Publication d'un trajet", C.METIER, "trajet"),
    "trajet.annuler": Action("Annulation d'un trajet", C.METIER, "trajet"),
    "trajet.terminer": Action("Fin d'un trajet", C.METIER, "trajet"),
    # Réservations
    "reservation.demander": Action("Demande de réservation", C.METIER, "reservation"),
    "reservation.accepter": Action("Acceptation d'une réservation", C.METIER, "reservation"),
    "reservation.refuser": Action("Refus d'une réservation", C.METIER, "reservation"),
    "reservation.annuler": Action("Annulation d'une réservation", C.METIER, "reservation"),
    "reservation.saisir_code": Action("Saisie du code de départ", C.METIER, "reservation"),
    "reservation.declarer_absent": Action("Passager déclaré absent", C.METIER, "reservation"),
    "reservation.confirmer_arrivee": Action("Confirmation d'arrivée", C.METIER, "reservation"),
    "reservation.cloturer": Action("Clôture automatique", C.METIER, "reservation"),
    # Portefeuille (simulé)
    "portefeuille.recharger": Action("Recharge du portefeuille", C.METIER, "utilisateur"),
    "portefeuille.retirer": Action("Retrait du portefeuille", C.METIER, "utilisateur"),
    "paiement.initier": Action("Paiement Mobile Money initié", C.METIER, "utilisateur"),
    "paiement.confirmer": Action(
        "Confirmation d'un paiement Mobile Money", C.METIER, "utilisateur"
    ),
    "portefeuille.verser": Action("Versement manuel d'un retrait", C.ADMIN, "utilisateur"),
    # Confiance, partage, paramètres
    "avis.noter": Action("Note d'un trajet", C.METIER, "reservation"),
    "signalement.creer": Action("Signalement d'un problème", C.METIER, "reservation"),
    "signalement.traiter": Action("Traitement d'un signalement", C.ADMIN, "signalement"),
    "partage.creer_lien": Action("Partage du trajet", C.METIER, "reservation"),
    "parametre.modifier": Action("Modification d'un paramètre", C.ADMIN, "parametre"),
    # Journal d'audit et incidents
    "audit.purger": Action("Purge du journal d'audit (rétention)", C.ADMIN),
    "audit.exporter": Action("Export du journal d'audit", C.ADMIN),
    "api.acces_refuse": Action("Accès refusé", C.SECURITE),
    "api.trop_de_requetes": Action("Trop de requêtes", C.SECURITE),
    "api.non_authentifie": Action("Accès sans session valide", C.SECURITE),
    "api.erreur_interne": Action("Erreur interne de l'API", C.TECHNIQUE),
}

# (nom de route, méthode HTTP) → action. Les routes absentes ne produisent pas de refus métier.
ROUTES: dict[tuple[str, str], str] = {
    ("admin-connexion", "POST"): "session.connecter",
    ("admin-jeton-rafraichir", "POST"): "session.rafraichir",
    ("parametres-detail", "PATCH"): "parametre.modifier",
    ("admin-utilisateur-suspendre", "POST"): "compte.suspendre",
    ("admin-utilisateur-reactiver", "POST"): "compte.reactiver",
    ("admin-kyc-valider", "POST"): "kyc.valider",
    ("admin-kyc-rejeter", "POST"): "kyc.rejeter",
    ("admin-kyc-piece", "GET"): "kyc.consulter_piece",
    ("admin-signalement-traiter", "POST"): "signalement.traiter",
    ("admin-retrait-verser", "POST"): "portefeuille.verser",
    ("admin-retrait-refuser", "POST"): "portefeuille.verser",
    ("otp-demander", "POST"): "otp.demander",
    ("otp-verifier", "POST"): "session.connecter",
    ("jeton-rafraichir", "POST"): "session.rafraichir",
    ("moi", "PATCH"): "profil.modifier",
    ("moi-mode", "PATCH"): "profil.changer_mode",
    ("kyc-pieces", "POST"): "kyc.deposer_piece",
    ("kyc-soumettre", "POST"): "kyc.soumettre",
    ("vehicules", "POST"): "vehicule.declarer",
    ("vehicule-detail", "PATCH"): "vehicule.modifier",
    ("vehicule-detail", "DELETE"): "vehicule.supprimer",
    ("trajets", "POST"): "trajet.publier",
    ("trajet-terminer", "POST"): "trajet.terminer",
    ("trajet-annuler", "POST"): "trajet.annuler",
    ("reservations", "POST"): "reservation.demander",
    ("accepter", "POST"): "reservation.accepter",
    ("refuser", "POST"): "reservation.refuser",
    ("annuler", "POST"): "reservation.annuler",
    ("code-depart", "POST"): "reservation.saisir_code",
    ("absent", "POST"): "reservation.declarer_absent",
    ("confirmer-arrivee", "POST"): "reservation.confirmer_arrivee",
    ("reservation-note", "POST"): "avis.noter",
    ("reservation-signalement", "POST"): "signalement.creer",
    ("partage-creer", "POST"): "partage.creer_lien",
    ("portefeuille-recharger", "POST"): "portefeuille.recharger",
    ("portefeuille-retirer", "POST"): "portefeuille.retirer",
}
