# CLAUDE.md — Kovoit Backend (MVP)

Kovoit : covoiturage urbain à Lomé (Togo) par partage des frais de carburant. Ce dépôt = **backend Django uniquement** (le mobile Flutter et l'admin React sont dans d'autres dépôts et consomment cette API).

> **Règle d'or :** `PRD.md` = source de vérité **métier**. `CLAUDE.md` = source de vérité **technique / méthode**. Spec d'origine : `docs/Kovoit_Spécification_du_MVP.docx`. En cas de doute sur une règle métier : relire le PRD, ne jamais inventer.

---

## 1. Stack

| Rôle | Technologie |
|---|---|
| Framework | Django 5.2 LTS + Django REST Framework |
| Auth | Email + OTP (envoyé via **Gmail SMTP**) puis JWT (`djangorestframework-simplejwt`) |
| Base de données | PostgreSQL 16 (coordonnées GPS en latitude / longitude, sans PostGIS) |
| Tâches asynchrones | Celery + Redis (emails, clôture auto, suspensions) |
| Routage / distances | **OSRM** derrière une interface `RoutingProvider` |
| Paiement | **Simulation** derrière une interface `PaiementProvider` |
| Documentation API | drf-spectacular (OpenAPI 3) |
| Qualité | pytest-django, factory_boy, ruff, pre-commit |

## 2. Commandes

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # Windows
cp .env.example .env                       # puis renseigner DJANGO_SECRET_KEY, Gmail…
docker compose up -d db redis              # postgres (5433) + redis (6381) — ou `docker compose up` pour tout (API sur 8001)
python manage.py migrate
python manage.py seed_parametres           # valeurs de départ des paramètres
python manage.py createsuperuser           # compte admin (email + mot de passe)
python manage.py seed_demo                 # comptes passager/conducteur vérifiés + trajet + jetons JWT (DEBUG)
python manage.py seed_backoffice           # 30 jours d'activité fictive pour le back-office React (DEBUG, exige un admin)
python manage.py runserver                 # API : /api/v1/  · Swagger : /api/docs/
celery -A kovoit worker -l info --pool=solo   # worker (--pool=solo obligatoire sous Windows)
celery -A kovoit beat -l info              # tâches planifiées
pytest                                     # tests
ruff check . && ruff format --check .      # lint
python scripts/check_file_length.py        # limite 200 lignes
python manage.py spectacular --file schema.yml --validate
```

- **Sans Redis en local** : `CELERY_TASK_ALWAYS_EAGER=True` et `CACHE_URL=locmemcache://` dans `.env` (les tâches s'exécutent immédiatement).
- **Pas de PostGIS** (GDAL absent sous Windows) : pré-filtre en base sur une boîte lat/lng puis distance Haversine exacte en Python (`trajets/services/recherche.py`).
- Pièces KYC stockées dans `PRIVATE_MEDIA_ROOT` (`prive/`, hors `MEDIA_ROOT`, jamais servi par URL).
- Photos (`/media/`) servies par Django en DEBUG uniquement ; en prod par le serveur web. Statiques du Django admin : WhiteNoise.
- **Push** : `FIREBASE_CREDENTIALS` (chemin du JSON de compte de service, jamais commité) active `FcmPushSender`. Sans clé : push journalisé et **email de secours** systématique. Jeton FCM périmé → appareil supprimé, email de secours.
- Le Django admin (backoffice interne) est sur `/django-admin/` ; `/api/v1/admin/` est l'API de l'admin React.

---

## 3. Architecture

