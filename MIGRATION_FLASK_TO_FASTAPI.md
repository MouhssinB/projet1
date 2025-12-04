# Migration Flask vers FastAPI - GMA Training Bot IHM

## 📋 Résumé

Ce document décrit la migration complète du projet **GMA Training Bot IHM** de Flask 3.0.0 vers FastAPI 0.115+.

**Version:** 2.0.0
**Date:** 2025-12-04
**Statut:** ✅ Migration complète

---

## 🎯 Objectifs de la Migration

1. **Modernisation** : Passage à un framework moderne et performant
2. **Scalabilité** : Support natif de l'asynchrone pour de meilleures performances
3. **Documentation automatique** : Swagger/OpenAPI intégré nativement
4. **Validation des données** : Pydantic pour une validation robuste
5. **Simplicité** : Code plus simple et maintenable

---

## 📊 Statistiques de Migration

- **40+ endpoints** migrés
- **13 templates Jinja2** conservés (compatibles)
- **11 modules core/** préservés (aucune modification nécessaire)
- **Architecture modulaire** : 6 routers organisés par domaine
- **Tests** : Suite de tests pytest créée

---

## 🏗️ Nouvelle Architecture

### Structure du Projet

```
projet1/
├── app/                           # Nouveau package FastAPI
│   ├── __init__.py
│   ├── config.py                  # Configuration centralisée (Pydantic Settings)
│   ├── exceptions.py              # Gestionnaires d'exceptions
│   ├── models/                    # Modèles Pydantic
│   │   ├── chat.py
│   │   ├── user.py
│   │   ├── profile.py
│   │   ├── synthesis.py
│   │   ├── rating.py
│   │   ├── habilitations.py
│   │   └── faq.py
│   ├── routers/                   # Routes organisées par domaine
│   │   ├── auth.py                # Authentification OAuth2
│   │   ├── chat.py                # Routes de chat
│   │   ├── faq.py                 # Routes FAQ
│   │   ├── admin.py               # Routes admin
│   │   ├── files.py               # Gestion des fichiers
│   │   └── history.py             # Historique et suivi
│   ├── dependencies/              # Dépendances FastAPI
│   │   ├── auth.py                # get_current_user, get_current_admin
│   │   └── session.py             # Gestion de session
│   └── middleware/                # Middlewares
│       ├── logging.py             # Logging des requêtes/réponses
│       └── session.py             # Configuration session
│
├── main_fastapi.py                # Point d'entrée FastAPI (remplace app.py)
├── auth/                          # Modules d'authentification (préservés)
├── core/                          # Logique métier (préservés)
├── templates/                     # Templates Jinja2 (préservés)
├── static/                        # Fichiers statiques (préservés)
├── data/                          # Données (préservées)
└── tests/                         # Tests pytest
    ├── conftest.py
    ├── test_auth.py
    ├── test_health.py
    ├── test_models.py
    └── test_security.py
```

---

## 🔄 Changements Majeurs

### 1. Point d'Entrée

**Avant (Flask):**
```python
# app.py
from flask import Flask
app = Flask(__name__)
```

**Après (FastAPI):**
```python
# main_fastapi.py
from fastapi import FastAPI
app = create_app()
```

### 2. Routes et Endpoints

**Avant (Flask):**
```python
@app.route("/chat", methods=["POST"])
@auth.login_required
def chat():
    data = request.json
    return jsonify(response)
```

**Après (FastAPI):**
```python
@router.post("/chat")
async def chat(
    request: Request,
    chat_message: ChatMessage,
    user: Dict[str, Any] = Depends(get_current_user)
):
    return {"response": bot_response}
```

### 3. Authentification

**Avant (Flask):**
```python
@auth.login_required
def protected_route():
    user = session["user"]
```

**Après (FastAPI - Dépendances):**
```python
async def protected_route(
    user: Dict[str, Any] = Depends(get_current_user)
):
    # user est automatiquement injecté
```

### 4. Validation des Données

**Avant (Flask):**
```python
data = request.json
message = data.get("message")
if not message:
    return jsonify({"error": "Missing message"}), 400
```

**Après (FastAPI - Pydantic):**
```python
class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)

async def chat(chat_message: ChatMessage):
    # Validation automatique par Pydantic
```

### 5. Middleware

**Avant (Flask):**
```python
@app.before_request
def before_request():
    # Logging

@app.after_request
def after_request(response):
    # Logging
    return response
```

**Après (FastAPI):**
```python
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Logging before
        response = await call_next(request)
        # Logging after
        return response
```

### 6. Gestion des Sessions

**Avant (Flask):**
```python
from flask_session import Session
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
```

**Après (FastAPI):**
```python
from starlette.middleware.sessions import SessionMiddleware
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    max_age=settings.session_max_age
)
```

---

## 📦 Dépendances

### Dépendances Supprimées

- `flask==3.0.0`
- `flask-cors>=5.0.1`
- `flask-session>=0.8.0`
- `gunicorn>=23.0.0`
- `pytest-flask>=1.3.0`

### Dépendances Ajoutées

- `fastapi>=0.115.0`
- `uvicorn[standard]>=0.32.0`
- `python-multipart>=0.0.17`
- `pydantic>=2.0.0`
- `pydantic-settings>=2.0.0`
- `pytest-asyncio>=0.24.0`
- `httpx>=0.27.0`

### Dépendances Conservées

- `authlib>=1.6.0` (compatible Starlette)
- Tous les packages Azure
- `openai>=1.76.0`
- Autres utilitaires

---

## 🔧 Configuration

### Variables d'Environnement

**Nouvelles variables:**
- `PORT` : Port de l'application (défaut: 8000)

**Variables modifiées:**
- ~~`FLASK_APP`~~ → Supprimée (pas nécessaire)
- ~~`FLASK_ENV`~~ → Supprimée (pas nécessaire)

**Variables conservées:**
- Toutes les variables Azure (AZURE_*)
- Toutes les variables OAuth2 (GAUTHIQ_*)
- `SECRET_KEY`, `LISTE_ADMINS`, etc.

---

## 🚀 Déploiement

### Développement

```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
uvicorn main_fastapi:app --reload --port 8000
```

### Production

```bash
# Docker
docker build -t gma-training-bot:2.0.0 .
docker run -p 8000:8000 gma-training-bot:2.0.0

# Ou directement avec uvicorn
uvicorn main_fastapi:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker

**Changements dans le Dockerfile:**
- Port exposé: `5000` → `8000`
- Commande de démarrage: `gunicorn` → `uvicorn`
- Variables d'environnement Flask supprimées

**Changements dans docker-entrypoint.sh:**
- Remplacement de Gunicorn par Uvicorn
- Support des workers Uvicorn (`UVICORN_WORKERS`)

---

## 📝 Documentation API

### Swagger UI

Accessible en développement sur : `http://localhost:8000/docs`

### ReDoc

Accessible en développement sur : `http://localhost:8000/redoc`

**Note:** Ces endpoints sont désactivés en production pour des raisons de sécurité.

---

## ✅ Fonctionnalités Conservées

Toutes les fonctionnalités de l'application Flask ont été préservées :

✅ Authentification OAuth2 (Gauthiq)
✅ Système de permissions (Habilitations)
✅ Chat avec Azure OpenAI
✅ Synthèse de conversations
✅ FAQ
✅ Gestion de profils utilisateur
✅ Historique de conversations
✅ Panel d'administration
✅ Upload/Download de fichiers
✅ Intégration Azure (OpenAI, Speech, Storage, Monitor)
✅ Templates Jinja2
✅ Fichiers statiques
✅ Gestion de sessions
✅ Logging Azure Monitor

---

## 🧪 Tests

### Exécuter les Tests

```bash
# Tous les tests
pytest

# Tests avec couverture
pytest --cov=app --cov-report=html

# Tests spécifiques
pytest tests/test_auth.py -v
```

### Tests Créés

- `test_health.py` : Tests des endpoints de santé
- `test_auth.py` : Tests d'authentification
- `test_models.py` : Tests des modèles Pydantic
- `test_security.py` : Tests des fonctions de sécurité

---

## 📈 Améliorations Futures

### Possibilités d'Amélioration

1. **Asynchrone complet**
   - Convertir les fonctions de `core/fonctions.py` en async
   - Utiliser `httpx` au lieu de `requests`
   - Client Azure OpenAI asynchrone

2. **Base de données**
   - Migration vers PostgreSQL avec SQLAlchemy async
   - Ou utilisation de MongoDB avec Motor

3. **Cache**
   - Redis pour les sessions (au lieu de cookies)
   - Cache des réponses fréquentes

4. **WebSockets**
   - Chat en temps réel
   - Notifications push

5. **Sécurité renforcée**
   - Rate limiting (slowapi)
   - CSRF protection avancée
   - JWT tokens au lieu de sessions

---

## ⚠️ Points d'Attention

### Différences Comportementales

1. **Sessions**
   - FastAPI utilise des sessions basées sur des cookies signés (itsdangerous)
   - Taille limitée à 4KB (contrainte cookies)
   - Pour des sessions plus volumineuses, envisager Redis

2. **Pickle dans les Sessions**
   - `ProfilManager` est sérialisé en pickle dans la session
   - Fonctionne mais augmente la taille de la session
   - Alternative recommandée : stocker uniquement l'ID et récupérer depuis DB

3. **Routes FAQ**
   - Préfixe `/faq` ajouté
   - `/faq_chat` devient `/faq/chat` (note: underscore remplacé)
   - `/faq_history` devient `/faq/history`
   - `/faq_reset` devient `/faq/reset`

4. **Admin Routes**
   - Préfixe `/admin` ajouté
   - `/admin_suivis` devient `/admin/suivis` (note: underscore remplacé)
   - Autres routes similaires

---

## 🔍 Vérifications Post-Migration

### Checklist de Vérification

- [x] Toutes les routes migrées
- [x] Authentification OAuth2 fonctionnelle
- [x] Gestion des sessions
- [x] Templates Jinja2 rendus correctement
- [x] Fichiers statiques accessibles
- [x] Intégration Azure OpenAI
- [x] Intégration Azure Monitor
- [x] Permissions et habilitations
- [x] Upload/Download de fichiers
- [x] Tests unitaires créés
- [x] Dockerfile mis à jour
- [x] Documentation API générée

### Tests Manuels Recommandés

1. **Authentification**
   - Login OAuth2
   - Callback et récupération des habilitations
   - Vérification des permissions
   - Logout

2. **Chat**
   - Envoi de messages
   - Réception de réponses
   - Historique de conversation
   - Changement de profil

3. **FAQ**
   - Questions/Réponses
   - Historique FAQ
   - Reset

4. **Admin**
   - Accès panel admin
   - Modification des habilitations
   - Upload de guides

---

## 📚 Ressources

### Documentation

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [Starlette Documentation](https://www.starlette.io/)

### Migration Guides

- [Migrating from Flask](https://fastapi.tiangolo.com/alternatives/#flask)
- [OAuth2 with FastAPI](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)

---

## 👥 Support

Pour toute question concernant cette migration, contacter l'équipe de développement.

---

## 📄 Licence

Voir le fichier LICENSE du projet.
