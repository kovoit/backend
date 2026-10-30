# API Kovoit — contrat pour les clients (mobile Flutter, admin React)

> Périmètre actuel de ce dossier : **seulement les routes touchées par la mission M-003**
> (tracé du trajet, filtre par type de véhicule, photo de profil). Le reste de l'API est
> décrit par le schéma OpenAPI (`/api/docs/`) et par `PRD.md` §15.

## Index

| Fichier | Routes |
|---|---|
| [`trajets.md`](trajets.md) | `POST /api/v1/trajets/` · `GET /api/v1/trajets/{id}/` · `GET /api/v1/trajets/recherche/` |
| [`profil.md`](profil.md) | `PATCH /api/v1/moi/` (photo de profil) · règle des URL de `photo` sur toutes les routes |
| [`CHANGELOG.md`](CHANGELOG.md) | Modifications du contrat (cassantes signalées) |

## Règle d'or côté client

Le client **ne calcule jamais** le prix, la distance, la durée, la fiabilité ni un statut :
il **affiche** ce que renvoie l'API. Le tracé (`trace`) sert uniquement à dessiner la route
sur la carte.

## Authentification

1. `POST /api/v1/auth/otp/demander/` `{ "email": … }` : un code à 6 chiffres part par email.
2. `POST /api/v1/auth/otp/verifier/` `{ "email": …, "code": "123456" }` : renvoie
   `access` (15 min) et `refresh` (7 jours).
3. Chaque requête porte l'en-tête `Authorization: Bearer <access>`.
4. `access` expiré : `POST /api/v1/auth/jeton/rafraichir/` `{ "refresh": … }`.

Les routes décrites ici exigent un compte connecté **avec email vérifié**.

## Enveloppe de réponse (toutes les routes)

Succès :

```json
{ "statut": "success", "message": "Trajet récupéré.", "reponse": { "id": "…" } }
```

Échec :

```json
{
  "statut": "failed",
  "message": "Les données envoyées sont invalides.",
  "reponse": { "code": "DONNEES_INVALIDES", "erreurs": { "type_vehicule": ["…"] } }
}
```

- `statut` : `"success"` ou `"failed"` uniquement.
- `message` : phrase en français, affichable telle quelle à l'utilisateur.
- `reponse` en échec : `code` (stable, à tester par le client) et `erreurs` (détail champ
  par champ pour `DONNEES_INVALIDES`, sinon `null`).
- Le **code HTTP** reste significatif (200, 201, 400, 401, 403, 404, 409, 429, 500).
- Ne jamais comparer le texte de `message` ni des `erreurs` : seulement `reponse.code`.

## Pagination

Les listes paginées renvoient dans `reponse` : `{ "count", "next", "previous", "results" }`
(20 éléments par page). **Note** : `GET /trajets/recherche/` n'est **pas** paginée,
`reponse` est directement une liste.

## Formats

- Dates : ISO 8601 en UTC. L'API écrit le suffixe `Z` (`2026-10-31T07:30:00Z`), équivalent
  à `+00:00` ; le client doit accepter les deux à la lecture et peut envoyer l'un ou l'autre.
- Montants : entiers en F CFA (`prix_place: 365`).
- `distance_km` : chaîne décimale (`"9.97"`), à afficher, pas à recalculer.
- Coordonnées : nombres décimaux, latitude puis longitude.
- Images (`photo`) : **URL relatives** (`/media/…`) ou `null` ; voir [`profil.md`](profil.md).

## Codes d'erreur génériques

| HTTP | `reponse.code` | `message` (exemple réel) | Quand |
|---|---|---|---|
| 400 | `DONNEES_INVALIDES` | `Les données envoyées sont invalides.` | Champ manquant / invalide ; détail dans `erreurs` |
| 400 | `REQUETE_MALFORMEE` | `Le corps de la requête n'est pas un JSON valide.` | JSON illisible |
| 401 | `NON_AUTHENTIFIE` | `Informations d'authentification non fournies.` | En-tête `Authorization` absent |
| 401 | `AUTHENTIFICATION_ECHOUEE` | `Session invalide ou expirée. Reconnectez-vous.` | Jeton invalide ou expiré : rafraîchir |
| 403 | `EMAIL_NON_VERIFIE` | `Vérifiez votre adresse email pour accéder à ce service.` | Email non vérifié |
| 403 | `COMPTE_SUSPENDU` | `Votre compte est suspendu : action impossible.` | Compte suspendu (publication) |
| 403 | `ACCES_REFUSE` | variable | Autre refus d'accès |
| 404 | `RESSOURCE_INTROUVABLE` | `Trajet introuvable.` | Ressource absente ou non accessible |
| 405 | `METHODE_NON_AUTORISEE` | variable | Mauvaise méthode HTTP |
| 415 | `FORMAT_NON_SUPPORTE` | variable | `Content-Type` refusé |
| 429 | `TROP_DE_REQUETES` | variable | Limite de débit atteinte |
| 500 | `ERREUR_INTERNE` | `Une erreur interne est survenue. Réessayez plus tard.` | Incident serveur |

Les codes propres à une route (ex. `CONDUCTEUR_NON_HABILITE`, `DEPART_PASSE`) sont listés
dans le fichier de la route.

## Machine à états de la réservation (rappel)

```
demandee → acceptee | refusee | annulee
acceptee → en_cours (code de départ saisi par le conducteur) | annulee | absent
en_cours → terminee
terminee → cloturee | litige
litige   → cloturee (décision admin)
```

Le statut est toujours celui renvoyé par l'API ; le client ne le déduit jamais.

## Régénérer et valider le schéma OpenAPI

`schema.yml` n'est **pas** versionné (`.gitignore`). Pour le produire localement, depuis
`backend/` :

```bash
python manage.py spectacular --file schema.yml --validate
```

La commande échoue si le schéma est invalide. Documentation interactive (serveur lancé) :
`/api/docs/`.
