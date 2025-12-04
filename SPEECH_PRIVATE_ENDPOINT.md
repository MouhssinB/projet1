# Gestion automatique Private Endpoint / Public Endpoint pour Azure Speech

## 🎯 Problématique

Lorsqu'Azure Speech Service est configuré avec un **Private Endpoint**, l'API de génération de tokens (`/sts/v1.0/issueToken`) est **désactivée** par Azure pour des raisons de sécurité réseau.

**Erreur typique** :
```json
{
  "error": {
    "code": "BadRequest",
    "message": "Virtual network/Firewall is configured, Token API is disabled."
  }
}
```

## ✅ Solution implémentée : Détection automatique

Le système détecte automatiquement le mode de déploiement et s'adapte :

| Mode | Détection | Authentification | Sécurité |
|------|-----------|------------------|----------|
| **Public Endpoint** | Token API répond 200 | Token temporaire (10 min) | ✅ Clé jamais exposée |
| **Private Endpoint** | Token API erreur 400/timeout | Clé directe | ✅ Réseau privé sécurisé |

## 📐 Architecture

### Backend : `/get_speech_config` (app.py)

```python
@app.route('/get_speech_config', methods=['GET'])
@auth.login_required
def get_speech_config():
    """
    Retourne la configuration Speech selon l'environnement détecté
    """
    # 1. Tenter d'obtenir un token
    response = requests.post(token_url, headers=headers, timeout=5)
    
    # 2. Si succès → Mode PUBLIC (token)
    if response.status_code == 200:
        return jsonify({
            'mode': 'token',
            'token': response.text,
            'region': service_region
        })
    
    # 3. Si erreur "Token API is disabled" → Mode PRIVATE (clé)
    if 'Token API is disabled' in error_message:
        return jsonify({
            'mode': 'subscription_key',
            'subscription_key': speech_key,  # OK car réseau privé
            'region': service_region
        })
```

### Frontend : `app.js`

```javascript
// Variables globales
let speechAuthMode = null;        // 'token' ou 'subscription_key'
let authToken = null;             // Mode public
let subscriptionKey = null;       // Mode private

// Récupération de la config
async function fetchSpeechConfig() {
    const response = await fetch('/get_speech_config');
    const data = await response.json();
    
    if (data.mode === 'token') {
        authToken = data.token;
        console.log('✅ Mode PUBLIC - Token obtenu');
    } else if (data.mode === 'subscription_key') {
        subscriptionKey = data.subscription_key;
        console.log('✅ Mode PRIVATE - Clé directe (réseau sécurisé)');
    }
}

// Initialisation SDK
async function initializeSpeechSDK() {
    let speechConfig;
    
    if (speechAuthMode === 'token') {
        // Mode Public : token temporaire
        speechConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(
            authToken, 
            serviceRegion
        );
    } else if (speechAuthMode === 'subscription_key') {
        // Mode Private Endpoint : clé directe
        speechConfig = SpeechSDK.SpeechConfig.fromSubscription(
            subscriptionKey, 
            serviceRegion
        );
    }
}
```

## 🔒 Considérations de sécurité

### Mode Public Endpoint (production internet)
- ✅ **Token temporaire** : Expire après 10 minutes
- ✅ **Clé protégée** : Jamais exposée côté client
- ✅ **Renouvellement auto** : Token renouvelé avant expiration
- ⚠️ **Token visible** : Peut être intercepté pendant 10 min (risque limité)

### Mode Private Endpoint (réseau privé)
- ✅ **Réseau isolé** : Accessible uniquement depuis le VNet Azure
- ✅ **Pas d'exposition internet** : Clé ne circule que dans le réseau privé
- ✅ **Token API désactivée** : Réduit la surface d'attaque
- ⚠️ **Clé en session** : Visible dans DevTools (acceptable car réseau privé)

## 🔍 Méthodes de détection

Le backend utilise **3 méthodes** pour détecter le Private Endpoint :

### 1. Erreur HTTP 400 avec message explicite
```python
if response.status_code == 400:
    error_message = response.json().get('error', {}).get('message', '')
    if 'Token API is disabled' in error_message:
        # → Mode Private Endpoint détecté
```

### 2. Timeout de connexion
```python
except requests.exceptions.Timeout:
    # Probable Private Endpoint (timeout DNS ou firewall)
    return mode: 'subscription_key'
```

