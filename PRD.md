PRD — Réservation et gestion d’un trajet
1. Problème en une phrase

Les passagers ont des difficultés à trouver rapidement un conducteur fiable proposant leur itinéraire, tandis que les conducteurs manquent d’un moyen simple pour proposer leurs trajets et gérer les réservations et paiements.

2. Utilisateurs principaux

Passager — recherche et réserve un trajet.

Conducteur — enregistre son véhicule, propose un itinéraire et gère les demandes de réservation.

3. Fonctionnalité principale : Réserver un trajet

Cas d’utilisation

En tant que passager, je veux rechercher un trajet en indiquant mon point de départ et ma destination afin de voir les conducteurs disponibles à proximité et choisir celui qui me convient.

En tant que conducteur, je veux proposer un itinéraire et recevoir des demandes de passagers afin de remplir mon véhicule.

Parcours principal

Conducteur :

Créer/vérifier son profil.
Enregistrer son véhicule.
Indiquer son point de départ et sa destination.
Définir les informations du trajet : date, heure, places disponibles, prix.
Publier le trajet.
Recevoir une demande de réservation.
Accepter ou refuser la demande.

Passager :

Indiquer son point de départ et sa destination.
Voir les conducteurs proposant un trajet correspondant.
Voir les informations du conducteur et du véhicule.
Choisir un conducteur.
Réserver une place.
Payer en espèces ou via mobile money.
Recevoir la confirmation du trajet.

4. Critères d’acceptation
CA1 — Recherche et sélection

Étant donné qu'un conducteur a publié un trajet,
quand le passager renseigne son départ et sa destination,
alors l'application affiche les conducteurs proposant un itinéraire correspondant, avec notamment leur distance, heure, prix et places disponibles.

CA2 — Réservation

Étant donné qu'un conducteur est disponible,
quand le passager sélectionne ce conducteur et confirme sa réservation,
alors une demande est envoyée au conducteur et la place est temporairement réservée.

CA3 — Paiement

Le passager peut choisir entre :

 paiement en espèces ;
 paiement via mobile money.

Une réservation payée doit être associée au trajet et à l'utilisateur.

CA4 — Annulation et remboursement

Si une réservation payée est annulée dans les conditions prévues, le montant doit être automatiquement recrédité sur le portefeuille du passager.

Pour le MVP, il faut définir clairement qui peut annuler, jusqu'à quand et dans quels cas le remboursement est de 100 %, partiel ou nul.

CA5 — Vérification

Avant de pouvoir effectuer certaines actions sensibles, notamment proposer un trajet ou réserver, l'utilisateur doit avoir effectué la vérification d'identité (KYC — Know Your Customer) selon les règles définies par l'application.

5. Écrans — maximum 3

Pour respecter la contrainte des 3 écrans maximum, je regrouperais les fonctionnalités ainsi :

Écran 1 —  Rechercher un trajet

Passager
Choisir le moyen de déplacement 
Point de départ
Destination
Date / heure
Bouton Rechercher

Ecrans 2 : Affiche la liste des conducteurs disponibles

Choisi le conducteur de son choix 
Distance du conducteur
Prix
Nombre de places
profil
Informations du véhicule

Écran 3 —  Détails & réservation

Photo/profil du conducteur
Information du Véhicule
Itinéraire
Date / heure
Prix
Places disponibles
Mode de paiement :
Espèces
Mobile money 
Réserver le trajet
Annuler

C'est l'écran le plus important du MVP.

Écran 4 — Gestion du trajet

Conducteur :

Enregistrer une voiture
proposer un trajet
Voir les demandes
Accepter / refuser
Annuler un trajet

Passager :

Voir sa réservation
Statut : en attente / acceptée / annulée
Informations du conducteur
Paiement
Remboursement éventuel

6. Données

Utilisateur

User
- id
- nom
- prénom
- téléphone
- email
- photo
- rôle (passager/conducteur)
- statut_KYC

Véhicule

Vehicule 

- id
- conducteur
-Type de vehicule 
- marque 
- modèle
- immatriculation
- couleur
- nombre_places
- photo
- statut_verification


Trajet
Trip
- id
- conducteur
- point_de_départ
- destination
- date
- heure
- prix
- places_disponibles
- statut( en cours / Terminer )
-passager 

Réservation
Booking

- id
- passager
- trajet
- nombre_places
- montant
- statut

Paiement
Payment
- id
- réservation
- montant
- méthode
- statut
- référence

Mobile Money 
Wallet
- id
- utilisateur
- solde

Remboursement
Refund
- id
- paiement
- montant
- motif
- statut

7. Intégrations
 Localisation / itinéraire

Pour :

déterminer la position du conducteur ;
calculer la proximité ;
vérifier la correspondance entre itinéraires ;
éventuellement afficher le trajet sur une carte.

 Paiement

Prévoir une intégration avec les solutions de paiement disponibles au Togo, selon le prestataire retenu.

Le système doit gérer :

Paiement → Confirmation → Annulation → Remboursement.

 KYC

Vérification de l'identité du conducteur et éventuellement du passager :

identité ;
numéro de téléphone ;
pièce d'identité ;
statut de vérification.

8. Stack technique
Partie	Technologie

Backend / API	Django + Django FAST API 
Base de données	PostgreSQL
Application mobile	Flutter
Interface web	React
Authentification	JWT
Paiement	API du prestataire de paiement
Géolocalisation	API cartographique
Vérification	Service/API KYC selon disponibilité


9. HORS PÉRIMÈTRE — à faire plus tard

Pour garder un MVP réalisable, je mettrais hors périmètre :

système de notation avancé ;
chat conducteur/passager ;
intelligence artificielle pour recommander les conducteurs ;
optimisation automatique des itinéraires ;
assurance intégrée ;
programme de fidélité ;
abonnement conducteur ;
statistiques avancées ;
portefeuille multi-devises ;
réservation récurrente ;
intégration de plusieurs prestataires KYC.

 Résumé du MVP

Le produit peut être résumé en un seul parcours central :

Conducteur propose un trajet → Passager recherche → choisit un conducteur → réserve → paie → conducteur accepte → trajet confirmé → annulation éventuelle → remboursement.

C'est ce parcours qu'il faut prioriser dans votre PRD et votre prototype. Les fonctionnalités comme KYC, portefeuille, véhicule et paiement servent à rendre ce parcours fiable et sécurisé.