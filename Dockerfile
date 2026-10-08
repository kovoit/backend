FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# GDAL / GEOS / PROJ : nécessaires à GeoDjango (PostGIS)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gdal-bin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

RUN useradd --create-home --uid 1000 kovoit && chown -R kovoit /app
USER kovoit

EXPOSE 8000
CMD ["gunicorn", "kovoit.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