### 3. Erreur réseau générale
```python
except requests.exceptions.RequestException:
    # Erreur réseau → fallback sur clé directe
    return mode: 'subscription_key'
```

## 📊 Logs de diagnostic

Le système log automatiquement le mode détecté :

**Mode Public détecté** :
```
✅ Mode PUBLIC - Token généré avec succès
🔧 Initialisation SDK avec token (mode public)
SDK Azure Speech initialisé avec succès [sécurisé (token)]
```

**Mode Private Endpoint détecté** :
```
⚠️ Private Endpoint détecté - Token API désactivée
✅ Mode PRIVATE - Utilisation de la clé directe (réseau sécurisé)
🔧 Initialisation SDK avec clé (mode private endpoint)
SDK Azure Speech initialisé avec succès [réseau privé (clé directe)]
```

## 🧪 Tests

### Test 1 : Mode Public
```bash
# Sans Private Endpoint
curl -X GET https://votre-app.azurewebsites.net/get_speech_config

# Réponse attendue :
{
  "mode": "token",
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "region": "westeurope",
  "success": true
}
```

### Test 2 : Mode Private Endpoint
```bash
# Avec Private Endpoint configuré
curl -X GET https://votre-app.azurewebsites.net/get_speech_config

# Réponse attendue :
{
  "mode": "subscription_key",
  "subscription_key": "abc123...",
  "region": "westeurope",
  "success": true,
  "info": "Private Endpoint - Clé utilisée directement (réseau sécurisé)"
}
```

## 🚀 Avantages de cette approche

1. **Automatique** : Pas de configuration manuelle selon l'environnement
2. **Robuste** : Fallback sur clé si token inaccessible
3. **Transparent** : L'utilisateur ne voit pas la différence
4. **Sécurisé** : 
   - Mode public : Token temporaire
   - Mode private : Clé isolée dans réseau privé
5. **Diagnosticable** : Logs clairs du mode utilisé

## 🔧 Variables d'environnement requises

```bash
# Backend (.env)
AZURE_SPEECH_KEY=votre_cle_speech
AZURE_SERVICE_REGION=westeurope
AZURE_SPEECH_ENDPOINT=https://votre-resource.cognitiveservices.azure.com/
```

Aucune variable supplémentaire n'est nécessaire - le système détecte automatiquement le mode.

## 📝 Recommandations

### Pour un environnement de production PUBLIC :
- ✅ Utiliser le mode token (automatique si pas de Private Endpoint)
- ✅ Configurer un monitoring des renouvellements de token
- ✅ Prévoir un fallback sur clé en cas d'erreur token

### Pour un environnement de production PRIVATE :
- ✅ Configurer le Private Endpoint dans Azure Portal
- ✅ Vérifier que le VNet permet l'accès depuis l'App Service
- ✅ Accepter l'utilisation de la clé (sécurisée par le réseau privé)
- ✅ Monitorer les logs pour confirmer "Mode PRIVATE" au démarrage

## 🐛 Dépannage

### Erreur : "Mode d'authentification Speech non défini"
**Cause** : Échec de récupération de la config au démarrage
**Solution** : Vérifier les variables d'environnement `AZURE_SPEECH_KEY` et `AZURE_SERVICE_REGION`

### Erreur persistante même en Private Endpoint
**Cause** : Le backend essaie toujours d'appeler le Token API
**Solution** : Vérifier que le timeout est court (5s) pour détecter rapidement le Private Endpoint

### Clé visible dans les DevTools en mode Private
**Comportement normal** : La clé est visible car le mode Private Endpoint nécessite son utilisation directe. C'est sécurisé car :
- La ressource n'est accessible que depuis le VNet
- La clé ne peut être utilisée depuis internet
- Le réseau privé Azure isole complètement la communication

## 📚 Références Azure

- [Azure Speech Service - Private Endpoints](https://docs.microsoft.com/en-us/azure/cognitive-services/speech-service/speech-services-private-link)
- [Token authentication limitations](https://docs.microsoft.com/en-us/azure/cognitive-services/speech-service/rest-speech-to-text#authentication)
- [VNet integration for App Service](https://docs.microsoft.com/en-us/azure/app-service/overview-vnet-integration)
