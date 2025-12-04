# 🐳 Configuration Docker avec Azure FileShare

## Vue d'ensemble

Le Dockerfile a été configuré pour supporter le montage automatique d'Azure FileShare pour le stockage persistant des sessions Flask.

## Architecture

### Structure des répertoires

```
/app/                   # Application Flask
├── flask_session/      # Sessions locales (fallback)
└── ...

/mnt/storage/           # Point de montage Azure FileShare
└── sessions/           # Sessions persistantes (production)
```

### Flux de démarrage

```
docker-entrypoint.sh
    ↓
Vérification du montage FileShare
    ↓
    ├─ Monté → Utilise /mnt/storage/sessions
    └─ Non monté → Fallback /app/flask_session
    ↓
Démarrage Flask
```

## Fonctionnement

### 1. Montage Azure FileShare

Sur **Azure App Service** ou **Azure Container Instances**, le FileShare est monté automatiquement via la configuration Azure :

```bash
# Variables d'environnement Azure
AZURE_FILESHARE_MOUNT_POINT=/mnt/storage
AZURE_STORAGE_ACCOUNT_NAME=stgmatrainingbotdfc
AZURE_FILESHARE_NAME=stindiasimsandfc
```

### 2. Script d'entrée (`docker-entrypoint.sh`)

Le script vérifie au démarrage :
1. ✅ Si `/mnt/storage` est monté → utilise le FileShare
2. ⚠️ Si non monté → utilise le stockage local `/app/flask_session`

### 3. Détection automatique dans Flask

L'application (`app.py`) détecte automatiquement le bon emplacement :

```python
fileshare_mount = os.getenv('AZURE_FILESHARE_MOUNT_POINT', '/mnt/storage')
if os.path.exists(fileshare_mount) and os.access(fileshare_mount, os.W_OK):
    session_base_dir = os.path.join(fileshare_mount, 'sessions')
else:
    session_base_dir = os.path.join(os.getcwd(), "flask_session")
```

## Utilisation

### Build de l'image

```bash
cd /home/gs8678/projet/simsan/infra/src
docker build -t simsan-app:latest .
```

### Test en local (sans FileShare)

```bash
docker run -p 5003:5000 \
  --env-file .env \
  simsan-app:latest
```

Les sessions seront stockées dans `/app/flask_session` (éphémère).

### Déploiement sur Azure

#### Option 1 : Azure App Service

Azure App Service monte automatiquement le FileShare si configuré dans le portail :

```bash
# Configuration dans Azure Portal
# App Service → Configuration → Path mappings
# Name: storage
# Type: Azure Files
# Storage account: stgmatrainingbotdfc
# Share name: stindiasimsandfc
# Mount path: /mnt/storage
```

#### Option 2 : Azure Container Instances

```bash
az container create \
  --resource-group simsan-rg \
  --name simsan-app \
  --image <registry>/simsan-app:latest \
  --azure-file-volume-account-name stgmatrainingbotdfc \
  --azure-file-volume-account-key <key> \
  --azure-file-volume-share-name stindiasimsandfc \
  --azure-file-volume-mount-path /mnt/storage \
  --environment-variables AZURE_FILESHARE_MOUNT_POINT=/mnt/storage
```

#### Option 3 : Docker Compose (local avec montage)

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "5003:5000"
    volumes:
      - type: volume
        source: azure-fileshare
        target: /mnt/storage
    env_file:
      - .env

volumes:
  azure-fileshare:
    driver: azure-file-share
    driver_opts:
      share_name: stindiasimsandfc
      storage_account_name: stgmatrainingbotdfc
```

## Vérification

### Logs de démarrage

Lors du démarrage du conteneur, vous verrez :

```
==========================================
🚀 DÉMARRAGE APPLICATION SIMSAN
==========================================
📋 Configuration FileShare:
   Mount Point: /mnt/storage
   Sessions Dir: /mnt/storage/sessions
✅ FileShare Azure déjà monté sur /mnt/storage
✅ Répertoire sessions prêt: /mnt/storage/sessions
==========================================
🌐 DÉMARRAGE FLASK
==========================================
```

### Vérifier dans le conteneur

```bash
# Accéder au conteneur
docker exec -it <container-id> /bin/bash

# Vérifier le montage
df -h /mnt/storage
mountpoint /mnt/storage

# Vérifier les sessions
ls -la /mnt/storage/sessions/
```

## Troubleshooting

### Sessions locales au lieu du FileShare

**Symptôme** : Les logs montrent `📁 Utilisation du filesystem local`

**Causes possibles** :
1. FileShare non monté dans Azure
2. Variables d'environnement manquantes
3. Permissions insuffisantes sur `/mnt/storage`

**Solution** :
```bash
# Vérifier les variables d'environnement
echo $AZURE_FILESHARE_MOUNT_POINT
echo $AZURE_STORAGE_ACCOUNT_NAME

# Vérifier les permissions
ls -ld /mnt/storage
```

### Erreur de montage

**Symptôme** : `⚠️ FileShare non monté`

**Solution** :
- Sur Azure : Vérifier la configuration du FileShare dans le portail
- En local : Utiliser le fallback local (comportement normal)

### Sessions perdues au redémarrage

**Symptôme** : Les utilisateurs doivent se reconnecter après redémarrage

**Cause** : FileShare non configuré, sessions dans le conteneur éphémère

**Solution** : Configurer le montage Azure FileShare (voir section Déploiement)

## Avantages

✅ **Persistance** : Sessions conservées entre redémarrages
✅ **Scalabilité** : Sessions partagées entre plusieurs instances
✅ **Fallback automatique** : Fonctionne en local sans FileShare
✅ **Zero downtime** : Pas d'interruption lors des déploiements

## Sécurité

- 🔒 FileShare accessible uniquement via Azure credentials
- 🔒 Montage en lecture/écriture avec permissions contrôlées
- 🔒 Sessions chiffrées avec `SESSION_USE_SIGNER=True`
- 🔒 Cookies sécurisés en production (`SESSION_COOKIE_SECURE=True`)

## Performance

- ⚡ Latence : ~5-10ms (Azure FileShare Premium)
- ⚡ Cache local : Sessions en mémoire Flask
- ⚡ Nettoyage automatique : Sessions > 24h supprimées

## Fichiers modifiés

1. **Dockerfile** : Installation de `cifs-utils`, création de `/mnt/storage`
2. **docker-entrypoint.sh** : Script de démarrage avec détection FileShare
3. **app.py** : Détection automatique du point de montage
4. **.env** : Configuration des variables Azure

## Références

- [Azure Files documentation](https://docs.microsoft.com/azure/storage/files/)
- [Flask-Session documentation](https://flask-session.readthedocs.io/)
- [Docker volumes](https://docs.docker.com/storage/volumes/)