```
backend/
├── kovoit/            # projet Django : settings.py (lu depuis .env), urls.py, celery.py, asgi/wsgi
├── scripts/           # check_file_length.py
└── apps/
    ├── core/          # BaseModel, BaseRepository, réponse API, exceptions, pagination, géo, permissions
    ├── parametres/    # Parametre(cle, valeur) + get_param() avec cache
    ├── accounts/      # User (email = login), OTP email, JWT, mode_actif, suspension
    ├── kyc/           # KycDossier, KycPiece, stockage privé, journal des consultations
    ├── vehicules/
    ├── trajets/       # Trajet, PointPriseEnCharge, recherche / correspondance
    ├── reservations/  # Reservation, machine à 9 états, code de départ, absence
    ├── tarification/  # RÉSERVÉ — algorithme de prix à définir plus tard (voir §7)
    ├── routage/       # RoutingProvider : OsrmProvider, FakeProvider
    ├── confiance/     # Note, Signalement / litige, fiabilité, suspension auto
    ├── partage/       # lien public temporaire « Partager mon trajet »
    ├── notifications/ # EmailSender (Gmail SMTP), PushSender (FCM), Fake
    ├── portefeuille/  # Transaction (journal) + PaiementProvider simulé
    └── dashboard/     # indicateurs, tableau de bord admin, économies conducteur, données de démo (demo/, seed_*)
```

### Couches (obligatoires, sens unique)

```
api/views  →  services  →  repository  →  models
```

| Couche | Fait | Ne fait JAMAIS |
|---|---|---|
| `models.py` | Champs, `choices`, contraintes DB (`CheckConstraint`, `UniqueConstraint`), index | Logique métier, appels externes |
| `repository.py` | **Seul endroit où l'ORM est utilisé** : `filter`, `get`, `create`, `update`, `select_for_update`, `annotate` | Règles métier, `transaction.atomic()`, envoi de notifications |
| `services/` | Logique métier, `transaction.atomic()`, vérification des transitions, appels aux providers, déclenchement des tâches Celery | Requêtes ORM directes |
| `api/` | Validation d'entrée (serializers), permissions, appel d'un service, réponse enveloppée | Logique métier, ORM direct |

- `select_for_update()` est appelé **dans le repository** (ex. `get_for_update(id)`), mais **toujours à l'intérieur** d'un `transaction.atomic()` ouvert par le service.
- Un service d'une app peut appeler le **service** (ou le repository) d'une autre app, jamais ses models directement.
- `core/repository.py` fournit `BaseRepository` (`get_by_id`, `get_or_none`, `filter`, `create`, `update`, `exists`) ; chaque app en hérite.

### Gabarit d'une app

```
apps/<app>/
├── models.py
├── repository.py
├── services/            # package dès que > 200 lignes ; sinon services.py
│   ├── __init__.py      # ré-exporte les fonctions publiques
│   └── <cas_usage>.py
├── transitions.py       # si l'app a une machine à états
├── api/{serializers,views,urls,permissions}.py
├── tasks.py             # Celery
├── admin.py
└── tests/{factories,test_repository,test_services,test_api}.py
```

### Limite de taille : 200 lignes max par fichier

- Aucun fichier `.py` ne dépasse **200 lignes** (migrations exclues). Vérifié par `scripts/check_file_length.py` en pre-commit et CI.
- Si un fichier approche la limite : le transformer en **package** découpé par cas d'usage (ex. `services/demande.py`, `services/decision.py`, `services/annulation.py`), jamais compacter le code pour tenir.

---

## 4. Format de réponse API (TOUS les endpoints)

```json
{ "statut": "success", "message": "Réservation envoyée au conducteur.", "reponse": { ... } }
{ "statut": "failed",  "message": "Plus aucune place disponible.",      "reponse": { "code": "PLUS_DE_PLACE", "erreurs": null } }
```

- `statut` : `"success"` ou `"failed"` uniquement.
- `message` : phrase en français, lisible par l'utilisateur final.
- `reponse` : données (objet, liste ou `null`) en succès ; en échec `{ "code": "<CODE_ERREUR>", "erreurs": <détail champ par champ ou null> }`.
- Les **codes HTTP restent significatifs** : 200, 201, 400, 401, 403, 404, 409, 429, 500.
- Implémentation centralisée dans `apps/core/api/` :
  - `reponses.py` : `succes(message, data=None, status=200)` utilisé par toutes les vues ;
  - `exceptions.py` : `exception_handler` DRF personnalisé qui enveloppe toutes les erreurs (validation, auth, 404, `ErreurMetier`) ;
  - `pagination.py` : liste paginée dans `reponse` → `{ "count", "next", "previous", "results" }`.
