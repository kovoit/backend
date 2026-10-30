# Changelog du contrat d'API

Format : date, mission, routes. **CASSANT** = un client existant peut se tromper sans mise à jour.

## 2026-10-30 — M-004 (connexion par e-mail + mot de passe)

Voir [`auth.md`](auth.md).

- **Ajout** de 6 routes publiques : `POST auth/inscription/` (201 `CODE_ENVOYE`, aucun jeton),
  `auth/inscription/verifier/` (`SESSION`), `auth/inscription/renvoyer-code/`,
  `auth/connexion/` (`SESSION` ; 5/min par IP), `auth/mot-de-passe/oublie/`,
  `auth/mot-de-passe/reinitialiser/` (aucun jeton, toutes les sessions révoquées).
  Nouveaux codes : `EMAIL_DEJA_UTILISE` (409), `MOT_DE_PASSE_FAIBLE` (400),
  `IDENTIFIANTS_INVALIDES` (401), `EMAIL_NON_VERIFIE` (403, sur `connexion/`).
- **CASSANT (admin React)** : 403 `CANAL_WEB_REQUIS` sur `/api/v1/admin/…` et
  `GET auth/admin/moi/` pour un administrateur dont le jeton n'a pas été émis par
  `auth/admin/connexion/` (ex. jeton de l'application). Un jeton du back-office ouvert avant
  ce déploiement peut être refusé : se reconnecter.
- **CASSANT (déconnexion)** : `POST auth/deconnexion/` renvoie 403 `JETON_AUTRE_COMPTE` si le
  `refresh` envoyé appartient à un autre compte (il n'est plus révoqué).
- **Validation** : `maxLength: 254` sur tous les champs `email` d'entrée ; au-delà, 400
  `DONNEES_INVALIDES` (`erreurs.email`) au lieu d'une erreur 500.
- **Dépréciées** : `POST auth/otp/demander/` et `auth/otp/verifier/`, inchangées jusqu'à leur
  retrait après la migration du mobile (D-70).
- **Démo** : les comptes `seed_demo` et `seed_backoffice` ont le mot de passe `Kovoit-Demo-2026`.

## 2026-10-30 — M-003 (démo : tracé, filtre véhicule, photo)

Aucune modification cassante.

- **Ajout** `trace` (objet ou `null`) dans `GET /api/v1/trajets/{id}/` et dans la réponse
  201 de `POST /api/v1/trajets/` : `{source: "routage" | "estimation", points: [[lat, lng], …]}`.
  `null` pour les trajets publiés avant l'ajout. Aucun nouveau code d'erreur.
  Voir [`trajets.md`](trajets.md).
- **Ajout** paramètre facultatif `type_vehicule` (`voiture` | `moto`) sur
  `GET /api/v1/trajets/recherche/`. Absent ou vide : comportement inchangé (tous les types).
  Toute autre valeur : 400 `DONNEES_INVALIDES` avec `erreurs.type_vehicule`.
- **Précision (pas de changement backend)** : `photo` est une URL **relative** (`/media/…`)
  sur toutes les routes (`/moi/`, `otp/verifier`, recherche, détail, profil public). Le
  client la préfixe avec l'origine de l'API. Voir [`profil.md`](profil.md).
- **Inchangés** : `distance_km`, `duree_min`, `prix_place`, `prix_passager`,
  `tarification`, `POST /trajets/estimation/`. Ils restent calculés départ → arrivée et ne
  suivent pas encore le tracé (D-21, reporté après la démo).
- **Schéma OpenAPI** : descriptions ajoutées (`trace` de la 201 de publication,
  `type_vehicule`, `photo`) ; aucun champ ni comportement modifié.
