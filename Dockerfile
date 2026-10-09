FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Fichiers statiques du Django admin, servis par WhiteNoise (valeurs factices : build seulement)
RUN DJANGO_SECRET_KEY=build DATABASE_URL=sqlite:////tmp/build.db \
    python manage.py collectstatic --noinput

RUN useradd --create-home --uid 1000 kovoit && chown -R kovoit /app
USER kovoit

EXPOSE 8000
CMD ["gunicorn", "kovoit.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
