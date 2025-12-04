# Image RedHat avec Python 3.11
FROM imagehub-projets.intra.groupama.fr/gtec-image/python-311-gtec:1.2.0
#FROM python:3.11.11-slim
# Passer en root pour installer les certificats
USER root

# Créer les répertoires nécessaires pour RedHat
RUN mkdir -p /app && mkdir -p /etc/pki/ca-trust/source/anchors/

# Installer cifs-utils pour le montage du FileShare Azure (si besoin)
# Nettoyer le cache pour réduire la taille de l'image
# hadolint ignore=DL3033,DL3041
RUN (yum install -y cifs-utils && yum clean all) || (dnf install -y cifs-utils && dnf clean all) || true

# Créer les répertoires d'application et définir les permissions
# Créer le point de montage pour Azure FileShare
RUN mkdir -p /app/flask_session /app/data/conversations /app/data/syntheses /app/certs /mnt/storage && \
    chown -R default:root /app /mnt/storage

# Copier les certificats (nécessite root)
COPY certs/* /etc/ssl/certs/

# Copier le script d'entrée et le rendre exécutable (nécessite root)
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh && \
    chown default:root /app/docker-entrypoint.sh

# Définir le répertoire de travail
WORKDIR /app

# Revenir à l'utilisateur par défaut
USER default

# Copier les fichiers de l'application
COPY app/ /app/app/
COPY auth/ /app/auth/
COPY core/ /app/core/
COPY data/ /app/data/
COPY static/ /app/static/
COPY templates/ /app/templates/
# COPY tests/ /app/tests/  # Tests non nécessaires en production
COPY main_fastapi.py .
COPY pyproject.toml .
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir --upgrade pip==25.1.1 && \
    pip install --no-cache-dir uv==0.7.18 && \
    uv pip install --no-cache-dir -r requirements.txt && \
    uv init . && \
    pip list

# Exposer le port utilisé par FastAPI
EXPOSE 8000

# Variables d'environnement pour FastAPI
ENV PORT=8000

# Variables d'environnement pour les certificats SSL (utilisation des certificats système RedHat)
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-bundle.trust.crt
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-bundle.crt
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-bundle.crt
ENV PYTHONHTTPSVERIFY=1

# Commande de démarrage (utilise le script d'entrée pour gérer le FileShare)
CMD ["/app/docker-entrypoint.sh"]
