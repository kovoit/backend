# Makefile du backend Kovoit : raccourcis pour les commandes courantes (voir claude.md §2).
#
# Deux façons de lancer le backend :
# - en local (recommandé pour développer) : `make installer` une fois, puis `make dev`.
#   PostgreSQL et Redis tournent dans Docker, l'API tourne dans le .venv sur le port 8000.
# - tout dans Docker : `make docker` (API sur le port 8001, avec worker et beat Celery).
#
# Le Makefile ne lit pas le .env : c'est Django qui le lit, comme d'habitude.
# Il ne pousse rien et ne supprime aucune donnée, sauf `purger-demo` (confirmation demandée).

.DEFAULT_GOAL := aide
.PHONY: aide installer env services services-arret migrer parametres admin demo backoffice \
	purger-demo dev serveur mobile worker beat shell tests couverture lint format longueur qualite \
	schema docker docker-arret logs

# Surchargeable : make dev PY=python3
VENV := .venv
PY ?= $(VENV)/bin/python
MANAGE := $(PY) manage.py
PORT ?= 8000

aide: ## Liste les cibles disponibles
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*## "} {printf "  %-15s %s\n", $$1, $$2}'

# ── Installation ──────────────────────────────────────────────────────
installer: env ## Crée le .venv et installe les dépendances (requirements.txt)
	@test -d $(VENV) || python3 -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt

env: ## Crée le .env depuis .env.example s'il n'existe pas (ne l'écrase jamais)
	@if [ -f .env ]; then echo ".env déjà présent : conservé."; \
	else cp .env.example .env && echo ".env créé : renseigner DJANGO_SECRET_KEY."; fi

# ── Services (PostgreSQL 5433, Redis 6381) ────────────────────────────
services: ## Démarre PostgreSQL et Redis dans Docker et attend qu'ils soient prêts
	docker compose up -d --wait db redis

services-arret: ## Arrête PostgreSQL et Redis (les données sont gardées)
	docker compose stop db redis

# ── Base de données ───────────────────────────────────────────────────
migrer: ## Applique les migrations Django
	$(MANAGE) migrate

parametres: ## Charge les valeurs de départ des paramètres (seed_parametres)
	$(MANAGE) seed_parametres

admin: ## Crée un compte administrateur (email + mot de passe)
	$(MANAGE) createsuperuser

demo: ## Comptes passager/conducteur vérifiés + trajet + jetons JWT (DEBUG)
	$(MANAGE) seed_demo

backoffice: ## 30 jours d'activité fictive pour le back-office (DEBUG, exige un admin)
	$(MANAGE) seed_backoffice

purger-demo: ## ATTENTION : supprime les données de démo (garde admins et paramètres)
	$(MANAGE) purger_demo

# ── Lancement en local ────────────────────────────────────────────────
dev: services migrer parametres serveur ## Tout en un : services, migrations, paramètres puis API

serveur: ## Lance l'API seule sur http://localhost:8000 (PORT=… pour changer)
	@echo "API : http://localhost:$(PORT)/api/v1/  ·  Swagger : http://localhost:$(PORT)/api/docs/"
	$(MANAGE) runserver $(PORT)

worker: ## Lance le worker Celery (inutile si CELERY_TASK_ALWAYS_EAGER=True)
	$(VENV)/bin/celery -A kovoit worker -l info

beat: ## Lance les tâches planifiées Celery (clôture auto, suspensions…)
	$(VENV)/bin/celery -A kovoit beat -l info --schedule /tmp/kovoit-celerybeat-schedule

# Pour l'app Flutter sur un vrai téléphone (même Wi-Fi que le PC) : écoute sur tout le réseau
# local et autorise l'IP du PC (variable d'environnement, prioritaire sur le .env).
IP_LOCALE := $(shell hostname -I 2>/dev/null | awk '{print $$1}')

mobile: services migrer parametres ## Lance l'API joignable depuis un téléphone du même Wi-Fi
	@echo "Côté mobile :"
	@echo "  flutter run --dart-define=USE_MOCK_API=false --dart-define=API_BASE_URL=http://$(IP_LOCALE):$(PORT)/api/v1"
	DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,$(IP_LOCALE) $(MANAGE) runserver 0.0.0.0:$(PORT)

shell: ## Ouvre le shell Django
	$(MANAGE) shell

# ── Qualité ───────────────────────────────────────────────────────────
tests: ## Lance les tests pytest (base PostgreSQL de `make services`)
	$(VENV)/bin/pytest

couverture: ## Tests avec couverture (la CI exige au moins 90 %)
	$(VENV)/bin/pytest --cov=apps --cov=kovoit --cov-report=term-missing --cov-fail-under=90

lint: ## Vérifie le style (ruff check + ruff format --check)
	$(VENV)/bin/ruff check .
	$(VENV)/bin/ruff format --check .

format: ## Corrige le style automatiquement (ruff)
	$(VENV)/bin/ruff check --fix .
	$(VENV)/bin/ruff format .

longueur: ## Vérifie qu'aucun fichier Python ne dépasse 200 lignes
	$(PY) scripts/check_file_length.py

qualite: lint longueur ## Lint + limite de 200 lignes (comme la CI)

schema: ## Génère et valide le schéma OpenAPI (schema.yml)
	$(MANAGE) spectacular --file schema.yml --validate

# ── Tout dans Docker (API sur le port 8001) ───────────────────────────
docker: ## Lance toute la stack dans Docker : base, Redis, API, worker, beat
	docker compose up -d --build
	docker compose exec web python manage.py migrate
	docker compose exec web python manage.py seed_parametres
	@echo "API : http://localhost:8001/api/v1/  ·  Swagger : http://localhost:8001/api/docs/"

docker-arret: ## Arrête toute la stack Docker (les données sont gardées)
	docker compose stop

logs: ## Affiche les journaux de l'API et du worker Docker
	docker compose logs -f web worker
