# Image de production pour le backend Nexus (FastAPI).
# Build : docker build -t nexus-backend -f backend/Dockerfile backend/
FROM python:3.11-slim

# ffmpeg est requis par le module Studio (montage vidéo, filtres, texte
# incrusté). fonts-dejavu-core fournit une police pour les incrustations
# de texte (voir modules/studio/render.py).
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Utilisateur non-root : bonne pratique de sécurité conteneur.
RUN useradd --create-home --shell /bin/bash nexus \
    && chown -R nexus:nexus /app
USER nexus

EXPOSE 8000

# En production : migrations Alembic avant de démarrer, puis Uvicorn
# derrière un reverse proxy (voir deployment/nginx.conf).
# Le nombre de workers doit être ajusté au nombre de coeurs CPU disponibles.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"]
