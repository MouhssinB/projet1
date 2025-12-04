# Exemple d'intégration de gauthiq_p.py dans app.py pour la PRODUCTION

## Configuration minimale requise

```python
# app.py - VERSION PRODUCTION

import os
from flask import Flask
from dotenv import load_dotenv
from flask_session import Session

# Import de la version PRODUCTION
from auth.gauthiq_p import GauthiqAuthProduction

# Chargement des variables d'environnement
load_dotenv('.env.production')

# Initialisation Flask
app = Flask(__name__)

# ============================================
# CONFIGURATION CRITIQUE (PRODUCTION)
# ============================================

# SECRET_KEY - OBLIGATOIRE et FORTE
app.secret_key = os.getenv('SECRET_KEY')
# Générer avec: python -c "import secrets; print(secrets.token_hex(32))"

# ============================================
# CONFIGURATION DES SESSIONS
# ============================================

app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_FILE_DIR"] = os.path.join(os.getcwd(), "flask_session")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)

# COOKIES SÉCURISÉS (PRODUCTION)
app.config["SESSION_COOKIE_NAME"] = "simsan_session"
app.config["SESSION_COOKIE_SAMESITE"] = "None"  # Pour OAuth cross-domain
app.config["SESSION_COOKIE_SECURE"] = True      # HTTPS obligatoire
app.config["SESSION_COOKIE_HTTPONLY"] = True    # Protection XSS
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_FILE_THRESHOLD"] = 500

# ============================================
# CONFIGURATION OAUTH2 GAUTHIQ
# ============================================

app.config['GAUTHIQ_CLIENT_ID'] = os.getenv('GAUTHIQ_CLIENT_ID')
app.config['GAUTHIQ_CLIENT_SECRET'] = os.getenv('GAUTHIQ_CLIENT_SECRET')
app.config['GAUTHIQ_DISCOVERY_URL'] = os.getenv('GAUTHIQ_DISCOVERY_URL')
app.config['GAUTHIQ_REDIRECT_URI'] = os.getenv('GAUTHIQ_REDIRECT_URI')
app.config['GAUTHIQ_SSL_VERIFY'] = True  # OBLIGATOIRE en production

# Configuration Habilitations
app.config['GAUTHIQ_HABILITATION'] = os.getenv('GAUTHIQ_HABILITATION')
app.config['GAUTHIQ_HABILITATION_FILTRE'] = os.getenv('GAUTHIQ_HABILITATION_FILTRE')

# ============================================
# INITIALISATION
# ============================================

# Initialiser la session Flask
os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
Session(app)

# Initialiser Gauthiq Auth PRODUCTION
try:
    auth = GauthiqAuthProduction(app)
    app.logger.info("✅ Gauthiq Auth Production initialisé avec succès")
except ValueError as e:
    app.logger.critical("❌ ERREUR CRITIQUE: %s", str(e))
    raise
except Exception as e:
    app.logger.critical("❌ ERREUR FATALE: %s", str(e))
    raise

# ============================================
# LISTE DES ADMINISTRATEURS
# ============================================

LISTE_ADMINS = os.getenv('LISTE_ADMINS', '').split(',')
app.logger.info("📋 Administrateurs configurés: %d", len(LISTE_ADMINS))

# ============================================
# ROUTES PROTÉGÉES
# ============================================

@app.route("/")
@auth.login_required
def index():
    """Page d'accueil - requiert authentification"""
    user_info = auth.get_user_info()
    habilitations = auth.get_habilitations()
    
    return render_template(
        "index.html",
        user=user_info,
        habilitations=habilitations
    )

@app.route("/admin")
@auth.admin_required(admin_list=LISTE_ADMINS)
def admin_page():
    """Page admin - requiert authentification + droits admin"""
    user_info = auth.get_user_info()
    session_info = auth.get_session_info()
    
    return render_template(
        "admin.html",
        user=user_info,
        session_info=session_info
    )

@app.route("/api/profile")
@auth.login_required
def api_profile():
    """API - Informations utilisateur"""
    user_info = auth.get_user_info()
    habilitations = auth.get_habilitations()
    
    return jsonify({
        "user": {
            "username": user_info.get('preferred_username'),
            "email": user_info.get('email'),
            "name": user_info.get('name')
        },
        "habilitations": habilitations,
        "session": auth.get_session_info()
    })

# ============================================
# HEALTH CHECK (NON PROTÉGÉ)
# ============================================

@app.route("/_stcore/health")
def health_check():
    """Health check pour Azure"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "auth": "enabled"
    })

# ============================================
# GESTION D'ERREURS
# ============================================

@app.errorhandler(403)
def forbidden(error):
    """Accès refusé"""
    return render_template('error.html', 
                         error_code=403,
                         error_message="Accès refusé"), 403

@app.errorhandler(500)
def internal_error(error):
    """Erreur serveur"""
    app.logger.error("Erreur 500: %s", str(error))
    return render_template('error.html',
                         error_code=500,
                         error_message="Erreur interne"), 500

# ============================================
# LOGGING DE SÉCURITÉ
# ============================================

@app.before_request
def log_security_event():
    """Log des requêtes sensibles"""
    # Log les accès admin
    if request.path.startswith('/admin'):
        app.logger.info(
            "🔒 Accès admin - Path: %s, User: %s, IP: %s",
            request.path,
            session.get('user', {}).get('preferred_username', 'Anonymous'),
            request.remote_addr
        )

# ============================================
# DÉMARRAGE
# ============================================

if __name__ == "__main__":
    # En production, utiliser gunicorn
    # gunicorn --bind 0.0.0.0:8000 --workers 4 app:app
    
    # Mode debug désactivé en production
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 8000)),
        debug=False
    )
```

