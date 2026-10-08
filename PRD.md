# PRD — Kovoit Backend (MVP)

> Source : `docs/Kovoit_Spécification_du_MVP.docx`, adaptée aux décisions de l'équipe (voir §2).
> Ce document est la **source de vérité métier**. Les règles techniques sont dans `CLAUDE.md`.

---

## 1. Vision

Kovoit met en relation des conducteurs qui font **déjà** un trajet en ville à Lomé avec des passagers qui vont dans la même direction. Le conducteur réduit ses frais de carburant, le passager paie moins cher qu'un zémidjan ou un taxi.

- **Périmètre :** trajets **urbains à Lomé** uniquement.
- **Partage de frais, pas de profit :** Kovoit n'est pas un service de taxi.
- **Prix fixe et connu à l'avance :** aucune négociation.
- **Un seul compte, deux modes :** passager le matin, conducteur le soir.
- **Trois types d'utilisateurs :** passager, conducteur, administrateur.
- **Pas d'IA dans le MVP :** correspondance, statuts et fiabilité sont des règles.

## 2. Décisions d'équipe (écarts avec la spec d'origine)

| Sujet | Spec d'origine | Décision MVP |
|---|---|---|
| Vérification du compte | OTP par SMS | **OTP par email via Gmail SMTP**. Téléphone obligatoire mais non vérifié |
| Notifications | Push, SMS si app fermée | Push, **email** si app fermée |
| Tarification | Grille 200 / 300 / 500 F par tranche | **À définir plus tard** — prix temporaire = paramètre `prix_simulation` |
| Paiement | Espèces ou portefeuille | **Portefeuille simulé** (aucun argent réel) |
| Distances | Google Maps ou OSRM | **OSRM** |
| Périmètre de ce dépôt | — | **Backend uniquement** (API pour Flutter et admin React) |

## 3. Rôles et fonctionnalités

### Passager
- Créer un compte (email + OTP), renseigner téléphone, nom, prénom, photo.
- Soumettre son KYC passager.
- Chercher un trajet : départ, arrivée, date, heure.
- Voir le profil du conducteur : statut vérifié, note moyenne, taux de fiabilité, véhicule.
- Demander une place ; recevoir l'acceptation ou le refus.
- Voir son code de départ et le donner au conducteur à la prise en charge.
- Confirmer l'arrivée ; noter le conducteur ; signaler un problème.
- Partager son trajet en cours avec un proche.
- Recharger (simulé) et consulter son portefeuille.

