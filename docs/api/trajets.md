# Trajets — routes touchées par M-003

Enveloppe, authentification et erreurs génériques : voir [`README.md`](README.md).
Le client **affiche** `prix_place`, `prix_passager`, `distance_km`, `duree_min`, `statut`
et `trace` tels que renvoyés : il ne les calcule jamais.

> **Limite connue (D-21, reporté après la démo)** : `distance_km`, `duree_min`,
> `prix_place` et `prix_passager` sont calculés **départ → arrivée en direct**, sans passer
> par les carrefours. Ils **ne suivent pas encore le tracé** affiché. Ne pas les recalculer
> à partir de `trace`.

## Champ `trace` (contrat C1)

| Champ | Type | Règle |
|---|---|---|
| `trace` | objet ou `null` | Toujours présent dans le détail et la 201 de publication. `null` : trajet publié avant l'ajout du tracé |
| `trace.source` | `"routage"` \| `"estimation"` | `routage` : itinéraire par la route ; `estimation` : service de routage indisponible, segments droits départ → carrefour 1 → 2 → 3 → arrivée |
| `trace.points` | liste de paires `[lat, lng]` | ≥ 2 points, 5 décimales max, du départ à l'arrivée via les carrefours dans l'ordre `ordre`. En `estimation` : exactement `[départ, carrefours…, arrivée]` |