- Les erreurs métier sont levées dans les services via des sous-classes de `core.exceptions.ErreurMetier(code, message, http_status)` ; jamais de `Response` construite à la main avec un autre format.
- Le schéma OpenAPI (drf-spectacular) doit refléter cette enveloppe.

---

## 5. Règles transverses

1. **Langue :** code métier **en français** (modèles `Trajet`, `Reservation`, champs `places_restantes`, statuts `demandee`…). Termes techniques Django/Python inchangés (`repository`, `services`, `serializer`).
2. **Transactions :** toute modification de places, de statut ou du journal de transactions se fait dans `transaction.atomic()` avec verrou `select_for_update()`. Filet DB : `CheckConstraint(places_restantes >= 0)`.
3. **Paramètres :** aucune valeur métier en dur. Lecture via `parametres.services.get_param("cle")` (cache invalidé à la modification).
4. **Argent :** montants en F CFA **entiers** (`PositiveIntegerField`). Jamais de `float`.
5. **Temps :** `USE_TZ = True`, `TIME_ZONE = "Africa/Lome"`, toujours `timezone.now()`.
6. **Secrets :** uniquement via variables d'environnement (`.env`, jamais commité). `.env.example` tenu à jour.
7. **Fournisseurs externes** (email, push, routage, paiement) : toujours derrière une interface + implémentation `Fake` utilisée en test. Aucun test n'appelle un service réel.
8. **Hors MVP :** ne rien implémenter hors périmètre (messagerie, KYC automatique/OCR, trajets interurbains, trajets récurrents, vrai Mobile Money, offre entreprises).

## 6. Authentification — OTP email via Gmail SMTP

- Login = **email** (unique). `telephone` obligatoire au profil mais **non vérifié** au MVP.
- **Deux flux de connexion, tous deux en JWT** : application mobile = OTP email (ci-dessous) ; back-office React = email + mot de passe, réservé aux `is_staff` (`/api/v1/auth/admin/…`, `accounts/services/connexion_admin.py`).
- Flux : `POST /auth/otp/demander` (email) → email avec code → `POST /auth/otp/verifier` (email + code) → JWT access + refresh.
- Code OTP : 6 chiffres, **stocké haché**, validité `otp_validite_min`, `otp_max_essais` essais, renvoi limité (`otp_delai_renvoi_s`, `otp_max_par_heure`). Un nouveau code invalide le précédent.
- Envoi **asynchrone** (Celery) via `notifications.EmailSender`.
- Config SMTP : `EMAIL_HOST=smtp.gmail.com`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=True`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` = **mot de passe d'application Gmail** (jamais le mot de passe du compte).
- Dev / test : `console.EmailBackend` / `locmem.EmailBackend`.
- Limite Gmail ≈ 500 emails/jour (compte gratuit) : suffisant pour le pilote ; changer de backend email sans toucher au métier si dépassé.

## 7. Prix & paiement

- **Tarification : à définir plus tard.** Ne coder **aucun** algorithme de prix. Les champs `prix` et `frais_service` existent sur `Reservation` (nullable). L'app `tarification` expose `prix_par_place(distance_km)` et `frais_service()` ; `prix_par_place`, en attendant, renvoie le paramètre `prix_simulation` ; elle sera remplacée sans toucher aux autres apps.
- **Distance :** `routage` calcule `distance_km` par la route (OSRM) et la stocke ; la correspondance utilise Haversine à vol d'oiseau (pré-filtre lat/lng en base).
- **Paiement : simulation** du portefeuille (option B de la spec) via `SimulationPaiementProvider` (aucun argent réel, références `SIM-…`).
  - Journal `Transaction` en ajout seul : `recharge, blocage, deblocage, debit, credit, retrait, remboursement`. **Le solde n'est jamais stocké** : il est calculé depuis le journal.
  - `solde_total = recharge + credit + remboursement − debit − retrait` ; `bloque = blocage − deblocage` ; `disponible = solde_total − bloque`.
  - Demande de réservation → `blocage` · refus / annulation → `deblocage` · code de départ saisi → `deblocage` + `debit` · clôture → `credit` conducteur · absence → `deblocage` + `debit` passager + `credit` conducteur · litige → rien tant que l'admin n'a pas tranché.

