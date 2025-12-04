# Guide de Migration vers la Production

## 📋 Vue d'ensemble

Ce document décrit les étapes pour migrer votre application de développement vers la production avec `gauthiq_p.py`.

---

## 🔒 Différences Développement vs Production

| Aspect | Développement (`gauthiq.py`) | Production (`gauthiq_p.py`) |
|--------|------------------------------|----------------------------|
| **SSL/TLS** | Peut être désactivé | **OBLIGATOIRE** |
| **Cookies** | `SameSite=Lax, Secure=False` | `SameSite=None, Secure=True` |
| **Protocole** | HTTP autorisé | **HTTPS uniquement** |
| **SECRET_KEY** | Validation basique | Validation stricte (32+ chars) |
| **Nonce** | Validation simple | Validation + expiration (5 min) |
| **Session** | Expiration simple | Expiration + monitoring |
| **Logging** | Basique | Sécurité renforcée |
| **Validation URL** | Permissive | Protection open redirect |
| **Admin** | Décorateur simple | Décorateur avec audit |

---

## 🚀 Étapes de Migration

### 1. Préparation de l'environnement

#### a) Générer une nouvelle SECRET_KEY

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copiez la clé générée (64 caractères) dans `.env.production`.

#### b) Configurer le fichier `.env.production`

```bash
# Copier le template
cp .env.production .env.production.local

# Éditer avec vos valeurs réelles
nano .env.production.local
```

**Valeurs OBLIGATOIRES à changer :**

- ✅ `SECRET_KEY` (64+ caractères)
- ✅ `GAUTHIQ_CLIENT_ID` (votre client ID production)
- ✅ `GAUTHIQ_CLIENT_SECRET` (votre secret production)
- ✅ `GAUTHIQ_REDIRECT_URI` (HTTPS uniquement)
- ✅ `GAUTHIQ_HABILITATION_FILTRE` (vos filtres production)
- ✅ `LISTE_ADMINS` (liste des admins)
- ✅ Toutes les clés Azure (OpenAI, Speech, Storage)

#### c) Vérifier la configuration SSL/TLS

```bash
# Test de connectivité SSL
curl -v https://authentification-interne.caas-prod.intra.groupama.fr

# Test de l'API habilitations
curl -v https://svc-habilitation-gauthiq.caas-prod.intra.groupama.fr
```

---

### 2. Modification de `app.py`

#### a) Importer la version production

```python
# Remplacer cette ligne
from auth.gauthiq import GauthiqAuth

# Par celle-ci
from auth.gauthiq_p import GauthiqAuthProduction as GauthiqAuth
```

#### b) Configurer les cookies pour HTTPS

Dans `app.py`, vérifiez la configuration :

```python
# Configuration des cookies PRODUCTION
app.config["SESSION_COOKIE_SAMESITE"] = os.getenv('SESSION_COOKIE_SAMESITE', 'None')
app.config["SESSION_COOKIE_SECURE"] = get_env_bool('SESSION_COOKIE_SECURE', 'True')  # True en prod
app.config["SESSION_COOKIE_HTTPONLY"] = get_env_bool('SESSION_COOKIE_HTTPONLY', 'True')
```

#### c) Activer SSL pour Gauthiq

```python
# Dans app.py
app.config['GAUTHIQ_SSL_VERIFY'] = os.getenv('GAUTHIQ_SSL_VERIFY', 'True').lower() in ('true', '1', 't')
```

---

### 3. Configuration Azure App Service

#### a) Activer HTTPS uniquement

Dans le portail Azure :

1. **App Service** → **Configuration** → **General settings**
2. **HTTPS Only** : `On`
3. **Minimum TLS Version** : `1.2`

#### b) Configurer les App Settings

```bash
# Via Azure CLI
az webapp config appsettings set \
  --resource-group VOTRE_RG \
  --name VOTRE_APP \
  --settings \
    SECRET_KEY="VOTRE_SECRET_KEY_64_CHARS" \
    GAUTHIQ_CLIENT_ID="simsan-production" \
    GAUTHIQ_CLIENT_SECRET="VOTRE_SECRET" \
    GAUTHIQ_REDIRECT_URI="https://votre-app.azurewebsites.net/oauth2callback" \
    GAUTHIQ_SSL_VERIFY="True" \
    SESSION_COOKIE_SECURE="True" \
    SESSION_COOKIE_SAMESITE="None"
```

#### c) Configurer le Custom Domain (recommandé)

```bash
# Ajouter un domaine personnalisé
az webapp config hostname add \
  --resource-group VOTRE_RG \
  --webapp-name VOTRE_APP \
  --hostname simsan.groupama.fr

# Activer SSL
az webapp config ssl bind \
  --resource-group VOTRE_RG \
  --name VOTRE_APP \
  --certificate-thumbprint VOTRE_CERT_THUMBPRINT \
  --ssl-type SNI
```

---

### 4. Configuration Gauthiq (côté serveur OAuth)

#### a) Enregistrer l'URL de callback

Dans Gauthiq, enregistrez :

```
https://simsan.groupama.fr/oauth2callback
```

**⚠️ ATTENTION** : L'URL doit correspondre EXACTEMENT à `GAUTHIQ_REDIRECT_URI`.

#### b) Configurer les habilitations

Vérifiez que les filtres sont configurés :

```
GAUTHIQ_HABILITATION_FILTRE=GR_SIMSAN_PROD,LAVANDE:GR_SIMSAN_ADMIN
```

---

### 5. Tests avant déploiement

#### a) Tests locaux avec HTTPS (optionnel)

```bash
# Générer un certificat self-signed
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout key.pem -out cert.pem -days 365

# Lancer l'app avec SSL
gunicorn --certfile=cert.pem --keyfile=key.pem \
  --bind 0.0.0.0:5443 app:app
```