### Conducteur (tout ce que fait le passager, plus)
- Soumettre son KYC conducteur ; déclarer son véhicule.
- Publier un trajet : départ, arrivée, 1 à 3 points de prise en charge, date, heure, places.
- Voir le prix par place (renvoyé par l'API).
- Accepter / refuser les demandes ; saisir le code de départ de chaque passager.
- Déclarer un passager absent ; clôturer le trajet ; noter ses passagers.
- Voir ses économies : par trajet et cumul du mois.
- Retirer ses gains (simulé).

### Administrateur (API `/api/v1/admin/` pour l'admin React)
- Valider / rejeter les dossiers KYC avec motif.
- Consulter trajets, réservations, utilisateurs.
- Traiter signalements et litiges.
- Suspendre / réactiver un compte.
- Modifier les paramètres.
- Suivre les indicateurs : trajets, passagers transportés, économies réalisées, utilisateurs vérifiés.

## 4. Compte, authentification et KYC

**Authentification :** email + code OTP à 6 chiffres envoyé par Gmail SMTP → JWT. Code haché, durée de vie, essais et renvois limités par paramètres.

**KYC (validation manuelle par l'admin)**

| Rôle | Pièces | Débloque |
|---|---|---|
| Passager | Email vérifié, pièce d'identité, selfie | Réserver |
| Conducteur | Pièces passager + permis, carte grise ou assurance, photo du véhicule | Publier (avec véhicule déclaré) |

Statuts d'un dossier : `non_verifie → en_attente → verifie | rejete`. Un dossier rejeté porte un motif et peut être soumis à nouveau.

**Stockage des pièces :** privé (aucune URL publique), accès réservé à l'admin via un endpoint authentifié, **chaque consultation journalisée**.

**Règles d'accès**
- Sans compte : aucun accès (sauf lien public de partage).
- Email vérifié : chercher et consulter les trajets.
- KYC passager `verifie` : réserver.
- KYC conducteur `verifie` + véhicule déclaré : publier.
- Compte suspendu : ni réserver ni publier ; réservations à venir annulées et remboursées.

## 5. Trajets et recherche

**Publication**
- Départ et arrivée : coordonnées GPS + libellé (quartier, repère).
- 1 à 3 points de prise en charge (carrefour, rond-point, station), ordonnés.
- Date et heure de départ.
- Places ≤ places du véhicule − 1 (le conducteur).
- `distance_km` calculée par la route (OSRM) et stockée.

**Correspondance (paramétrable)**

| Critère | Défaut | Paramètre |
|---|---|---|
| Départ passager ↔ un point de prise en charge | ≤ 1,5 km | `rayon_depart_km` |
| Arrivée passager ↔ arrivée conducteur | ≤ 1,5 km | `rayon_arrivee_km` |
| Écart heure souhaitée / heure de départ | ≤ 15 min | `fenetre_horaire_min` |
| Places restantes | ≥ 1 | — |

Correspondance à vol d'oiseau (Haversine, pré-filtre lat/lng en base). Résultats triés par heure de départ la plus proche, puis par distance de marche.

**Statuts du trajet :** `publie → complet (places_restantes = 0) → en_cours → termine` ; `annule` avant départ. Un trajet est `termine` quand toutes ses réservations actives sont terminées.

## 6. Réservation

**9 statuts :** `demandee, acceptee, refusee, annulee, absent, en_cours, terminee, litige, cloturee`.

```
demandee → acceptee | refusee | annulee
acceptee → en_cours | annulee | absent
en_cours → terminee
terminee → cloturee | litige
litige   → cloturee (décision admin)
```

**Règles**
- À l'acceptation : une place retirée de `places_restantes` ; rendue en cas d'annulation (le refus ne concerne qu'une demande non encore comptée).
- À l'acceptation : code de départ à **4 chiffres** généré, jamais stocké : dérivé par HMAC-SHA256 d'un sel propre à la réservation et de SECRET_KEY (`reservations/code_depart.py`), affiché **uniquement au passager**.
- `en_cours` uniquement quand le conducteur saisit le bon code (preuve de montée).
- `cloturee` à la confirmation du passager ou automatiquement après `delai_confirmation_auto_h` sans signalement.
- Chaque changement de statut notifie l'autre partie (push, sinon email).
- Chaque statut est horodaté.

## 7. Prix et paiement (simulation)

- **Prix :** algorithme à définir plus tard. En attendant, `prix = prix_simulation` (paramètre) et `frais_service = frais_service` (paramètre, 0 pendant le pilote). Le prix est **toujours fixé par le backend**, jamais saisi par le conducteur ni recalculé par le client.
- **Portefeuille simulé :** aucun argent réel, provider `Simulation`.

| Événement | Mouvements |
|---|---|
| Recharge (simulée) | `recharge` |
| Demande de place | `blocage` du prix sur le solde passager (refus si solde disponible insuffisant) |
| Refus / annulation | `deblocage` |
| Code de départ saisi | `deblocage` + `debit` passager |
| Clôture | `credit` conducteur |
| Absence | `deblocage` + `debit` passager + `credit` conducteur |
| Litige | montant gelé jusqu'à décision admin (`credit` conducteur ou `remboursement` passager) |
| Retrait (simulé) | `retrait` conducteur |

Le solde n'est jamais stocké : il est calculé depuis le journal des transactions.

**Économies conducteur :** par trajet = somme payée par ses passagers ; par mois = cumul.

## 8. Annulations et fiabilité

| Situation | Conséquence |
|---|---|
| Passager annule > `delai_annulation_min` avant départ | Gratuit, montant débloqué |
| Passager annule < `delai_annulation_min` avant départ | Gratuit, compte comme **annulation tardive** |
| Passager absent | Le passager paie, compte comme **absence** |
| Conducteur annule | Passagers débloqués / remboursés ; annulation tardive si < délai |
| Litige après trajet | Montant gelé, l'admin tranche |

**Fiabilité** = `1 − (annulations tardives + absences) / réservations des 30 derniers jours`, affichée en %.
Au-delà de `seuil_incidents` incidents sur 30 jours : suspension de `duree_suspension_j` jours.

**Déclaration d'absence :** par le conducteur, après `heure de départ + tolerance_retard_min`, **position GPS enregistrée** avec la déclaration.

## 9. Sécurité et confiance

- Notes après chaque trajet, des deux côtés (1 à 5 + commentaire optionnel), une seule par réservation et par auteur.
- « Partager mon trajet » : lien public temporaire (jeton) avec position du véhicule, valable jusqu'à la clôture.
- « Signaler un problème » pendant et après le trajet.
- Code de départ jamais stocké (dérivé par HMAC), jamais montré au conducteur.
- Photo et immatriculation du véhicule visibles avant la prise en charge.

## 10. Modèle de données

| Table | Champs principaux |
|---|---|
| `users` | id, email (unique), telephone, nom, prenom, photo, email_verifie, mode_actif (passager, conducteur), statut_compte (actif, suspendu), suspendu_jusqu_au, cree_le |
| `otp_codes` | id, email, code_hash, expire_le, essais, utilise, cree_le |
| `kyc_dossiers` | id, user_id, type (passager, conducteur), statut, motif_rejet, soumis_le, traite_le, traite_par |
| `kyc_pieces` | id, dossier_id, type_piece (identite, selfie, permis, carte_grise, assurance, photo_vehicule), fichier privé |
| `kyc_consultations` | id, piece_id, admin_id, consulte_le |
| `vehicules` | id, user_id, marque, modele, couleur, immatriculation (unique), nb_places, photo |
| `trajets` | id, conducteur_id, vehicule_id, depart (point, libelle), arrivee (point, libelle), depart_le, places_total, places_restantes, distance_km, statut |
| `points_prise_en_charge` | id, trajet_id, ordre (1–3), position, libelle |
| `reservations` | id, trajet_id, passager_id, point_id, arrivee (point), distance_km, prix, frais_service, statut, code_depart_sel, essais_code, horodatages par statut, position_absence |
| `notes` | id, reservation_id, auteur_id, cible_id, note (1–5), commentaire |
| `signalements` | id, reservation_id, auteur_id, cible_id, motif, statut (ouvert, traite), resolution |
| `transactions` | id, user_id, type, montant, reservation_id, reference_externe, statut, cree_le |
| `liens_partage` | id, reservation_id, jeton (unique), expire_le |
| `parametres` | cle, valeur, modifie_le, modifie_par |

## 11. Paramètres (valeurs de départ)

| Clé | Valeur | Rôle |
|---|---|---|
| `prix_simulation` | 300 F | Prix temporaire par passager |
| `frais_service` | 0 F | Désactivé pendant le pilote |
| `rayon_depart_km` | 1,5 | Correspondance |
| `rayon_arrivee_km` | 1,5 | Correspondance |
| `fenetre_horaire_min` | 15 | Correspondance |
| `delai_annulation_min` | 30 | Annulation tardive |
| `tolerance_retard_min` | 10 | Déclaration d'absence |
| `delai_confirmation_auto_h` | 3 | Clôture automatique |
| `seuil_incidents` | 3 | Suspension |
| `periode_incidents_j` | 30 | Période de calcul de la fiabilité et des incidents |
| `duree_suspension_j` | 7 | Suspension |
| `otp_validite_min` | 10 | OTP email |
| `otp_max_essais` | 5 | OTP email |
| `otp_delai_renvoi_s` | 60 | OTP email |
| `otp_max_par_heure` | 5 | OTP email |
| `code_depart_max_essais` | 5 | Code de départ |
| `recharge_min` / `retrait_min` | 500 F | Portefeuille simulé |

## 12. Critères d'acceptation

- **CA1 Inscription :** étant donné un email valide, quand l'utilisateur demande un code, alors un OTP est envoyé par email ; quand il saisit le bon code avant expiration, alors son email est vérifié et il reçoit un JWT. Au-delà de `otp_max_essais`, le code est invalidé.
- **CA2 KYC :** quand l'utilisateur soumet ses pièces, le dossier passe `en_attente` ; l'admin le passe `verifie` ou `rejete` (motif obligatoire) ; un dossier rejeté peut être resoumis. Chaque consultation de pièce est journalisée.
- **CA3 Publication :** un conducteur sans KYC conducteur `verifie` ou sans véhicule reçoit `403`. Sinon le trajet est créé `publie` avec `places_restantes = places`, 1 à 3 points, places ≤ nb_places − 1.
- **CA4 Recherche :** un utilisateur à email vérifié obtient les trajets respectant rayons, fenêtre horaire et places ≥ 1, triés par heure puis distance de marche, avec conducteur, photo, statut vérifié, note, fiabilité, véhicule, heure, places, prix.
- **CA5 Demande :** un passager KYC `verifie` avec solde disponible suffisant crée une réservation `demandee` et un `blocage` ; le conducteur est notifié. Sinon `403` / `409`.
- **CA6 Acceptation :** la réservation passe `acceptee`, une place est retirée (jamais < 0, même en concurrence), un code de départ est généré, le passager est notifié. Le trajet passe `complet` si plus de place.
- **CA7 Refus :** la réservation passe `refusee`, `deblocage`, passager notifié.
- **CA8 Annulation :** possible depuis `demandee` ou `acceptee` jusqu'au départ ; place rendue si acceptée ; `deblocage` ; annulation tardive comptée si < `delai_annulation_min` ; l'autre partie est notifiée.
- **CA9 Départ :** le bon code fait passer `en_cours` (`deblocage` + `debit`) ; un mauvais code incrémente les essais ; le code n'apparaît dans aucune réponse destinée au conducteur.
- **CA10 Absence :** déclarable seulement après `depart_le + tolerance_retard_min`, avec position GPS ; statut `absent`, le passager paie, absence comptée.
- **CA11 Clôture :** fin de trajet → `terminee` ; confirmation passager ou délai `delai_confirmation_auto_h` sans signalement → `cloturee` + `credit` conducteur. Un signalement fait passer `litige`, montant gelé.
- **CA12 Fiabilité / suspension :** au-delà de `seuil_incidents` sur 30 jours, le compte est suspendu `duree_suspension_j` jours, ses réservations à venir annulées et remboursées.
- **CA13 Format de réponse :** toute réponse de l'API respecte `{ "statut": "success" | "failed", "message": "...", "reponse": ... }`.

## 13. Hors périmètre MVP

Algorithme de prix définitif, paiement réel (Mobile Money, agrégateur), passagers pris n'importe où sur l'itinéraire, trajets récurrents, messagerie, KYC automatique / OCR, offre entreprises et écoles, abonnement conducteur, trajets interurbains, vérification du téléphone par SMS.

## 14. Questions ouvertes

- Algorithme / grille de prix définitive (relevé terrain à faire).
- Cadre légal du covoiturage avec partage de frais au Togo.
- Agrégateur de paiement réel et frais (FedaPay, CinetPay, PayGate) — cadre BCEAO.
- Fournisseur email transactionnel si la limite Gmail (~500/jour) est dépassée.
- Fournisseur push (FCM confirmé ?).

## 15. Contrat d'API (implémenté)

Préfixe `/api/v1/`. Toutes les réponses : `{ "statut": "success" | "failed", "message", "reponse" }`. Documentation interactive : `/api/docs/`.

| Domaine | Endpoints |
|---|---|
| Authentification | `POST auth/otp/demander/` · `POST auth/otp/verifier/` · `POST auth/jeton/rafraichir/` · `POST auth/deconnexion/` |
| Profil | `GET/PATCH moi/` · `PATCH moi/mode/` · `GET moi/economies/` · `GET utilisateurs/{id}/` |
| KYC | `GET kyc/` · `POST kyc/{type}/pieces/` · `POST kyc/{type}/soumettre/` |
| Véhicules | `GET/POST vehicules/` · `GET/PATCH/DELETE vehicules/{id}/` |
| Trajets | `POST trajets/` · `GET trajets/recherche/` · `GET trajets/mes-trajets/` · `GET trajets/{id}/` · `GET trajets/{id}/reservations/` · `POST trajets/{id}/position/` · `POST trajets/{id}/terminer/` · `POST trajets/{id}/annuler/` |
| Réservations | `GET/POST reservations/` · `GET reservations/{id}/` · `POST reservations/{id}/accepter/` · `refuser/` · `annuler/` · `code-depart/` · `absent/` · `confirmer-arrivee/` · `note/` · `signalement/` · `partage/` |
| Partage (public) | `GET partage/{jeton}/` |
| Portefeuille (simulé) | `GET portefeuille/` · `GET portefeuille/transactions/` · `POST portefeuille/recharger/` · `POST portefeuille/retirer/` |
| Notifications | `POST notifications/appareils/` · `DELETE notifications/appareils/{jeton}/` |
| Admin (`admin/…`) | `utilisateurs/` (+ `{id}/`, `suspendre/`, `reactiver/`) · `kyc/` (+ `{id}/`, `valider/`, `rejeter/`, `pieces/{id}/fichier/`) · `trajets/` · `reservations/` · `signalements/` (+ `{id}/traiter/`) · `indicateurs/` · `parametres/` (+ `{cle}/`) |