## 8. Accès & machine à états

**Accès (permissions DRF)**
- Sans compte : uniquement le lien public de partage.
- Email vérifié : chercher et consulter les trajets.
- KYC passager `verifie` : réserver.
- KYC conducteur `verifie` + véhicule déclaré : publier.
- Compte suspendu : ni réserver ni publier ; réservations à venir annulées et remboursées.
- Admin (`is_staff`) : endpoints `/api/v1/admin/…`.

**Réservation — 9 statuts** (`reservations/transitions.py` = seule table de vérité)

```
demandee → acceptee | refusee | annulee
acceptee → en_cours (code de départ) | annulee | absent
en_cours → terminee
terminee → cloturee | litige
litige   → cloturee (décision admin)
```

- `en_cours` **uniquement** si le conducteur saisit le bon code de départ (4 chiffres, généré à l'acceptation, jamais stocké : dérivé par HMAC-SHA256 d'un sel propre à la réservation et de SECRET_KEY (`reservations/code_depart.py`), montré **uniquement au passager**, jamais dans un serializer conducteur ; essais limités).
- `cloturee` à la confirmation du passager ou automatiquement après `delai_confirmation_auto_h` (tâche Celery).
- Toute transition non listée lève `TransitionInvalide`. Chaque transition horodate et notifie l'autre partie.

**Trajet :** `publie → complet (places_restantes = 0) → en_cours → termine` ; `annule` possible avant départ.

---

## CI/CD (GitHub Actions)

- `.github/workflows/ci.yml` (push sur `main`, chaque PR) :
  1. **qualite** : `ruff check`, `ruff format --check`, `scripts/check_file_length.py` ;
  2. **tests** : PostgreSQL + Redis réels, `makemigrations --check`, `migrate`, `check --deploy` (réglages prod), schéma OpenAPI `--validate`, `pytest` avec **couverture ≥ 90 %** ;
  3. **docker** : build de l'image prod (sans publication).
- `.github/workflows/cd.yml` : après une CI **verte sur `main`**, publie l'image sur `ghcr.io/kovoit/backend` (tags `latest` + SHA). Déploiement serveur à ajouter quand l'hébergeur sera choisi.
- `.github/dependabot.yml` : mises à jour hebdo (pip) et mensuelles (actions, Docker).
- Une PR ne se merge que si la CI est verte. Ne jamais baisser le seuil de couverture pour faire passer la CI.

## 9. Méthode de travail

1. Lire `PRD.md` et le code existant de l'app concernée avant toute modification.
2. Ordre d'implémentation d'une fonctionnalité : `models` → migration → `repository` → `services` → `api` → `admin` → tests.
3. **Définition de « terminé » :** tests verts (`pytest`), `ruff` propre, aucun fichier > 200 lignes, migration créée, toutes les réponses au format §4, schéma OpenAPI à jour.
4. Ne jamais modifier une migration déjà appliquée ; en créer une nouvelle.

## 10. Agents (`.claude/agents/`)

| Agent | Quand l'utiliser |
|---|---|
| `django-architect` | Avant de coder : concevoir modèles, repository, services, endpoints d'une fonctionnalité |
| `django-backend-dev` | Implémenter une fonctionnalité de bout en bout |
| `regles-metier-guardian` | Vérifier la conformité au PRD après implémentation |
| `test-engineer` | Écrire / compléter les tests |
| `security-reviewer` | Revue sécurité (OTP, JWT, KYC, permissions, secrets) |
| `api-contract-writer` | Mettre à jour OpenAPI et la doc pour mobile / admin React |
