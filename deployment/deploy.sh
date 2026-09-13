#!/usr/bin/env bash
# Script de déploiement de référence pour Nexus sur un serveur Debian/Linux.
# À lire et adapter avant exécution — ne lancez pas ceci en aveugle en prod.
set -euo pipefail

echo "=== 1. Dépendances système ==="
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv nginx ffmpeg certbot python3-certbot-nginx

echo "=== 2. Backend : environnement virtuel + dépendances ==="
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== 3. Configuration ==="
if [ ! -f .env ]; then
  cp .env.example .env
  echo ">>> Éditez backend/.env maintenant (SECRET_KEY, DATABASE_URL, CORS_ALLOWED_ORIGINS, etc.) puis relancez ce script."
  exit 1
fi

echo "=== 4. Migrations base de données (Alembic) ==="
alembic upgrade head

echo "=== 5. Frontend : build de production ==="
cd ../frontend
npm ci
npm run build   # génère frontend/dist, servi statiquement par Nginx

echo "=== 6. Certificat TLS (une seule fois par domaine) ==="
echo ">>> sudo certbot --nginx -d votre-domaine.tld"

echo "=== 7. Lancement ==="
echo "Option A (recommandé) : docker compose -f ../deployment/docker-compose.yml --env-file backend/.env up -d --build"
echo "Option B (sans Docker) : sudo systemctl enable --now nexus-backend  (voir deployment/nexus-backend.service)"

echo "=== Terminé. Vérifiez : curl -f https://votre-domaine.tld/api/health ==="