## Variables d'environnement requises

Créer un fichier `.env.production` :

```bash
# SECRET_KEY (64+ caractères)
SECRET_KEY=VOTRE_SECRET_KEY_64_CARACTERES_MINIMUM_GENERE_ALEATOIREMENT

# GAUTHIQ OAuth
GAUTHIQ_CLIENT_ID=simsan-production
GAUTHIQ_CLIENT_SECRET=VOTRE_SECRET_PRODUCTION
GAUTHIQ_DISCOVERY_URL=https://authentification-interne.caas-prod.intra.groupama.fr/auth/realms/interne/.well-known/openid-configuration
GAUTHIQ_REDIRECT_URI=https://simsan.groupama.fr/oauth2callback
GAUTHIQ_SSL_VERIFY=True

# Habilitations
GAUTHIQ_HABILITATION=https://svc-habilitation-gauthiq.caas-prod.intra.groupama.fr
GAUTHIQ_HABILITATION_FILTRE=GR_SIMSAN_PROD,LAVANDE:GR_SIMSAN_ADMIN

# Admins
LISTE_ADMINS=admin1,admin2,admin@groupama.com

# Cookies
SESSION_COOKIE_SAMESITE=None
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_PERMANENT=True
SESSION_LIFETIME_HOURS=8
```

## Commandes de déploiement

### Avec Gunicorn (recommandé)

```bash
# Installation
pip install gunicorn

# Démarrage
gunicorn --bind 0.0.0.0:8000 \
         --workers 4 \
         --timeout 120 \
         --access-logfile - \
         --error-logfile - \
         --log-level info \
         app:app
```

### Azure App Service

```bash
# Dans Azure Portal → Configuration → General settings
# Startup Command:
gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 120 app:app
```

## Vérifications avant déploiement

```bash
# 1. Vérifier les variables d'environnement
python -c "from dotenv import load_dotenv; import os; load_dotenv('.env.production'); print('SECRET_KEY:', 'OK' if os.getenv('SECRET_KEY') and len(os.getenv('SECRET_KEY')) >= 64 else 'ERREUR')"

# 2. Tester l'initialisation
python -c "from app import app; print('App initialisée:', app.name)"

# 3. Vérifier SSL
curl -I https://simsan.groupama.fr

# 4. Tester le health check
curl https://simsan.groupama.fr/_stcore/health
```

## Monitoring

```python
# Ajouter Application Insights
from applicationinsights.flask.ext import AppInsights

app.config['APPINSIGHTS_INSTRUMENTATIONKEY'] = os.getenv('APPINSIGHTS_KEY')
appinsights = AppInsights(app)

@app.after_request
def after_request(response):
    appinsights.flush()
    return response
```

## Sécurité additionnelle

```python
# Headers de sécurité
from flask_talisman import Talisman

# Force HTTPS
Talisman(app, 
         force_https=True,
         strict_transport_security=True,
         strict_transport_security_max_age=31536000,
         content_security_policy={
             'default-src': "'self'",
             'script-src': ["'self'", "'unsafe-inline'"],
             'style-src': ["'self'", "'unsafe-inline'"]
         })
```

## Rate Limiting

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route("/login")
@limiter.limit("10 per minute")
def login():
    return auth.login()
```
