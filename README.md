# Kovoit — Backend

API Django REST du MVP Kovoit (covoiturage urbain à Lomé), consommée par l'app mobile Flutter et l'admin React.

- Règles métier : [PRD.md](PRD.md)
- Règles techniques, architecture et commandes : [claude.md](claude.md)
- Agents Claude Code : [agents.md](agents.md)

## Démarrage rapide (Windows)

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
cp .env.example .env            # renseigner DJANGO_SECRET_KEY (et Gmail pour l'envoi réel d'emails)
docker compose up -d db redis
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py seed_parametres
.venv/Scripts/python manage.py createsuperuser
.venv/Scripts/python manage.py runserver
```

- Santé de l'API : http://localhost:8000/api/v1/sante/
- Documentation Swagger : http://localhost:8000/api/docs/
- Django admin : http://localhost:8000/django-admin/

Toutes les réponses suivent le format :

```json
{ "statut": "success", "message": "…", "reponse": { } }
```
