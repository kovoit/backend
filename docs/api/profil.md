# Profil — photo de profil (contrat C3)

Enveloppe, authentification et erreurs génériques : voir [`README.md`](README.md).

## Règle des URL de `photo` (toutes les routes)

Le champ `photo` est une **URL relative** commençant par `/media/` (ex.
`/media/photos_profil/moi.jpg`), ou `null` si l'utilisateur n'a pas de photo.
**Le client la préfixe avec l'origine de l'API** (schéma + hôte + port de
`API_BASE_URL`, sans `/api/v1`) avant de l'afficher, en un seul endroit du code.

Exemple : `API_BASE_URL = http://192.168.1.20:8001/api/v1` →
`http://192.168.1.20:8001/media/photos_profil/moi.jpg`.

Routes concernées (même forme relative partout, vérifié par les tests) :

| Route | Emplacement du champ |
|---|---|
| `GET /api/v1/moi/`, `PATCH /api/v1/moi/` | `reponse.photo` |
| `POST /api/v1/auth/otp/verifier/` | `reponse.utilisateur.photo` |
| `GET /api/v1/trajets/recherche/` | `reponse[].trajet.conducteur.photo` |
| `GET /api/v1/trajets/{id}/` | `reponse.conducteur.photo` |
| `GET /api/v1/utilisateurs/{id}/` (profil public) | `reponse.photo` |

`/media/` est servi par Django en développement (`DEBUG=True`) seulement ; en production
par le serveur web, à la même adresse.

## `PATCH /api/v1/moi/` — modifier mon profil (envoi de la photo)

**Permission** : connecté, email vérifié. Aucun KYC requis.

**Corps** : `multipart/form-data` pour envoyer une photo (JSON accepté pour les autres
champs). Tous les champs sont facultatifs ; seuls les champs envoyés sont modifiés.

| Champ | Type | Règle |
|---|---|---|
| `photo` | fichier image | Image lisible (JPEG, PNG…). Remplace la photo actuelle. Testé jusqu'à ~2 Mo |
| `nom`, `prenom` | chaîne | ≤ 100 caractères |
| `telephone` | chaîne | Mobile togolais, normalisé en `+228XXXXXXXX` (sinon 400 `TELEPHONE_INVALIDE`) |
| `accepter_cgu` | booléen | Vrai : accepte les CGU en vigueur |

Exemple (curl) :

```bash
curl -X PATCH "$API/api/v1/moi/" -H "Authorization: Bearer $ACCESS" \
     -F "photo=@moi.jpg;type=image/jpeg"
```

Côté Flutter : `MultipartFile` avec le nom de champ **`photo`**. Ne pas fixer
`Content-Type` à la main (la bibliothèque ajoute la `boundary`).

**200** — sortie réelle :

```json
{
  "statut": "success",
  "message": "Profil mis à jour.",
  "reponse": {
    "id": "38c0d517-81ec-4db7-8e5e-7600840953d3",
    "email": "kodjo.amegah@exemple.tg",
    "telephone": "+22890000000",
    "nom": "Amegah",
    "prenom": "Kodjo",
    "photo": "/media/photos_profil/moi.jpg",
    "email_verifie": true,
    "mode_actif": "passager",
    "statut_compte": "actif",
    "suspendu_jusqu_au": null,
    "profil_complet": true,
    "cgu_acceptees": false,
    "cgu_url": "https://kovoittg.com/conditions-utilisation/",
    "kyc": {"passager": "non_verifie", "conducteur": "verifie"},
    "etat": {
      "badge_kyc": true,
      "acces": {"peut_rechercher": true, "peut_reserver": false, "peut_publier": true},
      "mode_conducteur": {"disponible": true, "kyc_conducteur_verifie": true,
                          "vehicule_declare": true},
      "alertes": [{"code": "KYC_PASSAGER_NON_VERIFIE",
                   "message": "Vérifiez votre identité dans votre profil pour pouvoir réserver.",
                   "action_requise": true}]
    }
  }
}
```

Le nom du fichier stocké peut différer du nom envoyé (suffixe ajouté si le nom existe déjà) :
toujours utiliser l'URL renvoyée. Un `GET /api/v1/moi/` relu ensuite renvoie la même URL.

**Erreurs**

| HTTP | `reponse.code` | `message` | `erreurs` (texte réel) |
|---|---|---|---|
| 400 | `DONNEES_INVALIDES` | `Les données envoyées sont invalides.` | `{"photo": ["Transférez une image valide. Le fichier que vous avez transféré n'est pas une image, ou il est corrompu."]}` (fichier non image, ex. texte renommé en `.jpg`) |
| 400 | `DONNEES_INVALIDES` | `Les données envoyées sont invalides.` | `{"photo": ["La donnée soumise n'est pas un fichier. Vérifiez le type d'encodage du formulaire."]}` (champ `photo` envoyé comme texte, pas comme fichier) |
| 400 | `TELEPHONE_INVALIDE` | `Numéro de téléphone invalide : saisissez un numéro mobile togolais à 8 chiffres commençant par 7 ou 9 (ex. 90 11 22 33), avec ou sans +228.` | `null` |
| 401 | `NON_AUTHENTIFIE` / `AUTHENTIFICATION_ECHOUEE` | voir README | `null` |
| 403 | `EMAIL_NON_VERIFIE` | `Vérifiez votre adresse email pour accéder à ce service.` | `null` |

Exemple complet d'échec photo :

```json
{
  "statut": "failed",
  "message": "Les données envoyées sont invalides.",
  "reponse": {
    "code": "DONNEES_INVALIDES",
    "erreurs": {"photo": ["Transférez une image valide. Le fichier que vous avez transféré n'est pas une image, ou il est corrompu."]}
  }
}
```

En cas d'échec, la photo précédente est **conservée**. Le client teste `reponse.code` et la
présence de `erreurs.photo`, jamais le texte.

**Effets de bord** : fichier enregistré sous `/media/photos_profil/` ; entrée
`profil.modifier` au journal d'audit (noms des champs seulement, jamais le fichier).
Aucune notification, aucun mouvement de portefeuille. Un `PATCH` sans `photo` ne touche
pas à la photo existante.
