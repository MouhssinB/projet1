# 🚀 Guide de Déploiement - Sécurisation Speech Tokens

## ✅ Prérequis

- [x] Module `requests` installé (déjà dans requirements.txt)
- [x] Variables d'environnement configurées :
  - `AZURE_SPEECH_KEY`
  - `AZURE_SERVICE_REGION`
- [x] Authentification Gauthiq fonctionnelle

---

## 📝 Checklist Pré-Déploiement

### 1. Tests Automatisés

```bash
# Vérifier que tous les tests passent
cd /home/gs8678/projet/simsan/infra/src
python3 tests/test_speech_security.py
```

**Résultat attendu :**
```
✅ ✅ ✅ SUCCÈS - Tous les tests de sécurité sont passés ! ✅ ✅ ✅
```

### 2. Vérification Manuelle

#### a) Inspection du code source HTML
1. Lancer l'application en local
2. Ouvrir DevTools (F12)
3. Aller dans "Sources" > Rechercher "subscriptionKey"
4. ✅ **Attendu** : Aucun résultat trouvé

#### b) Inspection du réseau
1. Ouvrir DevTools > Network
2. Activer le mode vocal
3. Filtrer par "speech"
4. ✅ **Attendu** : Requêtes avec `Authorization: Bearer <token>` uniquement

#### c) Test Fonctionnel
1. Charger l'application
2. Passer en mode vocal
3. Appuyer sur ESPACE et parler
4. ✅ **Attendu** : Reconnaissance vocale fonctionne normalement

### 3. Vérification des Variables d'Environnement

```bash
# Sur le serveur de production
echo $AZURE_SPEECH_KEY
echo $AZURE_SERVICE_REGION
```

⚠️ **Important** : Ne pas exposer ces valeurs dans les logs !

---

## 🔄 Procédure de Déploiement

### Étape 1 : Commit des changements

```bash
cd /home/gs8678/projet/simsan

# Vérifier les fichiers modifiés
git status

# Ajouter les modifications
git add infra/src/app.py
git add infra/src/templates/index.html
git add infra/src/static/js/app.js
git add infra/src/SECURITE_SPEECH_TOKEN.md
git add infra/src/RESUME_SECURITE_SPEECH.md
git add infra/src/tests/test_speech_security.py
git add infra/src/DEPLOIEMENT_SECURITE_SPEECH.md

# Commit avec message descriptif
git commit -m "feat: sécurisation tokens Azure Speech

- Suppression des clés API exposées côté client
- Implémentation de tokens temporaires (10 min)
- Route /get_speech_token avec authentification
- Tests de sécurité automatisés
- Documentation complète

Validation équipe sécurité: OK"
```

### Étape 2 : Push vers le dépôt

```bash
# Push vers la branche de développement
git push origin develop

# Ou directement en production (selon votre workflow)
git push origin main
```

### Étape 3 : Déploiement (selon votre CI/CD)

#### Option A : Déploiement manuel

```bash
# Connexion au serveur
ssh user@production-server

# Pull des derniers changements
cd /path/to/simsan
git pull origin main

# Redémarrage de l'application
sudo systemctl restart simsan-app
# ou
sudo supervisorctl restart simsan
# ou
docker-compose restart
```

#### Option B : Pipeline CI/CD

Si vous utilisez GitLab CI/CD, Azure DevOps, ou GitHub Actions :
- Le déploiement se fera automatiquement après le push
- Surveiller les logs du pipeline
- Vérifier que tous les tests passent

---

## 🧪 Tests Post-Déploiement

### 1. Healthcheck API

```bash
# Vérifier que la nouvelle route existe
curl -i https://votre-domaine.com/get_speech_token
```

**Résultat attendu :**
```
HTTP/1.1 401 Unauthorized  (car non authentifié)
ou
HTTP/1.1 302 Found  (redirection vers login)
```

### 2. Test Authentifié

```bash
# Avec un cookie de session valide
curl -H "Cookie: session_simsan=..." \
     https://votre-domaine.com/get_speech_token
```

**Résultat attendu :**
```json
{
  "token": "eyJ...",
  "region": "francecentral",
  "success": true
}
```

### 3. Test Fonctionnel Complet

