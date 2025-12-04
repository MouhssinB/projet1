# Système de Logging Centralisé

## Vue d'ensemble

Le système de logging centralisé écrit **tous** les logs de l'application dans un fichier unique : `log/application.log`

## Fonctionnalités

### 📁 Fichier unique centralisé
- **Emplacement** : `log/application.log`
- **Rotation automatique** : 50MB par fichier, 10 fichiers d'historique
- **Encodage** : UTF-8 pour supporter les caractères français

### 📊 Niveaux de logs capturés
- **DEBUG** : Informations détaillées pour le développement
- **INFO** : Informations générales sur le fonctionnement
- **WARNING** : Avertissements sur des situations inhabituelles
- **ERROR** : Erreurs qui n'empêchent pas l'application de continuer
- **CRITICAL** : Erreurs critiques

### 🔍 Sources de logs couvertes

#### Application Flask
- Toutes les routes et endpoints
- Gestion des sessions utilisateur
- Erreurs et exceptions
- Requêtes HTTP entrantes et sortantes

#### Modules métier
- `synthetiser.py` : Processus de synthèse
- `fonctions.py` : Fonctions utilitaires
- `profil_manager.py` : Gestion des profils

#### Bibliothèques externes
- **Werkzeug** : Serveur Flask
- **Azure SDK** : Interactions avec Azure
- **OpenAI** : Appels à l'API
- **Requests** : Requêtes HTTP
- **urllib3** : Transport HTTP bas niveau

### 📝 Format des logs

```
2025-09-11 14:30:25 - app - INFO - /path/to/file.py:function_name:123 - Message de log
```

**Structure** :
- **Timestamp** : Date et heure précises
- **Logger** : Nom du module/composant
- **Niveau** : DEBUG/INFO/WARNING/ERROR/CRITICAL
- **Localisation** : Fichier:fonction:ligne
- **Message** : Contenu du log

### 🔐 Logs d'accès HTTP

Chaque requête HTTP est loggée avec :
- Méthode HTTP (GET, POST, etc.)
- URL complète
- Adresse IP du client
- User-Agent
- Headers d'authentification (masqués pour la sécurité)
- Taille du contenu
- Code de statut de réponse

### 🗃️ Gestion des fichiers

#### Rotation automatique
- **Taille limite** : 50MB par fichier
- **Fichiers conservés** : 10 versions
- **Nommage** : `application.log`, `application.log.1`, etc.

#### Organisation
```
log/
├── application.log          # Fichier actuel
├── application.log.1        # Version précédente
├── application.log.2        # Plus ancienne
└── ...
```

## 📈 Utilisation

### Dans le code Python

```python
import logging

# Logger principal de l'application
app_logger = logging.getLogger('app')
app_logger.info("Message d'information")
app_logger.error("Message d'erreur")

# Logger spécifique
synthetiser_logger = logging.getLogger('synthetiser')
synthetiser_logger.debug("Détails de synthèse")
```

### Consultation des logs

```bash
# Voir les derniers logs
tail -f log/application.log

# Rechercher des erreurs
grep "ERROR\|CRITICAL" log/application.log

# Filtrer par module
grep "synthetiser" log/application.log

# Voir les accès HTTP
grep "REQUÊTE ENTRANTE\|RÉPONSE" log/application.log
```

## 🔧 Configuration

### Variables d'environnement
- Aucune configuration externe nécessaire
- Tout est configuré automatiquement au démarrage

### Personnalisation
- Modifier `setup_comprehensive_logging()` dans `app.py`
- Ajuster les niveaux de log par module
- Changer la taille des fichiers de rotation

## 📊 Monitoring

### Surveillance en temps réel
```bash
# Suivre tous les logs
tail -f log/application.log

# Suivre uniquement les erreurs
tail -f log/application.log | grep -E "(ERROR|CRITICAL)"

# Suivre les accès HTTP
tail -f log/application.log | grep "REQUÊTE ENTRANTE"
```

### Analyse des performances
- Timestamp précis pour mesurer les durées
- Logs détaillés des appels API
- Traçabilité complète des requêtes utilisateur

## 🚨 Alertes et surveillance

### Erreurs critiques
```bash
# Détecter les erreurs récentes
grep "ERROR\|CRITICAL" log/application.log | tail -20
```

### Surveillance de l'espace disque
- Vérifier régulièrement l'espace dans `/log`
- La rotation automatique limite la croissance

## 📋 Exemples de logs typiques

### Connexion utilisateur
```
2025-09-11 14:30:25 - app - INFO - app.py:index:125 - === DÉBUT SESSION UTILISATEUR ===
2025-09-11 14:30:25 - app - INFO - app.py:index:130 - Profil de session initialisé: Particulier
2025-09-11 14:30:25 - app - INFO - app.py:index:142 - Informations utilisateur extraites des headers:
```

### Requête HTTP
```
2025-09-11 14:30:30 - http_access - INFO - REQUÊTE ENTRANTE: {"method": "POST", "url": "http://localhost:5001/chat", "path": "/chat", "remote_addr": "127.0.0.1"}
2025-09-11 14:30:32 - http_access - INFO - RÉPONSE: {"method": "POST", "path": "/chat", "status_code": 200, "content_length": 1024}
```

### Synthèse de conversation
```
2025-09-11 14:35:15 - synthetiser - INFO - Starting conversation synthesis...
2025-09-11 14:35:16 - synthetiser - DEBUG - Prompt de synthèse construit: 2847 caractères
2025-09-11 14:35:20 - synthetiser - INFO - Synthèse terminée avec succès
```

## ✅ Avantages du système

1. **Centralisation** : Tous les logs dans un seul endroit
2. **Exhaustivité** : Capture tous les événements de l'application
3. **Performance** : Rotation automatique évite la surcharge
4. **Sécurité** : Masquage des informations sensibles
5. **Traçabilité** : Localisation précise du code source
6. **Maintenance** : Facilite le débogage et le monitoring
