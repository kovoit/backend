# Changelog du contrat d'API

Format : date, mission, routes. **CASSANT** = un client existant peut se tromper sans mise à jour.

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