#### b) Tests unitaires

```bash
# Tests de sécurité
pytest tests/test_security_production.py -v
```

---

### 6. Déploiement

#### a) Via Azure CLI

```bash
# Déployer depuis Git
az webapp deployment source config \
  --resource-group VOTRE_RG \
  --name VOTRE_APP \
  --repo-url https://votre-repo.git \
  --branch production \
  --manual-integration

# Ou via ZIP
zip -r app.zip . -x "*.git*" -x "*__pycache__*" -x "*.env*"
az webapp deployment source config-zip \
  --resource-group VOTRE_RG \
  --name VOTRE_APP \
  --src app.zip
```

#### b) Vérifier le déploiement

```bash
# Logs en temps réel
az webapp log tail \
  --resource-group VOTRE_RG \
  --name VOTRE_APP

# Health check
curl -f https://simsan.groupama.fr/_stcore/health
```

---

### 7. Tests post-déploiement

#### a) Test du flux OAuth complet

1. ✅ Accéder à `https://simsan.groupama.fr`
2. ✅ Cliquer sur "Login"
3. ✅ S'authentifier sur Gauthiq
4. ✅ Vérifier la redirection vers l'app
5. ✅ Vérifier que les habilitations sont récupérées

#### b) Vérifier les logs

```bash
# Logs d'application
az webapp log download \
  --resource-group VOTRE_RG \
  --name VOTRE_APP \
  --log-file logs.zip

# Extraire et analyser
unzip logs.zip
grep "AUTHENTIFICATION RÉUSSIE" application.log
```

#### c) Tests de sécurité

```bash
# Test HTTPS obligatoire
curl -I http://simsan.groupama.fr
# Doit rediriger vers HTTPS

# Test headers de sécurité
curl -I https://simsan.groupama.fr | grep -E "Strict-Transport|X-Frame|X-Content"

# Test cookies sécurisés
curl -I -c cookies.txt https://simsan.groupama.fr
cat cookies.txt | grep "Secure.*HttpOnly"
```

---

### 8. Monitoring et alertes

#### a) Configurer Application Insights

```python
# Dans app.py
from applicationinsights.flask.ext import AppInsights

app.config['APPINSIGHTS_INSTRUMENTATIONKEY'] = os.getenv('APPINSIGHTS_KEY')
appinsights = AppInsights(app)
```

#### b) Métriques à surveiller

- ✅ Taux d'échec d'authentification
- ✅ Temps de réponse API habilitations
- ✅ Erreurs SSL/TLS
- ✅ Tentatives d'accès admin non autorisées
- ✅ Sessions expirées

#### c) Alertes recommandées

```bash
# Alerte sur échecs d'authentification
az monitor metrics alert create \
  --name auth-failures \
  --resource-group VOTRE_RG \
  --scopes /subscriptions/VOTRE_SUB/resourceGroups/VOTRE_RG/providers/Microsoft.Web/sites/VOTRE_APP \
  --condition "count requests where resultCode >= 400 > 10" \
  --window-size 5m \
  --evaluation-frequency 1m
```

---

## 🔐 Checklist de sécurité finale

Avant la mise en production, vérifiez :

- [ ] SECRET_KEY >= 64 caractères aléatoires
- [ ] HTTPS activé et obligatoire
- [ ] Certificat SSL valide (pas self-signed)
- [ ] `SESSION_COOKIE_SECURE=True`
- [ ] `SESSION_COOKIE_SAMESITE=None`
- [ ] `GAUTHIQ_SSL_VERIFY=True`
- [ ] URL callback HTTPS enregistrée dans Gauthiq
- [ ] Filtres habilitations configurés
- [ ] Liste admin à jour
- [ ] Logs de sécurité activés
- [ ] Application Insights configuré
- [ ] Backup et DR testés
- [ ] Tests de charge effectués
- [ ] Plan de rollback préparé

---

## 🆘 Dépannage

### Problème : "SSL Certificate verify failed"

**Solution :**
```python
# Vérifier la configuration
import ssl
import urllib.request

context = ssl.create_default_context()
context.check_hostname = True
context.verify_mode = ssl.CERT_REQUIRED
```

### Problème : "Session not persistent"

**Solution :**
```bash
# Vérifier les cookies
curl -v -c - https://simsan.groupama.fr/login

# Doit afficher:
# Set-Cookie: simsan_session=...; Secure; HttpOnly; SameSite=None
```

### Problème : "CSRF token missing"

**Solution :**
1. Vérifier que `SESSION_COOKIE_SAMESITE=None`
2. Vérifier que `SESSION_COOKIE_SECURE=True`
3. Vérifier que l'URL callback est en HTTPS

### Problème : "Habilitations vides"

**Solution :**
```bash
# Tester manuellement l'API
curl -H "Authorization: Bearer VOTRE_TOKEN" \
  "https://svc-habilitation-gauthiq.caas-prod.intra.groupama.fr/api/habilitations?filtre=VOS_FILTRES"
```

---

## 📞 Support

En cas de problème :

1. **Logs** : Consulter `log/application.log`
2. **Azure** : Vérifier Application Insights
3. **Gauthiq** : Contacter l'équipe Gauthiq
4. **Sécurité** : Contacter l'équipe SecOps

---

## 📚 Références

- [Documentation Gauthiq](https://wiki.groupama.fr/gauthiq)
- [OAuth 2.0 Best Practices](https://oauth.net/2/)
- [Flask Security](https://flask.palletsprojects.com/en/latest/security/)
- [Azure App Service Security](https://docs.microsoft.com/azure/app-service/overview-security)
