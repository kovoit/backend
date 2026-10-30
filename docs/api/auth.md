# Authentification de l'application : e-mail + mot de passe (M-004)

Préfixe `/api/v1/`. Routes publiques, sans en-tête `Authorization`, sauf la déconnexion.
Enveloppe `{statut, message, reponse}` (voir [`README.md`](README.md)). Ne testez que
`reponse.code`, jamais le texte de `message` (qui reste affichable tel quel).

**Commun à toutes les routes.** `email` : adresse valide, **254 caractères au plus**, mise en
minuscules et sans espaces par le serveur. Un champ manquant ou mal formé donne 400
`DONNEES_INVALIDES`, message `Les données envoyées sont invalides.`, `erreurs` =
`{champ: [messages]}` (ex. `{"code": ["Code à 6 chiffres."]}`). `mot_de_passe` : 128
caractères au plus, espaces conservés. `code` : 6 chiffres (chaîne).

## Formes partagées

`CODE_ENVOYE` (`delai_renvoi_s` = paramètre `otp_delai_renvoi_s`, 60 par défaut) :

```json
{ "email": "ama.mensah@exemple.tg", "delai_renvoi_s": 60 }
```

`SESSION` (identique à l'ancienne `auth/otp/verifier/`) : `access` (15 min) et `refresh`
(7 jours, `canal` = `mobile`) ; `utilisateur` = profil de `GET /moi/` (voir [`profil.md`](profil.md)).

```json
{
  "utilisateur": {
    "id": "38c0d517-81ec-4db7-8e5e-7600840953d3", "email": "ama.mensah@exemple.tg",
    "telephone": "+22890112233", "nom": "Mensah", "prenom": "Ama", "photo": null,
    "email_verifie": true, "mode_actif": "passager", "statut_compte": "actif",
    "suspendu_jusqu_au": null, "profil_complet": true, "cgu_acceptees": true,
    "cgu_url": "https://kovoittg.com/conditions-utilisation/",
    "kyc": {"passager": "non_verifie", "conducteur": "non_verifie"},
    "etat": {
      "badge_kyc": true,
      "acces": {"peut_rechercher": true, "peut_reserver": false, "peut_publier": false},
      "mode_conducteur": {"disponible": false, "kyc_conducteur_verifie": false,
                          "vehicule_declare": false},
      "alertes": [{"code": "KYC_PASSAGER_NON_VERIFIE",
                   "message": "Vérifiez votre identité dans votre profil pour pouvoir réserver.",
                   "action_requise": true}]
    }
  },
  "nouveau_compte": true,
  "access": "eyJhbGciOiJIUzI1NiIs…", "refresh": "eyJhbGciOiJIUzI1NiIs…"
}
```

Le client **n'interprète pas** le profil : droits (`etat.acces`), alertes et statuts sont
affichés tels que l'API les renvoie.

## Parcours

Inscription → `inscription/verifier/` (session ouverte) · Connexion → `connexion/` ; si 403
`EMAIL_NON_VERIFIE` → écran de code → `inscription/verifier/` · Oubli → `mot-de-passe/oublie/`
→ `mot-de-passe/reinitialiser/` → retour à `connexion/` (aucun jeton émis).

## `POST auth/inscription/` → 201 `CODE_ENVOYE`, aucun jeton

| Champ | Type | Obligatoire | Règle |
|---|---|---|---|
| `prenom`, `nom` | chaîne ≤ 100 | oui | |
| `email` | e-mail ≤ 254 | oui | unique |
| `telephone` | chaîne | oui | mobile togolais, 8 chiffres commençant par 7 ou 9, `+228` facultatif ; enregistré `+228XXXXXXXX` |
| `mot_de_passe` | chaîne ≤ 128 | oui | 8 caractères min., pas trop courant, pas entièrement numérique, pas trop proche du prénom, du nom ou de l'e-mail |
| `cgu_acceptees` | booléen | oui | doit valoir `true` (version et date des CGU enregistrées) |

```json
{ "prenom": "Ama", "nom": "Mensah", "email": "Ama.Mensah@exemple.tg",
  "telephone": "90 11 22 33", "mot_de_passe": "Tokoin-Bè-2026", "cgu_acceptees": true }
```

Succès 201 : message `Compte créé. Saisissez le code envoyé à votre adresse e-mail.`,
`reponse` = `CODE_ENVOYE`. Effet : compte créé **non vérifié**, code de vérification envoyé.

Erreurs, **contrôlées dans cet ordre** :

| HTTP | `code` | `erreurs` | `message` |
|---|---|---|---|
| 400 | `DONNEES_INVALIDES` | ex. `{"cgu_acceptees": ["Acceptez les conditions d'utilisation."]}` | `Les données envoyées sont invalides.` |
| 400 | `TELEPHONE_INVALIDE` | `{"telephone": [<message>]}` | `Numéro de téléphone invalide : saisissez un numéro mobile togolais à 8 chiffres commençant par 7 ou 9 (ex. 90 11 22 33), avec ou sans +228.` |
| 400 | `MOT_DE_PASSE_FAIBLE` | `{"mot_de_passe": [messages des validateurs]}` | `Mot de passe trop faible.` |
| 409 | `EMAIL_DEJA_UTILISE` | `{"email": ["Un compte existe déjà avec cette adresse e-mail."]}` | `Un compte existe déjà avec cette adresse e-mail. Connectez-vous.` |

## `POST auth/inscription/verifier/` → 200 `SESSION`, `nouveau_compte: true`

Corps : `email`, `code`. Exemple `{ "email": "ama.mensah@exemple.tg", "code": "482913" }`.
Succès : message `Adresse e-mail vérifiée.` ; effet : `email_verifie` = vrai, session ouverte.

| HTTP | `code` | `erreurs` | `message` |
|---|---|---|---|
| 400 | `CODE_OTP_INVALIDE` | `null` | `Code invalide ou expiré.` |

Même erreur pour : code faux, expiré, déjà utilisé, essais épuisés (`otp_max_essais`, 5 ; au
dernier essai le code est annulé), compte inconnu, désactivé ou déjà vérifié. Validité d'un
code : `otp_validite_min` (10 min). Un nouveau code annule le précédent.

## `POST auth/inscription/renvoyer-code/` → 200 `CODE_ENVOYE`

Corps : `{ "email": "ama.mensah@exemple.tg" }`. Message (toujours le même) : `Si un compte
attend la vérification de cette adresse, un nouveau code vient d'y être envoyé.` Rien n'est
envoyé pour une adresse inconnue, déjà vérifiée ou désactivée (même réponse 200).

| HTTP | `code` | `erreurs` | `message` |
|---|---|---|---|
| 429 | `TROP_DE_REQUETES` | `null` | `Patientez 60 secondes avant de demander un nouveau code.` (délai de renvoi) |
| 429 | `TROP_DE_REQUETES` | `null` | `Trop de codes demandés. Réessayez dans une heure.` (plafond horaire) |

## `POST auth/connexion/` → 200 `SESSION`, `nouveau_compte: false`

Corps : `{ "email": "ama.mensah@exemple.tg", "mot_de_passe": "Tokoin-Bè-2026" }`.
Succès : message `Connexion réussie.` Un compte **suspendu** se connecte (alerte
`COMPTE_SUSPENDU` dans `etat.alertes`) ; un administrateur aussi, mais ses jetons (`canal` =
`mobile`) n'ouvrent pas le back-office (voir `CANAL_WEB_REQUIS`).

| HTTP | `code` | `erreurs` | `message` |
|---|---|---|---|
| 401 | `IDENTIFIANTS_INVALIDES` | `null` | `Email ou mot de passe incorrect.` |
| 403 | `EMAIL_NON_VERIFIE` | `null` | `Adresse e-mail pas encore vérifiée : saisissez le code reçu par e-mail.` |
| 429 | `TROP_DE_REQUETES` | `null` | `Requête ralentie. Expected available in 42 seconds.` (texte de la bibliothèque, partiellement traduit) |

- 401 identique pour : adresse inconnue, mauvais mot de passe, compte désactivé, compte sans
  mot de passe (créé par l'ancienne connexion par code : passer par « mot de passe oublié »).
- 403 seulement avec le **bon** mot de passe : un nouveau code part si le délai de renvoi est
  écoulé et le plafond horaire non atteint, sinon même 403 sans envoi. Le 403 ne contient pas
  `delai_renvoi_s` : l'écran de code suppose 60 s.
- 429 : **5 requêtes par minute et par IP** sur cette route, réussies ou non.

## `POST auth/mot-de-passe/oublie/` → 200 `CODE_ENVOYE`

Corps : `{ "email": "kossi.agbeko@exemple.tg" }`. Message (toujours le même) : `Si cette
adresse correspond à un compte, un code de réinitialisation vient d'y être envoyé.` Aucun code
pour une adresse inconnue, un compte désactivé ou un administrateur (`is_staff` : lien du
back-office). Erreurs : les mêmes deux 429 `TROP_DE_REQUETES` que `renvoyer-code`
(compte éligible seulement).

## `POST auth/mot-de-passe/reinitialiser/` → 200, `reponse: null`

Corps : `{ "email": "kossi.agbeko@exemple.tg", "code": "730518", "mot_de_passe": "Agoè-Nyivé-77" }`.
Succès : message `Mot de passe modifié. Connectez-vous avec votre nouveau mot de passe.`
Effets : nouveau mot de passe, `email_verifie` = vrai, **toutes les sessions révoquées**
(tous les `refresh` ; les `access` déjà émis restent valables jusqu'à 15 min). Aucun jeton
émis : renvoyer vers l'écran de connexion. Un compte sans mot de passe fixe ainsi le premier.

| HTTP | `code` | `erreurs` | `message` |
|---|---|---|---|
| 400 | `MOT_DE_PASSE_FAIBLE` | `{"mot_de_passe": [...]}` | `Mot de passe trop faible.` |
| 400 | `CODE_OTP_INVALIDE` | `null` | `Code invalide ou expiré.` |

Le mot de passe est contrôlé **avant** le code : après `MOT_DE_PASSE_FAIBLE`, le code et
l'ancien mot de passe restent valables. `CODE_OTP_INVALIDE` aussi pour une adresse inconnue,
désactivée ou d'administrateur.

## `POST auth/jeton/rafraichir/` → 200

Corps `{ "refresh": "…" }`. Succès : message `Jeton renouvelé.`, `reponse` =
`{ "access": "…", "refresh": "…" }`. **Rotation** : le nouveau `refresh` remplace l'ancien,
qui est révoqué ; le stocker aussitôt. Erreur : 401 `SESSION_EXPIREE`, `erreurs` null,
`Session invalide ou expirée. Reconnectez-vous.` (expiré, invalide ou révoqué).

## `POST auth/deconnexion/` → 200, `reponse: null`

Connecté, e-mail vérifié (`Authorization: Bearer <access>`). Corps `{ "refresh": "…" }` (celui
de cet appareil). Succès : `Déconnexion effectuée.` ; effet : ce `refresh` est révoqué.

| HTTP | `code` | `message` |
|---|---|---|
| 400 | `JETON_INVALIDE` | `Jeton de rafraîchissement invalide ou déjà utilisé.` |
| 403 | `JETON_AUTRE_COMPTE` (**nouveau**) | `Ce jeton de session n'appartient pas à votre compte.` (le jeton n'est pas révoqué) |
| 401 | `NON_AUTHENTIFIE` / `AUTHENTIFICATION_ECHOUEE` | voir [`README.md`](README.md) |
| 403 | `EMAIL_NON_VERIFIE` | `Vérifiez votre adresse email pour accéder à ce service.` |

## Routes `/api/v1/admin/…` et `GET auth/admin/moi/` : 403 `CANAL_WEB_REQUIS`

Un administrateur dont le jeton ne vient pas de `POST auth/admin/connexion/` (claim signé
`canal` ≠ `web`, ex. connexion par l'application) reçoit 403 `CANAL_WEB_REQUIS`, `erreurs`
null, `Connectez-vous au back-office pour accéder à cette partie de Kovoit.` Un non-admin
reçoit d'abord 403 `ACCES_REFUSE`. Refus journalisé. Côté React : se reconnecter par
`auth/admin/connexion/`.

## Limites et non-divulgation

- Délai de renvoi `otp_delai_renvoi_s` (60 s) **par objet** (vérification, réinitialisation) ;
  plafond `otp_max_par_heure` (5) **commun** à tous les codes envoyés à une adresse.
- Limite DRF `anon` 60/min par IP sur toutes ces routes ; `connexion/` : 5/min par IP.
- Compteur d'échecs par adresse (D-72) : **à venir**, pas encore actif.
- Réponses identiques, quel que soit le compte : `renvoyer-code/` et `oublie/` (200),
  `connexion/` (401), `inscription/verifier/` et `reinitialiser/` (400 `CODE_OTP_INVALIDE`).
  Seule l'inscription révèle qu'une adresse existe (409), et un 429 de `renvoyer-code/` ou
  `oublie/` ne concerne qu'un compte existant.

## Anciennes routes `auth/otp/*` : dépréciées

`POST auth/otp/demander/` et `POST auth/otp/verifier/` (connexion par code seul, création de
compte au premier code) restent **inchangées** pour le client jusqu'à leur retrait, après la
migration de l'application mobile (D-70). Ne plus les utiliser dans un nouveau code.

## Comptes de démo

`seed_demo` (`prenom.demo@kovoit.tg`) et `seed_backoffice` (`prenom.nomN@demo.kovoit.tg`)
créent des comptes vérifiés au mot de passe commun `Kovoit-Demo-2026` (jamais l'admin).
