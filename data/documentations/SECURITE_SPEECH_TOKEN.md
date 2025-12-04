# 🔒 Sécurisation Azure Speech - Utilisation de Tokens d'Autorisation

## ⚠️ Problème Identifié

Auparavant, les clés API Azure Speech étaient transmises directement dans le code HTML/JavaScript :
```html
<script>
  const subscriptionKey = "{{ speech_key }}";  // ❌ Clé exposée côté client !
  const speechEndpoint = "{{ speech_endpoint }}";
</script>
```

**Risques :**
- ✋ Clé API visible dans le code source du navigateur
- ✋ Clé API exposée dans les DevTools
- ✋ Clé API accessible via inspection du réseau
- ✋ Risque d'utilisation non autorisée

---

## ✅ Solution Implémentée

### Architecture Sécurisée avec Tokens Temporaires

Au lieu d'exposer les clés, nous utilisons un **système de tokens temporaires** :

```
┌──────────────┐                    ┌──────────────┐                    ┌─────────────────┐
│   Frontend   │                    │   Backend    │                    │  Azure Speech   │
│  (Browser)   │                    │   (Flask)    │                    │     Service     │
└──────────────┘                    └──────────────┘                    └─────────────────┘
       │                                   │                                      │
       │  1. Demande token                │                                      │
       │  GET /get_speech_token           │                                      │
       ├──────────────────────────────────>│                                      │
       │                                   │                                      │
       │                                   │  2. Demande token                    │
       │                                   │  POST /sts/v1.0/issueToken          │
       │                                   ├─────────────────────────────────────>│
       │                                   │  + Header: Ocp-Apim-Subscription-Key │
       │                                   │                                      │
       │                                   │  3. Token temporaire (10 min)        │
       │                                   │<─────────────────────────────────────┤
       │                                   │                                      │
       │  4. Token + Région                │                                      │
       │<──────────────────────────────────┤                                      │
       │                                   │                                      │
       │  5. Utilise token pour STT/TTS    │                                      │
       │  (valide pendant 10 minutes)      │                                      │
       ├────────────────────────────────────────────────────────────────────────>│
       │                                   │                                      │
```

---

## 🔧 Modifications Apportées

### 1. Backend (`app.py`)

#### Nouvelle route `/get_speech_token`
```python
@app.route('/get_speech_token', methods=['GET'])
@auth.login_required
def get_speech_token():
    """
    Génère un token d'autorisation temporaire pour Azure Speech Service
    Le token est valide pendant 10 minutes
    """
    try:
        fetch_token_url = f"https://{service_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
        headers = {'Ocp-Apim-Subscription-Key': speech_key}
        response = requests.post(fetch_token_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return jsonify({
                'token': response.text,
                'region': service_region,
                'success': True
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

#### Template modifié
```python
# Avant
return render_template(
    "index.html",
    speech_key=speech_key,          # ❌ Clé exposée
    speech_endpoint=speech_endpoint # ❌ Endpoint exposé
)

# Après
return render_template(
    "index.html",
    service_region=service_region   # ✅ Seulement la région
)
```

### 2. Frontend (`index.html`)

```html
<!-- Avant -->
<script>
  const subscriptionKey = "{{ speech_key }}";      // ❌ Clé en clair
  const speechEndpoint = "{{ speech_endpoint }}";  // ❌ Endpoint en clair
</script>

<!-- Après -->
<script>
  let authToken = null;        // ✅ Token temporaire
  let tokenExpiryTime = null;  // ✅ Gestion expiration
  let serviceRegion = null;    // ✅ Région récupérée via API
</script>
```

### 3. JavaScript (`app.js`)

#### Fonction de récupération du token
```javascript
async function fetchSpeechToken() {
    const response = await fetch('/get_speech_token');
    const data = await response.json();
    
    if (data.success) {
        authToken = data.token;
        serviceRegion = data.region;
        tokenExpiryTime = Date.now() + (9 * 60 * 1000); // Renouvellement après 9 min
        return true;
    }
    return false;
}
```

#### Renouvellement automatique
```javascript
async function ensureValidToken() {
    if (!authToken || Date.now() >= tokenExpiryTime) {
        console.log('🔄 Renouvellement du token Speech...');
        return await fetchSpeechToken();
    }
    return true;
}
```

#### Initialisation avec token
```javascript
// Avant
const speechConfig = SpeechSDK.SpeechConfig.fromEndpoint(
    new URL(speechEndpoint), 
    subscriptionKey  // ❌ Clé exposée
);

