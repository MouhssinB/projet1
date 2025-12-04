# Solution pour Azure Speech avec VNet/Firewall

## 🔥 Problème identifié

Votre ressource Azure Speech a un **Virtual Network (VNet)** ou **Firewall** configuré, ce qui désactive l'API de génération de tokens (`/sts/v1.0/issueToken`).

**Erreur retournée :**
```json
{
  "error": {
    "code": "BadRequest",
    "message": "Virtual network/Firewall is configured, Token API is disabled."
  }
}
```

## 🎯 Solutions disponibles

### Solution 1 : Désactiver le VNet/Firewall (RECOMMANDÉ)

Si vous n'avez pas besoin de restrictions réseau strictes :

1. **Dans le portail Azure :**
   - Allez sur votre ressource Speech : `spch-india-simsan-d-we`
   - Menu "Networking" (Réseau)
   - Section "Firewalls and virtual networks"
   - Sélectionnez : **"All networks"** au lieu de "Selected networks"
   - Cliquez sur "Save"

2. **Attendez 2-3 minutes** que la configuration se propage

3. **Testez** avec le script de diagnostic :
   ```bash
   cd /home/gs8678/projet/simsan/infra/src
   set -a && source .env && set +a
   python3 scripts/test_speech_config.py
   ```

### Solution 2 : Ajouter Azure Web App au VNet autorisé

Si vous devez conserver le VNet/Firewall :

1. **Dans le portail Azure :**
   - Ressource Speech → "Networking"
   - Section "Firewalls and virtual networks"
   - **Ajoutez l'adresse IP de votre Azure Web App**
   - OU intégrez votre Web App au VNet autorisé

2. **Pour trouver l'IP de votre Web App :**
   - Allez sur votre Web App Azure
   - Menu "Properties"
   - Notez les "Outbound IP addresses"
   - Ajoutez TOUTES ces IPs dans Speech Networking

### Solution 3 : Utiliser la clé directement (NON RECOMMANDÉ - Sécurité)

⚠️ **Cette solution expose la clé côté client et n'est pas recommandée.**

Si vous devez absolument garder le VNet ET ne pouvez pas ajouter les IPs :

1. Modifiez le frontend pour utiliser `fromSubscription()` au lieu de `fromAuthorizationToken()`
2. La clé sera envoyée au navigateur (risque de sécurité)

## ✅ Solution recommandée : Désactiver le VNet

Pour votre environnement de développement, la **Solution 1** est la plus simple :

```bash
# Dans Azure Portal
Speech Resource → Networking → Firewalls and virtual networks
→ Selected "All networks" → Save
```

## 🔍 Vérification

Après modification, testez avec :

```bash
cd /home/gs8678/projet/simsan/infra/src
set -a && source .env && set +a
python3 scripts/test_speech_config.py
```

Vous devriez voir :
```
✅ SUCCÈS!
Token reçu (début): eyJhbGciOiJIUzI1NiIs...
```

## 📚 Documentation Azure

- [Azure Cognitive Services - Virtual Networks](https://learn.microsoft.com/en-us/azure/cognitive-services/cognitive-services-virtual-networks)
- [Speech Service - Network security](https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/speech-services-private-link)
