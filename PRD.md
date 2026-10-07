# Kovoit Spécification du MVP

## Vision et principes

Kovoit met en relation des conducteurs qui font déjà un trajet en ville à Lomé avec des passagers qui vont dans la même direction. Le conducteur réduit ses frais de carburant, le passager paie moins cher qu'un zémidjan ou un taxi.

- **Périmètre du MVP** : trajets urbains à Lomé uniquement. Les trajets entre villes sont hors périmètre.

- **Partage de frais, pas de profit** : le prix couvre une part du carburant du conducteur. Kovoit n'est pas un service de taxi (cadre légal au Togo à confirmer).

- **Prix fixe et connu à l'avance** : pas de négociation, contrairement aux zémidjans et aux taxis.

- **Un seul compte, deux modes** : la même personne peut être conductrice le matin et passagère le soir.

- **Trois types d'utilisateurs** : passager, conducteur, administrateur. Le KYC est obligatoire avant de réserver ou de publier.

## Rôles et fonctionnalités du MVP

Un utilisateur a un seul compte et bascule entre les modes passager et conducteur. Le mode conducteur s'active une fois le KYC conducteur validé et un véhicule déclaré.

### Passager

- [ ] Créer un compte avec son numéro de téléphone (code OTP par SMS)
- [ ] Soumettre son KYC passager
- [ ] Chercher un trajet : point de départ, point d'arrivée, date, heure
- [ ] Voir le profil du conducteur : statut vérifié, note, taux de fiabilité, véhicule
- [ ] Demander une place
- [ ] Recevoir l'acceptation ou le refus (notification)
- [ ] Donner le code de départ au conducteur à la prise en charge
- [ ] Confirmer l'arrivée
- [ ] Noter le conducteur
- [ ] Partager son trajet en cours avec un proche
- [ ] Signaler un problème
- [ ] Recharger et consulter son portefeuille (si paiement en ligne retenu)

### Conducteur

Tout ce que fait le passager, plus :

- [ ] Soumettre son KYC conducteur (permis, carte grise ou assurance, photo du véhicule)
- [ ] Déclarer son véhicule : marque, couleur, immatriculation, nombre de places
- [ ] Publier un trajet : départ, arrivée, points de prise en charge, date, heure, places disponibles
- [ ] Voir le prix par place calculé automatiquement
- [ ] Accepter ou refuser les demandes
- [ ] Saisir le code de départ de chaque passager
- [ ] Clôturer le trajet
- [ ] Noter ses passagers
- [ ] Voir ses économies : par trajet et cumul du mois
- [ ] Retirer ses gains (si paiement en ligne retenu)

### Administrateur

- [ ] Valider ou rejeter les dossiers KYC, avec un motif de rejet
- [ ] Consulter les trajets, les réservations et les utilisateurs
- [ ] Traiter les signalements et les litiges
- [ ] Suspendre ou réactiver un compte
- [ ] Modifier les paramètres : prix du litre, grille de prix, frais de service, délais d'annulation
- [ ] Suivre les indicateurs : trajets, passagers transportés, économies réalisées, utilisateurs vérifiés

## KYC

Le niveau de vérification dépend du rôle. Dans le MVP, l'administrateur valide chaque dossier à la main.

| Rôle       | Pièces demandées                                                                     | Ce que le KYC débloque |
|------------|--------------------------------------------------------------------------------------|------------------------|
| Passager   | Téléphone vérifié (OTP), pièce d'identité, selfie                                    | Réserver une place     |
| Conducteur | Pièces du passager + permis de conduire, carte grise ou assurance, photo du véhicule | Publier un trajet      |

**Statuts d'un dossier** : non_verifie → en_attente → verifie ou rejete. Un dossier rejeté porte un motif et peut être soumis à nouveau.

**Règles d'accès**

