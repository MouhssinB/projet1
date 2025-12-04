# 📁 Stockage Unifié - FileShare Azure

## Vue d'ensemble

L'application utilise désormais un système de stockage unifié qui s'adapte automatiquement à l'environnement :

- **🚀 Production (Azure)** : Lecture/écriture directe dans le FileShare Azure monté sur `/mnt/storage`
- **💻 Développement (Local)** : Lecture/écriture dans le répertoire local `data/`

## Changements principaux

### ✅ Ce qui a été fait

1. **Suppression de la synchronisation périodique**
   - Ancien système : synchronisation toutes les 10 minutes entre `data/` local et FileShare Azure
   - Nouveau système : accès direct au FileShare monté (production) ou au répertoire local (développement)

2. **Nouveau `StorageManager`**
   - Détecte automatiquement l'environnement (production vs développement)
   - Gère tous les chemins de fichiers de manière transparente
   - Fichier : `core/storage_manager.py`

3. **Adaptation des fonctions de stockage**
   - `core/fonctions_fileshare.py` : réécriture complète pour utiliser le `StorageManager`
   - Toutes les fonctions de lecture/écriture utilisent maintenant le bon emplacement

4. **Adaptation du logging**
   - `core/fonctions.py` : `log_to_journal()` écrit directement dans le FileShare
   - `core/async_logger.py` : logger asynchrone adapté pour utiliser le `StorageManager`

5. **Nettoyage de `app.py`**
   - Suppression de l'import `AzureFileShareSync`
   - Suppression du code de démarrage de la synchronisation
   - L'application est maintenant plus simple et plus directe

6. **Mise à jour du `.env`**
   - Suppression de `INTERVAL_MINUTES_SYNC_FILESHARE` (n'est plus nécessaire)
   - Ajout de commentaires explicatifs sur le fonctionnement

## Structure de stockage

### Production (Azure - /mnt/storage/)
```
/mnt/storage/
├── admin/
│   ├── journal.csv          # Journal des événements
│   └── application.log       # Logs de l'application
├── utilisateurs/
│   └── user_email/
│       ├── conversations/    # Conversations utilisateur
│       └── syntheses/        # Synthèses générées
└── sessions/                 # Sessions Flask
```

### Développement (Local - data/)
```
data/
├── admin/
│   ├── journal.csv
│   └── application.log
├── utilisateurs/
│   └── user_email/
│       ├── conversations/
│       └── syntheses/
├── conversations/            # Anciens fichiers (compatibilité)
├── syntheses/                # Anciens fichiers (compatibilité)
└── suivis/                   # Anciens fichiers (compatibilité)
```

## Comment ça fonctionne

### Détection automatique de l'environnement

Le `StorageManager` détecte automatiquement si le FileShare est monté :

```python
# Vérifie si /mnt/storage existe et est accessible en écriture
if os.path.exists('/mnt/storage') and os.access('/mnt/storage', os.W_OK):
    # Mode PRODUCTION : utiliser le FileShare monté
    base_path = Path('/mnt/storage')
else:
    # Mode DÉVELOPPEMENT : utiliser le répertoire local
    base_path = Path(os.getcwd()) / 'data'
```

### Utilisation dans le code

Toutes les fonctions de stockage utilisent maintenant le `StorageManager` :

```python
from core.storage_manager import get_storage_manager

storage = get_storage_manager()

# Sauvegarder un fichier
file_path = storage.base_path / "admin" / "journal.csv"
storage.save_file(file_path, content)

# Lire un fichier
success, content = storage.read_file(file_path)

# Lister des fichiers
files = storage.list_files(storage.base_path / "utilisateurs")
```

## Avantages

1. **✅ Simplicité** : Plus besoin de synchronisation, tout est direct
2. **✅ Performance** : Pas de latence de synchronisation (toutes les 10 minutes)
3. **✅ Fiabilité** : Pas de risque de perte de données entre deux synchronisations
4. **✅ Transparence** : Le code ne sait pas s'il utilise le FileShare ou le stockage local
5. **✅ Développement** : Fonctionne exactement pareil en local et en production

## Migration

### Anciens fichiers locaux

Si vous avez des données dans l'ancien format (`data/suivis/journal.csv`, `data/conversations/`, etc.), elles seront toujours accessibles mais ne seront plus synchronisées automatiquement.

Pour migrer manuellement les anciennes données :

```bash
# En développement local
# Les données sont déjà dans data/, pas besoin de migration

# En production avec FileShare monté sur /mnt/storage
# Copier les anciennes données locales vers le FileShare
cp -r data/conversations/* /mnt/storage/admin/
cp -r data/syntheses/* /mnt/storage/admin/
cp data/suivis/journal.csv /mnt/storage/admin/
```

## Configuration Azure

### Variables d'environnement requises

```bash
# Point de montage du FileShare (production)
AZURE_FILESHARE_MOUNT_POINT=/mnt/storage

# Nom du FileShare (pour information)
AZURE_FILESHARE_NAME=stindiasimsandfc
```

### Montage du FileShare dans Azure

Le FileShare doit être monté automatiquement par Azure App Service sur `/mnt/storage`.

Configuration dans le portail Azure :
- **App Service** → **Configuration** → **Path mappings**
- **Name**: storage
- **Type**: Azure Files
- **Storage account**: stindiasimsandfc
- **Share name**: stindiasimsandfc
- **Mount path**: /mnt/storage

## Logs au démarrage

L'application affiche maintenant des informations claires sur le mode de stockage utilisé :

```
🔧 Initialisation de la structure de stockage...
📁 StorageManager initialisé
   Mode: PRODUCTION (FileShare)
   Base path: /mnt/storage
✅ Structure de stockage initialisée
```

ou

```
🔧 Initialisation de la structure de stockage...
📁 StorageManager initialisé
   Mode: DÉVELOPPEMENT (Local)
   Base path: /home/user/projet/simsan/infra/src/data
✅ Structure de stockage initialisée
```

## Fichiers modifiés

- ✅ `core/storage_manager.py` (nouveau)
- ✅ `core/fonctions_fileshare.py` (réécriture complète)
- ✅ `core/fonctions.py` (adaptation `log_to_journal`)
- ✅ `core/async_logger.py` (adaptation pour StorageManager)
- ✅ `app.py` (suppression synchronisation)
- ✅ `.env` (suppression `INTERVAL_MINUTES_SYNC_FILESHARE`)

## Fichiers obsolètes (peuvent être supprimés)

- ⚠️ `core/azure_sync.py` (n'est plus utilisé)
- ⚠️ `core/fonctions_fileshare.py.old` (backup de l'ancienne version)
- ⚠️ `core/fonctions_fileshare_backup.py` (backup de l'ancienne version)

## Tests

Pour tester le bon fonctionnement :

1. **En développement** :
   ```bash
   # Démarrer l'application
   python app.py
   
   # Vérifier que les logs indiquent "Mode: DÉVELOPPEMENT (Local)"
   # Vérifier que les fichiers sont créés dans data/
   ```

2. **En production** :
   ```bash
   # Démarrer l'application
   # Vérifier que les logs indiquent "Mode: PRODUCTION (FileShare)"
   # Vérifier que les fichiers sont créés dans /mnt/storage/
   ```

## Support

En cas de problème :
- Vérifier les logs au démarrage pour confirmer le mode détecté
- Vérifier que `/mnt/storage` est bien monté en production
- Vérifier les permissions d'écriture sur le répertoire de stockage