1. Connexion avec un utilisateur valide
2. Activation du mode vocal
3. Test de reconnaissance vocale
4. Test de synthèse vocale (TTS)
5. Vérification dans les logs serveur :
   ```
   ✅ Token Speech obtenu (valide 10 minutes)
   ```

---

## 📊 Monitoring Post-Déploiement

### Métriques à Surveiller

#### a) Logs Applicatifs
```bash
# Rechercher les erreurs liées à Speech
tail -f /var/log/simsan/app.log | grep -i "speech\|token"
```

**Patterns à surveiller :**
- ✅ `Token Speech obtenu`
- ✅ `Renouvellement du token Speech`
- ❌ `Erreur lors de l'obtention du token`
- ❌ `Erreur d'authentification Speech`

#### b) Azure Portal
- Ouvrir Azure Portal > Cognitive Services > Votre ressource Speech
- Aller dans "Monitoring" > "Metrics"
- Vérifier que les appels continuent normalement

#### c) Taux d'Erreur
```bash
# Analyser les logs pour détecter des erreurs
grep "500 Internal Server Error" /var/log/nginx/access.log | wc -l
```

---

## 🔧 Rollback en Cas de Problème

### Si le déploiement pose problème :

```bash
# Revenir à la version précédente
git revert HEAD
git push origin main

# Ou checkout du commit précédent
git checkout <commit-hash-précédent>
git push -f origin main

# Redémarrer l'application
sudo systemctl restart simsan-app
```

### Rollback Rapide (sans git)

Si vous devez restaurer l'ancienne version immédiatement :

1. **Restaurer les clés dans le template** (temporaire uniquement !) :
   ```python
   # Dans app.py
   return render_template(
       "index.html",
       speech_key=speech_key,  # Restaurer temporairement
       service_region=service_region
   )
   ```

2. **Restaurer le JS** :
   ```javascript
   // Dans app.js
   const speechConfig = SpeechSDK.SpeechConfig.fromSubscription(
       subscriptionKey,
       serviceRegion
   );
   ```

3. Redémarrer l'application

⚠️ **Note** : Ce rollback n'est QUE temporaire. Il faut investiguer et corriger le problème.

---

## 📞 Support et Escalade

### En cas de problème :

#### Niveau 1 : Logs et Diagnostics
```bash
# Vérifier les logs applicatifs
tail -f /var/log/simsan/app.log

# Vérifier les logs système
sudo journalctl -u simsan-app -f

# Vérifier les processus
ps aux | grep simsan
```

#### Niveau 2 : Tests Manuels
```bash
# Tester la route directement
python3 -c "
import requests
response = requests.post(
    'https://francecentral.api.cognitive.microsoft.com/sts/v1.0/issueToken',
    headers={'Ocp-Apim-Subscription-Key': 'VOTRE_CLE'}
)
print(response.status_code)
print(response.text)
"
```

#### Niveau 3 : Escalade
- **Équipe Développement** : Support technique
- **Équipe Infrastructure** : Problèmes serveur/réseau
- **Microsoft Support** : Problèmes Azure Speech Service

---

## ✅ Critères de Succès

Le déploiement est considéré comme réussi si :

- ✅ Tests automatisés passent (test_speech_security.py)
- ✅ Aucune clé API visible côté client
- ✅ Reconnaissance vocale fonctionne normalement
- ✅ Synthèse vocale fonctionne normalement
- ✅ Pas d'augmentation du taux d'erreur
- ✅ Logs confirment l'utilisation des tokens
- ✅ Validation équipe sécurité obtenue

---

## 📅 Timeline Recommandée

1. **J-1** : Tests en environnement de développement
2. **J0 - 10h** : Déploiement en production
3. **J0 - 10h-12h** : Monitoring intensif
4. **J0 - 14h** : Revue post-déploiement
5. **J+1** : Bilan 24h
6. **J+7** : Validation finale

---

## 📝 Documentation Connexe

- `SECURITE_SPEECH_TOKEN.md` : Documentation technique complète
- `RESUME_SECURITE_SPEECH.md` : Résumé exécutif
- `tests/test_speech_security.py` : Tests automatisés

---

**Bonne chance pour le déploiement ! 🚀**

*En cas de question, n'hésitez pas à consulter l'équipe de développement.*