- Sans compte : aucun accès.
- Compte avec téléphone vérifié : peut chercher et consulter les trajets.
- KYC passager verifie : peut réserver.
- KYC conducteur verifie et véhicule déclaré : peut publier des trajets.
- Compte suspendu : ne peut ni réserver ni publier ; ses réservations à venir sont annulées et remboursées.

**Stockage** : les pièces sont des données sensibles. Stockage privé (pas d'URL publique), accès réservé à l'administrateur, journalisation de chaque consultation.

## Trajets et recherche

Un trajet correspond quand le départ et l'arrivée du passager sont proches de ceux du conducteur et que l'heure tombe dans la même fenêtre. Les valeurs ci-dessous sont des paramètres modifiables par l'administrateur.

**Publication d'un trajet (conducteur)**

- Départ et arrivée : coordonnées GPS + libellé (quartier, repère connu).
- Points de prise en charge : 1 à 3 repères sur le chemin (carrefour, rond-point, station). Plus naturel à Lomé et plus sûr qu'une adresse précise.
- Date et heure de départ.
- Nombre de places disponibles (inférieur ou égal aux places du véhicule moins le conducteur).
- Le prix par place est calculé par l'application (voir Tarification), pas saisi librement.

**Règle de correspondance (MVP)**

| Critère                                                             | Valeur par défaut | Paramètre           |
|---------------------------------------------------------------------|-------------------|---------------------|
| Distance entre le départ du passager et un point de prise en charge | 1,5 km max        | rayon_depart_km     |
| Distance entre l'arrivée du passager et l'arrivée du conducteur     | 1,5 km max        | rayon_arrivee_km    |
| Écart entre l'heure souhaitée et l'heure de départ                  | 15 min max        | fenetre_horaire_min |
| Places restantes                                                    | au moins 1        | —                   |

Résultats triés par heure de départ la plus proche, puis par distance de marche.

**Calcul des distances**

- Distance par la route, jamais à vol d'oiseau : API Google Maps Directions (payante par requête) ou OSRM sur OpenStreetMap (gratuit, auto-hébergeable).
- La correspondance (rayons) peut se faire à vol d'oiseau en base (formule de Haversine ou PostGIS) pour aller vite ; seule la distance de facturation passe par la route.
- Un passager qui ne fait qu'une partie du trajet paie selon sa propre distance, de son point de prise en charge à son arrivée.

**Hors MVP** : passagers situés n'importe où sur l'itinéraire (pas seulement aux points de prise en charge), trajets réguliers automatiques.

## Réservation

Une réservation ne passe « en cours » que lorsque le conducteur saisit le code de départ donné par le passager : c'est la preuve que le passager est bien monté.

Cycle de vie (schéma de la spécification) :

```
demandee --accepte--> acceptee --code de départ saisi--> en_cours --conducteur clôture--> terminee --confirmation ou délai--> cloturee
demandee --refus--> refusee
demandee | acceptee --annulation--> annulee
acceptee --absence déclarée--> absent
terminee --problème signalé--> litige --arbitrage--> cloturee
```

cycle de vie d'une réservation · 9 statuts

L'annulation est possible depuis « Demandée » comme depuis « Acceptée », jusqu'au départ. Valeurs du champ statut : demandee, acceptee, refusee, annulee, absent, en_cours, terminee, litige, cloturee.

**Règles**

- À l'acceptation, une place est retirée de places_restantes ; elle est rendue en cas d'annulation ou de refus.
- Un code à 4 chiffres est généré à l'acceptation et affiché uniquement au passager.
- « Clôturée » intervient à la confirmation du passager ou automatiquement après delai_confirmation_auto_h heures sans signalement. Avec le portefeuille, c'est à ce moment que le conducteur est crédité.
- Chaque changement de statut envoie une notification (push, ou SMS si l'application est fermée) à l'autre partie.
- Un trajet passe à « complet » quand places_restantes = 0, et à « terminé » quand toutes ses réservations actives sont terminées.

## Tarification

Le prix par passager se situe entre deux repères : le coût du carburant du conducteur (plancher) et le prix des alternatives, zémidjan, taxi collectif et Gozem (plafond). Les montants visés vont de 200 à 500 F par passager.

**Plancher : coût du carburant**

Le super sans plomb est à 817 F CFA le litre depuis le 11 septembre 2026 ([Koaci](https://www.koaci.com/index.php/article/2026/09/11/togo/societe/togo-hausse-des-prix-du-carburant-le-super-sans-plomb-passe-a-817-f-cfa_200435.html)). Il a déjà changé deux fois en 2026 : le prix du litre est donc un paramètre, jamais une valeur en dur.

`coût au km = consommation (L/100 km) / 100 × prix du litre`

Avec 7,5 L/100 km en ville : environ 61 F par km, soit environ 610 F pour 10 km. Partagé entre le conducteur et 2 passagers, la part de chacun est d'environ 200 F.

**Plafond : prix des alternatives**

Dans Lomé, une courte course en taxi coûte environ 500 F, et les trajets plus longs en ville montent vers 1 500 à 2 500 F ([guide des transports au Togo](https://www.cyriljarnias.com/?p=41447)). Les prix des zémidjans sont négociés à chaque course. À compléter par le relevé terrain ci-dessous.

**Grille de prix par tranche de distance (à valider par le relevé)**

| Distance par la route | Prix par passager |
|-----------------------|-------------------|
| Moins de 5 km         | 200 F             |
| 5 à 10 km             | 300 F             |
| Plus de 10 km         | 500 F             |

Règle : le prix d'une tranche reste toujours sous le prix d'un zémidjan pour la même distance, idéalement autour de la moitié.

**Relevé terrain à faire par l'équipe**

- [ ] Choisir 10 à 15 itinéraires fréquents à Lomé (ex. Agoè–Grand Marché, Adidogomé–Université, Baguida–centre-ville)
- [ ] Pour chacun, noter la distance par la route (Google Maps)
- [ ] Noter le prix payé en zémidjan, en taxi collectif et sur Gozem (prix affiché avant commande)
- [ ] Calculer le coût carburant du conducteur avec la formule ci-dessus
- [ ] Ajuster la grille entre les deux repères

**Économies affichées au conducteur**

- Par trajet : somme payée par ses passagers.
- Par mois : cumul de ces sommes. C'est ce chiffre qui motive le conducteur ; à mettre en avant dans l'application.

## Paiement

Avec des montants de 200 à 500 F, un paiement Mobile Money par trajet coûte trop cher en frais. Le modèle retenu à terme est un portefeuille dans l'application ; le MVP peut démarrer en espèces.

**Option A : espèces (MVP rapide)**

- Le passager paie le conducteur en main propre au moment de la prise en charge.
- Le code de départ et les notes assurent la confiance.
- L'application enregistre le montant dû pour calculer les économies du conducteur.

**Option B : portefeuille (cible)**

1.  Le passager recharge son portefeuille par Mobile Money (T-Money, Flooz), par exemple 2 000 ou 5 000 F. Les frais ne sont payés qu'une fois.
1.  À la réservation, le prix est bloqué sur son solde (montant réservé, non débité).

2.  À la saisie du code de départ, le montant est débité du passager.

3.  À la clôture du trajet (confirmation du passager, ou automatique après le délai delai_confirmation_auto_h), le montant est crédité au conducteur.

4.  Le conducteur retire ses gains sur Mobile Money, à la demande ou automatiquement une fois par semaine, en un seul versement.

Chaque mouvement est une ligne dans un journal de transactions (recharge, blocage, déblocage, débit, crédit, retrait, remboursement). Le solde se calcule à partir de ce journal, il n'est jamais modifié directement.

**Contraintes**

- Kovoit détient l'argent des utilisateurs : passer par un agrégateur agréé (ex. PayGate Global, FedaPay, CinetPay) et vérifier le cadre BCEAO avant le lancement.
- Décider qui paie les frais de recharge et de retrait : passager, conducteur ou Kovoit.
- Montant minimum de recharge et de retrait : paramètres administrateur.

## Annulations et fiabilité

Avec des montants aussi petits, les pénalités financières pèsent peu. Ce qui compte en ville, c'est la fiabilité : elle est affichée sur chaque profil et peut mener à une suspension.

| Situation                                                               | Conséquence                                                                                 |
|-------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| Passager annule plus de 30 min avant le départ                          | Gratuit, montant débloqué                                                                   |
| Passager annule moins de 30 min avant                                   | Gratuit, mais compte comme annulation tardive                                               |
| Passager absent (code jamais saisi, conducteur au point de rendez-vous) | Le passager paie le trajet, compte comme absence                                            |
| Conducteur annule                                                       | Passagers débloqués ou remboursés, compte comme annulation tardive si moins de 30 min avant |
| Litige signalé après le trajet                                          | Montant gelé, l'administrateur tranche                                                      |

**Taux de fiabilité**

\text{fiabilité} = 1 - \frac{\text{annulations tardives} + \text{absences}}{\text{réservations sur les 30 derniers jours}}

Affiché en pourcentage sur le profil. Au-delà de seuil_incidents annulations tardives ou absences sur 30 jours (3 par défaut), suspension temporaire de duree_suspension_j jours (7 par défaut).

**Preuve d'absence** : le conducteur déclare l'absence depuis le point de prise en charge, après l'heure de départ + tolerance_retard_min (10 min par défaut). La position GPS du conducteur est enregistrée avec la déclaration.

## Modèle économique

Pendant le pilote, Kovoit ne prélève rien : l'objectif est d'attirer conducteurs et passagers. L'application prévoit dès le MVP un paramètre de frais de service, désactivé par défaut.

**Revenu par passager selon le mode de prélèvement**

| Prix payé | Commission 10 % | Commission 15 % | Frais fixes 50 F |
|-----------|-----------------|-----------------|------------------|
| 200 F     | 20 F            | 30 F            | 50 F             |
| 300 F     | 30 F            | 45 F            | 50 F             |
| 500 F     | 50 F            | 75 F            | 50 F             |

Les frais fixes ajoutés au prix du passager sont préférables : plus simples, plus rentables sur des petits montants, et ils ne réduisent pas l'économie du conducteur. Dans les applications de transport, la commission courante est de 12 à 18 %, 15 % étant un point d'équilibre en 2026 ([Kolonell](https://kolonell.com/fr/blog/app-taxi-moto-vtc-lome-cout-2026)).

**Projection mensuelle** (hypothèse : 2 passagers par trajet, aller-retour, 22 jours, 45 F par passager)

| Conducteurs actifs | Trajets passagers par mois | Revenu mensuel |
|--------------------|----------------------------|----------------|
| 50                 | 4 400                      | ~200 000 F     |
| 200                | 17 600                     | ~790 000 F     |
| 500                | 44 000                     | ~1 980 000 F   |

Ce revenu doit couvrir serveur, SMS (OTP), cartographie, frais de l'agrégateur et validation KYC. Avec quelques dizaines de conducteurs, Kovoit n'est pas rentable : c'est normal pour un pilote.

**Sources de revenus à terme**

- Frais de service par passager (grand public).
- Abonnement entreprises et écoles : covoiturage domicile-travail entre employés ou étudiants. Source principale visée.
- Abonnement conducteur premium (trajets mis en avant, trajets réguliers), une fois le volume atteint.

## Sécurité

- Notes après chaque trajet, des deux côtés (1 à 5 étoiles + commentaire optionnel).
- Bouton « Partager mon trajet » : lien public temporaire avec la position du véhicule, valable jusqu'à la clôture.
- Bouton « Signaler un problème », pendant et après le trajet, vers l'administrateur.
- Code de départ à 4 chiffres par réservation, stocké haché, jamais affiché au conducteur.
- Photo et immatriculation du véhicule visibles par le passager avant la prise en charge.

## Place de l'IA

Le MVP n'utilise pas d'IA : la correspondance, le prix, les statuts et la fiabilité sont des règles. Le seul vrai cas d'IA est la vérification automatique du KYC (lecture de la pièce d'identité par OCR, comparaison du selfie avec la photo), à prévoir quand le volume d'inscriptions dépasse la validation manuelle.

## Hors MVP (V2)

- Passagers pris n'importe où sur l'itinéraire
- Trajets réguliers (« tous les jours à 7 h »)
- Portefeuille et Mobile Money, si le MVP démarre en espèces
- Messagerie intégrée
- Vérification automatique du KYC
- Offre entreprises et écoles
- Trajets entre villes

## Modèle de données

| Table                  | Champs principaux                                                                                                                                                                                    |
|------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| users                  | id, telephone (unique), nom, prenom, photo, mode_actif (passager, conducteur), statut_compte (actif, suspendu), suspendu_jusqu_au, cree_le                                                           |
| kyc_dossiers           | id, user_id, type (passager, conducteur), statut (non_verifie, en_attente, verifie, rejete), motif_rejet, soumis_le, traite_le, traite_par                                                           |
| kyc_pieces             | id, dossier_id, type_piece (identite, selfie, permis, carte_grise, assurance, photo_vehicule), chemin_fichier privé                                                                                  |
| vehicules              | id, user_id, marque, modele, couleur, immatriculation, nb_places                                                                                                                                     |
| trajets                | id, conducteur_id, vehicule_id, depart (lat, lng, libelle), arrivee (lat, lng, libelle), depart_le, places_total, places_restantes, distance_km, statut (publie, complet, en_cours, termine, annule) |
| points_prise_en_charge | id, trajet_id, ordre, lat, lng, libelle                                                                                                                                                              |
| reservations           | id, trajet_id, passager_id, point_id, arrivee (lat, lng), distance_km, prix, frais_service, statut, code_depart_hash, horodatages par statut                                                         |
| notes                  | id, reservation_id, auteur_id, cible_id, note (1 à 5), commentaire                                                                                                                                   |
| signalements           | id, reservation_id, auteur_id, cible_id, motif, statut (ouvert, traite), resolution                                                                                                                  |
| transactions           | id, user_id, type (recharge, blocage, deblocage, debit, credit, retrait, remboursement), montant, reservation_id, reference_externe, statut, cree_le                                                 |
| parametres             | cle, valeur, modifie_le, modifie_par                                                                                                                                                                 |

## Paramètres administrateur (valeurs de départ)

| Clé                       | Valeur                                             | Rôle                        |
|---------------------------|----------------------------------------------------|-----------------------------|
| prix_litre                | 817 F                                              | Calcul du coût au km        |
| conso_l_100km             | 7,5                                                | Calcul du coût au km        |
| grille_prix               | \<5 km : 200 F · 5–10 km : 300 F · \>10 km : 500 F | Prix par passager           |
| frais_service             | 0 F                                                | Désactivé pendant le pilote |
| rayon_depart_km           | 1,5                                                | Correspondance              |
| rayon_arrivee_km          | 1,5                                                | Correspondance              |
| fenetre_horaire_min       | 15                                                 | Correspondance              |
| delai_annulation_min      | 30                                                 | Annulation tardive          |
| tolerance_retard_min      | 10                                                 | Déclaration d'absence       |
| delai_confirmation_auto_h | 3                                                  | Clôture automatique         |
| seuil_incidents           | 3 sur 30 jours                                     | Suspension                  |
| duree_suspension_j        | 7                                                  | Suspension                  |

## Questions ouvertes

- [ ] MVP en espèces ou portefeuille dès le départ ?
- [ ] Cadre légal du covoiturage avec partage de frais au Togo
- [ ] Agrégateur de paiement retenu et frais réels
- [ ] Google Maps ou OSRM pour les distances
- [ ] Résultats du relevé terrain pour valider la grille de prix