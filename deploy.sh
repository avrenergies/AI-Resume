#!/usr/bin/env bash
# deploy.sh — Run once on a fresh Ubuntu 22.04 VPS as root/sudo user
# Usage: sudo bash deploy.sh

set -euo pipefail

DEPLOY_DIR="/opt/resume_api"
SERVICE_USER="www-data"
PYTHON="python3.10"

echo "==> Updating system packages..."
apt-get update -qq
apt-get install -y -qq \
    python3.10 python3.10-venv python3-pip \
    poppler-utils tesseract-ocr libgl1 \
    nginx certbot python3-certbot-nginx \
    antiword libreoffice-writer \
    git curl

echo "==> Creating deploy directory..."
mkdir -p "$DEPLOY_DIR"
chown "$SERVICE_USER":"$SERVICE_USER" "$DEPLOY_DIR"

echo "==> Copying app files..."
cp -r app "$DEPLOY_DIR/"
cp requirements.txt "$DEPLOY_DIR/"
cp .env.example "$DEPLOY_DIR/.env.example"

echo "==> Creating virtual environment..."
$PYTHON -m venv "$DEPLOY_DIR/venv"
"$DEPLOY_DIR/venv/bin/pip" install --upgrade pip -q
"$DEPLOY_DIR/venv/bin/pip" install -r "$DEPLOY_DIR/requirements.txt" -q

echo "==> Downloading spaCy model..."
"$DEPLOY_DIR/venv/bin/python" -m spacy download en_core_web_sm

echo "==> Installing systemd service..."
cp resume_api.service /etc/systemd/system/resume_api.service
systemctl daemon-reload
systemctl enable resume_api

echo "==> Installing nginx config..."
cp nginx.conf /etc/nginx/sites-available/resume_api
ln -sf /etc/nginx/sites-available/resume_api /etc/nginx/sites-enabled/resume_api
nginx -t
systemctl reload nginx

echo ""
echo "============================================================"
echo "  NEXT STEPS (manual):"
echo ""
echo "  1. Edit /opt/resume_api/.env and set:"
echo "       RESUME_API_KEY=<your-strong-secret>"
echo "       ALLOWED_ORIGINS=https://avrenergies.com"
echo ""
echo "  2. Get SSL cert:"
echo "       certbot --nginx -d api.avrenergies.com"
echo ""
echo "  3. Start the service:"
echo "       systemctl start resume_api"
echo "       systemctl status resume_api"
echo ""
echo "  4. Verify:"
echo "       curl https://api.avrenergies.com/health"
echo "============================================================"
