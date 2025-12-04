# 🔧 Résolution Problème DNS - Azure Web App

## ❌ Erreur Rencontrée

```
CRITICAL - Exception lors de la génération du token Speech: 
HTTPSConnectionPool(host='westeurope.api.cognitive.microsoft.com', port=443): 
Max retries exceeded with url: /sts/v1.0/issueToken 
(Caused by NameResolutionError: Failed to resolve 'westeurope.api.cognitive.microsoft.com')
```

**Cause** : Problème de résolution DNS dans Azure Web App (restrictions réseau sortant)

---

## ✅ Solution Implémentée

### Modification 1 : Utilisation de l'Endpoint Complet

Au lieu d'utiliser :
```python
# ❌ AVANT (problème DNS)
fetch_token_url = f"https://{service_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
```

Maintenant on utilise :
```python
# ✅ APRÈS (résout le problème)
if speech_endpoint:
    endpoint_base = speech_endpoint.rstrip('/')
    fetch_token_url = f"{endpoint_base}/sts/v1.0/issueToken"
else:
    # Fallback
    fetch_token_url = f"https://{service_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
```

### Modification 2 : Ajout de Retry Logic

- ✅ 3 tentatives au lieu d'1
- ✅ Timeout augmenté à 30s
- ✅ Délai de 1s entre les tentatives
- ✅ Logs détaillés pour le debugging

---

## 🔧 Configuration Azure

### Variables d'Environnement à Vérifier

Dans votre **Azure Web App** > **Configuration** > **Application settings** :

```bash
# ✅ OBLIGATOIRE
AZURE_SPEECH_KEY=<votre_clé_api>

# ✅ MÉTHODE 1 : Utiliser l'endpoint complet (RECOMMANDÉ)
AZURE_SPEECH_ENDPOINT=https://votre-ressource.cognitiveservices.azure.com

# OU

# ✅ MÉTHODE 2 : Utiliser la région (peut avoir des problèmes DNS)
AZURE_SERVICE_REGION=westeurope
```

### Comment Trouver l'Endpoint

1. Aller sur **Azure Portal**
2. Ouvrir votre ressource **Cognitive Services** ou **Speech**
3. Dans **Keys and Endpoint** :
   - Copier **Endpoint** : `https://xxxxx.cognitiveservices.azure.com`
   - Copier **Key** : votre clé API

### Configuration Recommandée

**Option A - Endpoint Complet (Meilleur pour Azure Web Apps)** :
```bash
AZURE_SPEECH_KEY=abc123...
AZURE_SPEECH_ENDPOINT=https://ma-ressource-speech.cognitiveservices.azure.com
AZURE_SERVICE_REGION=westeurope  # Pour info, mais pas utilisé pour le token
```

**Option B - Région uniquement (Peut avoir des problèmes DNS)** :
```bash
AZURE_SPEECH_KEY=abc123...
AZURE_SERVICE_REGION=westeurope
```

---

## 🔍 Diagnostic

### 1. Vérifier les Variables d'Environnement

Dans votre Web App :

```bash
# Azure Cloud Shell ou Azure CLI
az webapp config appsettings list \
  --name <nom-webapp> \
  --resource-group <nom-rg> \
  --query "[?name=='AZURE_SPEECH_ENDPOINT' || name=='AZURE_SPEECH_KEY' || name=='AZURE_SERVICE_REGION']"
```

### 2. Vérifier les Logs

```bash
# Streaming des logs
az webapp log tail \
  --name <nom-webapp> \
  --resource-group <nom-rg>
```

Cherchez :
- ✅ `Utilisation endpoint configuré: https://...`
- ❌ `Erreur réseau:` ou `NameResolutionError`

### 3. Tester la Connectivité

Depuis la **Console SSH** de votre Web App :

```bash
# Test DNS
nslookup westeurope.api.cognitive.microsoft.com

# Test réseau
curl -v https://westeurope.api.cognitive.microsoft.com/sts/v1.0/issueToken \
  -H "Ocp-Apim-Subscription-Key: VOTRE_CLE" \
  -X POST
```

---

## 🚨 Problèmes Courants

### Problème 1 : Intégration VNet

**Symptôme** : DNS ne résout pas les domaines publics

**Solution** :
1. Aller dans **Networking** > **VNet Integration**
2. Si activé, vérifier le **Private DNS** ou **DNS Settings**
3. Ajouter un **DNS Server** : `168.63.129.16` (Azure DNS)

### Problème 2 : Restrictions Réseau Sortant

**Symptôme** : Connexion refusée ou timeout

**Solution** :
1. Vérifier **Outbound Rules** du NSG (Network Security Group)
2. Autoriser le trafic vers :
   - `*.cognitiveservices.azure.com` (port 443)
   - `*.api.cognitive.microsoft.com` (port 443)

### Problème 3 : Firewall Azure Speech

**Symptôme** : Accès refusé même avec bonne clé

**Solution** :
1. Dans votre ressource Speech > **Networking**
2. Vérifier les **Firewall rules**
3. Options :
   - **Public endpoint (all networks)** : Recommandé pour débuter
   - **Selected networks** : Ajouter l'IP de votre Web App

---

## ✅ Validation

### Test depuis Azure

1. **Redémarrer la Web App** :
   ```bash
   az webapp restart --name <nom-webapp> --resource-group <nom-rg>
   ```

2. **Vérifier les logs** :
   ```bash
   az webapp log tail --name <nom-webapp> --resource-group <nom-rg>
   ```

3. **Tester l'endpoint** :
   ```bash
   curl https://votre-webapp.azurewebsites.net/get_speech_token
   ```

### Test depuis l'Application

1. Ouvrir votre application
2. Activer le mode vocal
3. Vérifier la console JavaScript (F12) :
   - ✅ `Token Speech obtenu (valide 10 minutes)`
   - ❌ `Erreur lors de l'obtention du token`

---

## 📝 Checklist de Résolution

- [ ] Variables d'environnement configurées dans Azure Web App
- [ ] `AZURE_SPEECH_ENDPOINT` défini avec l'URL complète
- [ ] `AZURE_SPEECH_KEY` défini avec la clé valide
- [ ] Web App redémarrée après modification config
- [ ] Logs vérifiés (pas d'erreur DNS)
- [ ] Test `/get_speech_token` réussi
- [ ] Mode vocal fonctionne dans l'application

---

## 🆘 Si le Problème Persiste

### Option 1 : Service Endpoint

Ajouter un **Service Endpoint** pour Cognitive Services :

1. Dans votre Web App > **Networking** > **VNet Integration**
2. Aller dans votre VNet > **Service endpoints**
3. Ajouter : `Microsoft.CognitiveServices`

### Option 2 : Private Link

Si vous avez besoin d'une connexion privée :

1. Créer un **Private Endpoint** pour votre ressource Speech
2. Configurer le **Private DNS Zone**
3. Lier à votre VNet

### Option 3 : Changer de Région

Si le problème est spécifique à une région :

```bash
# Essayer une autre région
AZURE_SERVICE_REGION=francecentral
AZURE_SPEECH_ENDPOINT=https://francecentral.api.cognitive.microsoft.com
```

---

## 📞 Support

Si aucune solution ne fonctionne :

1. **Créer un ticket Azure Support**
2. **Fournir** :
   - Logs complets de la Web App
   - Configuration réseau (VNet, NSG, Firewall)
   - Résultat des tests de connectivité

---

**Date** : 2025-10-23  
**Statut** : ✅ Solution implémentée avec fallback et retry logic