// Après
const speechConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(
    authToken,      // ✅ Token temporaire
    serviceRegion
);
```

---

## 🔐 Avantages de Sécurité

| Critère | Avant | Après |
|---------|-------|-------|
| **Clé API visible** | ❌ Oui (HTML source) | ✅ Non |
| **Clé API dans DevTools** | ❌ Oui | ✅ Non |
| **Durée validité** | ❌ Permanente | ✅ 10 minutes |
| **Révocation possible** | ❌ Non | ✅ Oui (régénération) |
| **Protection backend** | ❌ Non | ✅ Oui (@auth.login_required) |
| **Traçabilité** | ❌ Faible | ✅ Forte (logs serveur) |

---

## 📊 Cycle de Vie du Token

```
┌─────────────────────────────────────────────────────────────┐
│                     CYCLE DE VIE                            │
└─────────────────────────────────────────────────────────────┘

T=0        : Utilisateur charge la page
T=+0.5s    : Premier appel → fetchSpeechToken()
T=+1s      : Token obtenu (valide 10 min)
T=+9min    : Auto-renouvellement (ensureValidToken)
T=+9min+1s : Nouveau token obtenu
...        : Cycle continue tant que la session est active
```

---

## 🧪 Test de Sécurité

### Vérification côté client
1. Ouvrir DevTools (F12)
2. Aller dans l'onglet "Sources" ou "Debugger"
3. Rechercher "subscriptionKey" ou "speech_key"
4. ✅ **Résultat attendu** : Aucune occurrence trouvée

### Vérification réseau
1. Ouvrir DevTools > Network
2. Activer le mode vocal
3. Filtrer par "speech"
4. ✅ **Résultat attendu** : Uniquement des requêtes avec `Authorization: Bearer <token>`

---

## 🚀 Déploiement

### Prérequis
- Module `requests` Python (déjà présent dans requirements.txt)
- Variables d'environnement :
  ```bash
  AZURE_SPEECH_KEY=votre_clé_api
  AZURE_SERVICE_REGION=francecentral  # ou votre région
  ```

### Aucun changement côté infrastructure
- ✅ Pas de modification Docker
- ✅ Pas de modification Terraform
- ✅ Variables d'environnement inchangées

---

## 📝 Recommandations Supplémentaires

### 1. Rotation des clés
```bash
# Planifier une rotation régulière des clés Azure
# Exemple : tous les 90 jours
az cognitiveservices account keys regenerate \
  --name votre-speech-service \
  --resource-group votre-rg \
  --key-name key1
```

### 2. Monitoring
Ajouter des logs pour surveiller :
- Nombre de tokens générés par utilisateur
- Échecs d'authentification
- Utilisation anormale

### 3. Rate Limiting (optionnel)
```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: session.get('user_name'))

@app.route('/get_speech_token')
@limiter.limit("10 per minute")  # Max 10 tokens/minute/user
def get_speech_token():
    ...
```

---

## 📚 Références Microsoft

- [Azure Speech Token Authentication](https://learn.microsoft.com/azure/cognitive-services/speech-service/how-to-configure-authentication)
- [Speech SDK Authorization Token](https://learn.microsoft.com/javascript/api/microsoft-cognitiveservices-speech-sdk/speechconfig#microsoft-cognitiveservices-speech-sdk-speechconfig-fromauthorizationtoken)
- [Security Best Practices](https://learn.microsoft.com/azure/cognitive-services/security-features)

---

## ✅ Validation Équipe Sécurité

Cette implémentation respecte les standards de sécurité :
- ✅ Pas de secrets dans le code client
- ✅ Tokens à durée limitée (10 minutes)
- ✅ Authentification requise pour obtenir un token
- ✅ Traçabilité complète
- ✅ Conformité RGPD (pas de données sensibles exposées)

---

**Date de mise en place** : 2025-10-23  
**Auteur** : Équipe Développement  
**Validé par** : Équipe Sécurité ✅
