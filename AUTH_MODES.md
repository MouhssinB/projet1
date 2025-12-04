# Modes d'Authentification - GMA Training Bot IHM

## Vue d'ensemble

L'application supporte deux modes d'authentification OAuth2 avec Gauthiq :

1. **Mode Local** (développement uniquement)
2. **Mode Production** (déploiement sécurisé)

## Configuration

Le mode d'authentification est contrôlé par la variable d'environnement `AUTH_MODE` dans votre fichier `.env`.

### Mode Local

**À utiliser UNIQUEMENT en développement local**

```bash
AUTH_MODE=local
```

**Caractéristiques :**
- ✅ Désactive la vérification SSL pour Gauthiq
- ✅ Permet de tester avec des certificats auto-signés
- ✅ Simplifie le développement local
- ❌ **NE JAMAIS utiliser en production**
- ❌ Non sécurisé pour un environnement réel

**Cas d'usage :**
- Développement sur poste local
- Tests avec un serveur Gauthiq de développement
- Environnement de test sans certificats SSL valides

### Mode Production

**Mode par défaut - À utiliser en production et staging**

```bash
AUTH_MODE=production
```

**Caractéristiques :**
- ✅ Active la vérification SSL complète
- ✅ Conforme aux standards de sécurité
- ✅ Protection contre les attaques man-in-the-middle
- ✅ Certificats SSL validés
- ✅ Recommandé pour tous les déploiements

**Cas d'usage :**
- Production
- Staging
- Pré-production
- Tout environnement accessible publiquement

## Configuration détaillée

### 1. Variables d'environnement requises

```bash
# Mode d'authentification
AUTH_MODE=production  # ou "local"

# Configuration OAuth2 Gauthiq
GAUTHIQ_CLIENT_ID=your-client-id
GAUTHIQ_CLIENT_SECRET=your-client-secret
GAUTHIQ_DISCOVERY_URL=https://your-gauthiq-server/.well-known/openid-configuration
GAUTHIQ_REDIRECT_URI=https://your-app-domain.com/oauth2callback
GAUTHIQ_HABILITATION=https://your-gauthiq-server
GAUTHIQ_HABILITATION_FILTRE=your-filter-value

# SSL pour Gauthiq (utilisé en mode production uniquement)
GAUTHIQ_SSL_VERIFY=True
```

### 2. Comportement selon le mode

| Configuration | Mode Local | Mode Production |
|---------------|------------|-----------------|
| SSL Verify | **False** (désactivé) | **True** (activé) |
| Certificats auto-signés | ✅ Acceptés | ❌ Rejetés |
| Validation SSL | ❌ Désactivée | ✅ Activée |
| Sécurité | ⚠️ Faible | ✅ Forte |
| Usage recommandé | Dev local uniquement | Production/Staging |

## Exemples de configuration

### Développement local

Fichier `.env` pour le développement :

```bash
AUTH_MODE=local
GAUTHIQ_CLIENT_ID=dev-client-id
GAUTHIQ_CLIENT_SECRET=dev-client-secret
GAUTHIQ_DISCOVERY_URL=http://localhost:8080/.well-known/openid-configuration
GAUTHIQ_REDIRECT_URI=http://localhost:5000/oauth2callback
GAUTHIQ_SSL_VERIFY=False  # Ignoré en mode local
```

### Production

Fichier `.env` pour la production :

```bash
AUTH_MODE=production
GAUTHIQ_CLIENT_ID=prod-client-id
GAUTHIQ_CLIENT_SECRET=prod-client-secret
GAUTHIQ_DISCOVERY_URL=https://gauthiq.example.com/.well-known/openid-configuration
GAUTHIQ_REDIRECT_URI=https://app.example.com/oauth2callback
GAUTHIQ_SSL_VERIFY=True  # SSL activé en mode production
```

## Vérification du mode actuel

Vous pouvez vérifier le mode d'authentification utilisé dans les logs au démarrage de l'application :

```
✓ Configuration OAuth validée
✓ Mode d'authentification : production
✓ SSL Verify : True
```

Ou en mode local :

```
⚠️ Mode d'authentification : local
⚠️ SSL Verify : False (DÉVELOPPEMENT UNIQUEMENT)
```

## Sécurité

### ⚠️ Avertissements importants

1. **Ne JAMAIS utiliser le mode local en production**
   - Vulnérable aux attaques man-in-the-middle
   - Non conforme aux standards de sécurité
   - Données d'authentification exposées

2. **Protéger les secrets**
   - Ne jamais committer le fichier `.env`
   - Utiliser des gestionnaires de secrets en production
   - Rotation régulière des secrets

3. **HTTPS obligatoire en production**
   - Le mode production requiert HTTPS
   - Les certificats doivent être valides
   - Mise à jour régulière des certificats

## Dépannage

### Erreur : "SSL: CERTIFICATE_VERIFY_FAILED"

**En mode production :**
- Vérifiez que les certificats SSL du serveur Gauthiq sont valides
- Vérifiez la date d'expiration des certificats
- Vérifiez que l'URL correspond au certificat

**En mode local (développement) :**
- Passez en mode local : `AUTH_MODE=local`
- Cette erreur est normale avec des certificats auto-signés

### Changement de mode ne prend pas effet

1. Arrêter l'application complètement
2. Vérifier que `.env` contient la bonne valeur `AUTH_MODE`
3. Redémarrer l'application
4. Vérifier les logs au démarrage

### Mode local en production (erreur)

Si vous voyez ce warning en production :
```
⚠️⚠️⚠️ ATTENTION : Mode LOCAL détecté en production !
```

Actions immédiates :
1. Arrêter l'application
2. Changer `AUTH_MODE=production` dans `.env`
3. Redémarrer l'application
4. Vérifier les logs

## Migration

### De l'ancien système Flask vers le nouveau système FastAPI

L'ancien système Flask utilisait directement `GAUTHIQ_SSL_VERIFY`.
Le nouveau système FastAPI utilise `AUTH_MODE` pour plus de clarté.

**Migration :**

Ancien (Flask) :
```bash
GAUTHIQ_SSL_VERIFY=False  # Pour désactiver SSL
```

Nouveau (FastAPI) :
```bash
AUTH_MODE=local  # Pour désactiver SSL en dev
# ou
AUTH_MODE=production  # Pour activer SSL en prod
```

## Support

Pour toute question sur les modes d'authentification :
- Vérifier ce document
- Consulter `.env.example`
- Vérifier les logs de l'application
