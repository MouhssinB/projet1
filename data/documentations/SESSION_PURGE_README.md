# Purge des Sessions au Démarrage

## 📋 Description

Cette fonctionnalité permet de supprimer automatiquement **tous les fichiers de session** lors du démarrage de l'application. Cela garantit un démarrage propre sans sessions orphelines.

## ⚙️ Configuration

Ajoutez cette variable à votre fichier `.env` :

```bash
# Activer/Désactiver la purge des sessions au démarrage
# Par défaut: True (activé)
PURGE_SESSIONS_ON_STARTUP=True
```

## 🎯 Fonctionnement

### Au Démarrage de l'Application

1. **Vérification** du répertoire de sessions
2. **Suppression** de tous les fichiers de session
3. **Conservation** des fichiers cachés (`.gitkeep`, `.folder_init`, etc.)
4. **Affichage** des statistiques de suppression

### Exemple de Log

```
📁 Utilisation du filesystem local pour les sessions: /app/flask_session
🧹 Purge du répertoire de sessions: /app/flask_session
   ✅ 23 fichier(s) de session supprimé(s) (1.45 MB libérés)
```

## 🔧 Cas d'Usage

### ✅ Quand Activer la Purge

- **Environnement de développement** : Démarrage propre à chaque fois
- **Après un déploiement** : Éviter les sessions corrompues
- **Après une mise à jour** : Forcer la reconnexion des utilisateurs
- **En cas de problème** : Réinitialiser toutes les sessions

### ❌ Quand Désactiver la Purge

- **Production avec haute disponibilité** : Pour ne pas déconnecter les utilisateurs lors d'un redémarrage
- **Sessions persistantes critiques** : Si vous devez conserver les sessions actives

## 🚨 Important

### Impact Utilisateurs

⚠️ **Tous les utilisateurs connectés seront déconnectés** lors du redémarrage de l'application si la purge est activée.

### Fichiers Conservés

Les fichiers commençant par `.` ne sont **pas supprimés** :
- `.gitkeep`
- `.folder_init`
- `.htaccess`
- etc.

## 📊 Configuration Recommandée

### Développement
```bash
PURGE_SESSIONS_ON_STARTUP=True
```

### Production (déploiement manuel)
```bash
PURGE_SESSIONS_ON_STARTUP=True
```

### Production (haute disponibilité / multi-instance)
```bash
PURGE_SESSIONS_ON_STARTUP=False
# Utiliser un système de nettoyage périodique à la place
```

## 🔍 Vérification

Pour vérifier si la purge a eu lieu, consultez les logs au démarrage de l'application.

## 🐛 Troubleshooting

### Problème : Les sessions ne sont pas supprimées

**Solutions :**
1. Vérifier que `PURGE_SESSIONS_ON_STARTUP=True`
2. Vérifier les permissions d'écriture sur le répertoire de sessions
3. Consulter les logs pour voir les erreurs éventuelles

### Problème : Erreurs de permission

```bash
# Vérifier les permissions
ls -la flask_session/

# Corriger si nécessaire (développement uniquement)
chmod -R 755 flask_session/
```

## 💡 Alternative : Désactivation Temporaire

Pour désactiver temporairement la purge sans modifier le `.env` :

```bash
# Au lancement
PURGE_SESSIONS_ON_STARTUP=False python app.py
```

## 🔄 Combinaison avec Autres Fonctionnalités

Cette fonctionnalité peut être combinée avec :
- **PERMANENT_SESSION_LIFETIME** : Durée de vie des sessions
- **SESSION_FILE_THRESHOLD** : Nombre maximum de fichiers de session

## 📝 Exemple Complet de Configuration

```bash
# .env

# Sessions
SESSION_PERMANENT=True
SESSION_LIFETIME_HOURS=24
SESSION_FILE_THRESHOLD=500

# Purge au démarrage
PURGE_SESSIONS_ON_STARTUP=True

# Répertoire de sessions (auto-détecté)
# AZURE_FILESHARE_MOUNT_POINT=/mnt/storage
```
