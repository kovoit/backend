FROM python:3.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Fichiers statiques du Django admin, servis par WhiteNoise (valeurs factices : build seulement)
RUN DJANGO_SECRET_KEY=build DATABASE_URL=sqlite:////tmp/build.db \
    python manage.py collectstatic --noinput

# Dossier des pièces KYC créé ici : le volume de production en hérite les droits de kovoit
RUN mkdir -p /app/prive /app/media && useradd --create-home --uid 1000 kovoit && chown -R kovoit /app
USER kovoit

EXPOSE 8000
# PROCESSUS=web (défaut), worker ou beat : voir scripts/demarrer.sh
CMD ["sh", "scripts/demarrer.sh"]
