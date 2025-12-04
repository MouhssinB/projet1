#!/bin/bash

set -e

echo "=========================================="
echo "🚀 DÉMARRAGE APPLICATION SIMSAN"
echo "=========================================="

# Configuration du point de montage
MOUNT_POINT="${AZURE_FILESHARE_MOUNT_POINT:-/mnt/storage}"
SESSIONS_DIR="${MOUNT_POINT}/sessions"

echo "📋 Configuration FileShare:"
echo "   Mount Point: $MOUNT_POINT"
echo "   Sessions Dir: $SESSIONS_DIR"

# Vérifier si le FileShare est déjà monté
if mountpoint -q "$MOUNT_POINT" 2>/dev/null; then
    echo "✅ FileShare Azure déjà monté sur $MOUNT_POINT"
    df -h "$MOUNT_POINT" 2>/dev/null || true
elif [ -d "$MOUNT_POINT" ] && [ "$(ls -A $MOUNT_POINT 2>/dev/null)" ]; then
    echo "✅ FileShare détecté sur $MOUNT_POINT (montage Azure automatique)"
else
    echo "⚠️  FileShare non monté - utilisation du stockage local"
fi

# Créer le répertoire sessions
if [ -d "$MOUNT_POINT" ] && [ -w "$MOUNT_POINT" ]; then
    mkdir -p "$SESSIONS_DIR" 2>/dev/null || true
    if [ -d "$SESSIONS_DIR" ]; then
        echo "✅ Répertoire sessions prêt: $SESSIONS_DIR"
    fi
else
    echo "📁 Utilisation du répertoire local pour les sessions"
    mkdir -p /app/flask_session
fi

echo ""
echo "=========================================="
echo "🌐 DÉMARRAGE GUNICORN (Production)"
echo "=========================================="

# Démarrer avec Gunicorn (serveur WSGI production)
exec gunicorn \
    --bind=0.0.0.0:${PORT:-5000} \
    --workers=${GUNICORN_WORKERS:-4} \
    --threads=${GUNICORN_THREADS:-2} \
    --timeout=${GUNICORN_TIMEOUT:-600} \
    --worker-class=sync \
    --access-logfile=- \
    --error-logfile=- \
    --log-level=info \
    app:app