- Ordre **`[lat, lng]`** (latitude d'abord), déjà converti par le backend.
- `trace` est **absent** de `GET /trajets/recherche/`, `GET /trajets/mes-trajets/` et des
  réponses de `position/`, `terminer/`, `annuler/`.
- **Aucun nouveau code d'erreur** : la publication n'échoue jamais à cause du tracé.
- `trace: null` : le client dessine la carte sans tracé (marqueurs seulement).

Exemple `estimation` (routage indisponible, 1 carrefour) :

```json
"trace": {"source": "estimation", "points": [[6.1745, 1.169], [6.175, 1.17], [6.13, 1.222]]}
```

## `GET /api/v1/trajets/{id}/` — détail d'un trajet

**Permission** : connecté, email vérifié (aucun KYC requis pour consulter).

**Paramètres de requête (facultatifs, ensemble)** : `point_id` (UUID d'un point du trajet),
`arrivee_lat`, `arrivee_lng` (nombres). Les trois présents : `prix_passager` = prix pour ce
point et cette arrivée ; sinon `prix_passager` = `prix_place`.

**200** — sortie réelle du serializer (`TrajetDetailSerializer`) :

```json
{
  "statut": "success",
  "message": "Trajet récupéré.",
  "reponse": {
    "id": "f93ab320-6e02-4397-928e-c65bd58f4244",
    "conducteur": {
      "id": "38c0d517-81ec-4db7-8e5e-7600840953d3",
      "prenom": "Kodjo",
      "nom": "Amegah",
      "photo": "/media/photos_profil/moi.jpg",
      "confiance": {"note_moyenne": null, "nombre_notes": 0, "fiabilite_pct": 100,
                    "passager_verifie": false, "conducteur_verifie": true}
    },
    "vehicule": {"id": "f7de4175-2d3c-48c3-812a-71870d5eac8d", "type_vehicule": "voiture",
                 "marque": "Toyota", "modele": "Corolla", "couleur": "Grise",
                 "immatriculation": "TG0000AB", "nb_places": 5, "photo": null},
    "depart_lat": 6.1745,
    "depart_lng": 1.169,
    "depart_libelle": "Adidogomé",
    "arrivee_lat": 6.13,
    "arrivee_lng": 1.222,
    "arrivee_libelle": "Grand Marché",
    "points": [
      {"id": "c528ffae-edde-46ee-a3b2-ff0353a80760", "ordre": 1, "lat": 6.175, "lng": 1.17,
       "libelle": "Carrefour Adidogomé"},
      {"id": "651c0803-a5a8-4a1a-9c45-b0ce90b79826", "ordre": 2, "lat": 6.16, "lng": 1.19,
       "libelle": "Carrefour Bè"}
    ],
    "depart_le": "2026-10-31T07:30:00Z",
    "places_total": 2,
    "places_restantes": 2,
    "distance_km": "9.97",
    "duree_min": 24,
    "prix_place": 365,
    "frais_service": 0,
    "statut": "publie",
    "prix_passager": 365,
    "paiement": {"montant_total": 365, "solde_disponible": 5000, "complement_a_payer": 0,
                 "recharge_suggeree": 0,
                 "moyens_paiement": [{"code": "flooz", "libelle": "Flooz (Moov Africa)"},
                                     {"code": "mixx", "libelle": "Mixx (Togocom)"}]},
    "trace": {"source": "routage",
              "points": [[6.1745, 1.169], [6.175, 1.17], [6.16, 1.19], [6.13, 1.222]]}
  }
}
```

(Faux service de routage des tests ; avec OSRM réel, `points` compte souvent des centaines de paires.)

**Erreurs** : 401 `NON_AUTHENTIFIE` / `AUTHENTIFICATION_ECHOUEE` ; 403 `EMAIL_NON_VERIFIE` ;
404 `RESSOURCE_INTROUVABLE` « Trajet introuvable. » ; 400 `DONNEES_INVALIDES` si
`point_id` / `arrivee_*` sont mal formés. **Effets de bord** : aucun (lecture seule).

## `POST /api/v1/trajets/` — publier un trajet

**Permission** : connecté, email vérifié, compte non suspendu, KYC conducteur `verifie`
**et** véhicule déclaré.

**Corps JSON** (tous obligatoires) : `vehicule_id` (UUID, véhicule du conducteur),
`depart_lat`, `depart_lng`, `depart_libelle`, `arrivee_lat`, `arrivee_lng`,
`arrivee_libelle`, `depart_le` (date ISO 8601, future), `places` (entier ≥ 1, ≤ places du
véhicule − 1), `points` (1 à 3 objets `{lat, lng, libelle}`, dans l'ordre de passage).
Aucun prix n'est envoyé : Kovoit le calcule.

```json
{
  "vehicule_id": "f7de4175-2d3c-48c3-812a-71870d5eac8d",
  "depart_lat": 6.1745, "depart_lng": 1.169, "depart_libelle": "Adidogomé",
  "arrivee_lat": 6.13, "arrivee_lng": 1.222, "arrivee_libelle": "Grand Marché",
  "depart_le": "2026-10-31T07:30:00+00:00",
  "places": 2,
  "points": [{"lat": 6.175, "lng": 1.17, "libelle": "Carrefour Adidogomé"},
             {"lat": 6.16, "lng": 1.19, "libelle": "Carrefour Bè"}]
}
```

**201** — `message` : `"Trajet publié."`. `reponse` (`TrajetPublieSerializer`) = mêmes
champs que le détail **sans** `prix_passager` ni `paiement`, **plus** `nb_demandes` (0),
`position_le` (`null`), `tarification` (détail du calcul du prix, figé) et `trace` :

```json
"nb_demandes": 0,
"position_le": null,
"tarification": {"formule_version": "v1", "type_vehicule": "voiture", "distance_km": "9.970",
                 "duree_min": 24, "source_itineraire": "routage", "prix_place": 365, "…": "…"},
"trace": {"source": "routage",
          "points": [[6.1745, 1.169], [6.175, 1.17], [6.16, 1.19], [6.13, 1.222]]}
```

**Erreurs**

| HTTP | `reponse.code` | `message` |
|---|---|---|
| 400 | `DONNEES_INVALIDES` | `Les données envoyées sont invalides.` (`erreurs` : `{"places": ["Ce champ est obligatoire."], …}`) |
| 400 | `DEPART_PASSE` | `L'heure de départ doit être dans le futur.` |
| 400 | `PLACES_INVALIDES` | `Ce véhicule permet au plus 4 place(s) passager.` |
| 403 | `CONDUCTEUR_NON_HABILITE` | `Pour proposer un trajet, faites vérifier votre KYC conducteur et déclarez votre véhicule depuis votre profil.` |
| 403 | `COMPTE_SUSPENDU` | `Votre compte est suspendu : action impossible.` |
| 404 | `RESSOURCE_INTROUVABLE` | `Véhicule introuvable.` (véhicule d'un autre utilisateur) |

**Effets de bord** : trajet créé au statut `publie`, `places_restantes = places`, prix et
tracé enregistrés ; entrée `trajet.publier` au journal d'audit. Aucune notification,
aucun mouvement de portefeuille. Routage indisponible : la publication réussit quand même
(`trace.source = "estimation"`, `tarification.source_itineraire = "estimation"`).

## `GET /api/v1/trajets/recherche/` — rechercher un trajet

**Permission** : connecté, email vérifié.

**Paramètres de requête**

| Nom | Type | Obligatoire | Règle |
|---|---|---|---|
| `depart_lat`, `depart_lng` | nombre | oui | Position de départ du passager |
| `arrivee_lat`, `arrivee_lng` | nombre | oui | Destination du passager |
| `date_heure` | date ISO 8601 | oui | Heure de départ souhaitée |
| `type_vehicule` | chaîne | non | Contrat C2, ci-dessous |

**`type_vehicule` (contrat C2)**

| Valeur envoyée | Effet |
|---|---|
| absent, ou vide (`type_vehicule=`) | tous les types — 200 |
| `voiture` / `moto` (minuscules) | seulement les trajets dont `vehicule.type_vehicule` correspond — 200 |
| toute autre valeur, **majuscules comprises** (`MOTO`, `camion`…) | 400 `DONNEES_INVALIDES` |

Exemple : `GET /api/v1/trajets/recherche/?depart_lat=6.1748&depart_lng=1.1695&arrivee_lat=6.13&arrivee_lng=1.222&date_heure=2026-10-31T07:30:00Z&type_vehicule=moto`

**200** — `reponse` est une **liste non paginée** (vide si aucun trajet), `message` :
`"<n> trajet(s) trouvé(s)."`. Chaque élément : `trajet` (mêmes champs que le détail sans
`prix_passager`, `paiement` ni `trace`), `point_propose`, `distance_marche_km`,
`ecart_minutes`, `prix_passager`. Format inchangé par M-003.

```json
{"statut": "success", "message": "1 trajet(s) trouvé(s).", "reponse": [{
  "trajet": {"id": "f93ab320-6e02-4397-928e-c65bd58f4244", "…": "…",
             "vehicule": {"type_vehicule": "voiture", "…": "…"}, "prix_place": 365},
  "point_propose": {"id": "c528ffae-edde-46ee-a3b2-ff0353a80760", "ordre": 1,
                    "lat": 6.175, "lng": 1.17, "libelle": "Carrefour Adidogomé"},
  "distance_marche_km": 0.06, "ecart_minutes": 0, "prix_passager": 365}]}
```

**400 réel** (`type_vehicule=MOTO`) :

```json
{"statut": "failed", "message": "Les données envoyées sont invalides.",
 "reponse": {"code": "DONNEES_INVALIDES",
             "erreurs": {"type_vehicule": ["« MOTO » n'est pas un choix valide."]}}}
```

Les espaces autour de la valeur dans `« MOTO »` sont des espaces insécables (U+00A0).
Le client teste `reponse.code` et la clé `erreurs.type_vehicule`, jamais le texte.

**Autres erreurs** : 400 `DONNEES_INVALIDES` (paramètre obligatoire manquant :
`"Ce champ est obligatoire."`), 401, 403 `EMAIL_NON_VERIFIE`. **Effets de bord** : aucun.
