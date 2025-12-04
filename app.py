import os
import re
import json
import io
import urllib.parse
import requests
from datetime import datetime, timedelta
from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    session,
    send_from_directory,
    Response,
    url_for,
    send_file,
)
from flask_session import Session
from openai import AzureOpenAI
from azure.monitor.opentelemetry import configure_azure_monitor
from core.synthetiser import synthese_2
from core.fonctions import (
    get_next_bot_message,
    generer_rapport_html_synthese,
    get_user_folder_path,
    charger_documents_reference,
    log_to_journal,
    init_session_lists,
    init_session_profile,
    restore_profil_manager_from_session,
    save_profil_manager_to_session,
    save_user_rating_to_file,
    calcule_statistiques_conv,
    generate_expert_response,
)

from core.fonctions_fileshare import (
    save_file_to_azure,
    get_file_from_azure,
    list_files_from_azure,
    get_user_folder_path_fileshare as get_user_folder_path,
    init_fileshare_structure,
    get_guide_path,
    upload_guide,
    delete_guide,
)
from core.profil_manager import ProfilManager
from core.async_logger import get_async_logger, shutdown_async_logger
from auth.gauthiq import GauthiqAuth  # Import de la classe d'authentification
import logging
import atexit
from pathlib import Path
from core.security import sanitize_user_input, validate_message_format

# Initialisation de l'application Flask
app = Flask(__name__)
# load_dotenv('.env', override=True)


def set_log_record_factory_custom_attributes(**kwargs) -> None:
    """
    Adds custom attributes to all log records generated.

    :param kwargs: Key-value pairs where the key is the attribute name and the value is the attribute value.
    :return: None
    """
    factory = logging.getLogRecordFactory()

    def new_factory(*args, **kw):
        record = factory(*args, **kw)
        for k, v in kwargs.items():
            record.__setattr__(k, v)
        return record

    logging.setLogRecordFactory(factory=new_factory)


set_log_record_factory_custom_attributes(code_sa="simsan")  # A renseigner

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

configure_azure_monitor(
    connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
    logger_name="root",  # Recommandé : nom de votre application
    logging_formatter=formatter,
    instrumentation_options={"azure_sdk": {"enabled": False}},
)

# Initialiser la structure FileShare au démarrage
try:
    init_fileshare_structure()
    app.logger.info("Structure FileShare initialisée avec succès")
except Exception as e:
    app.logger.error(f"Erreur initialisation FileShare: {str(e)}")


# Configuration de base
secret_key = os.getenv("SECRET_KEY")
if not secret_key:
    raise RuntimeError(
        "SECRET_KEY environment variable must be set for security reasons."
    )
app.config["SECRET_KEY"] = secret_key
app.config["JSON_AS_ASCII"] = (
    False  # Empêche l'encodage des caractères non-ASCII (apostrophes, etc.)
)
profil_manager = ProfilManager()
documents_reference = charger_documents_reference()


# Configuration des sessions côté serveur
def get_env_bool(key, default="False"):
    return os.getenv(key, default).lower() in ("true", "1", "t", "yes")


# ============================================
# Configuration des sessions FILESHARE
# ============================================
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = get_env_bool("SESSION_PERMANENT", "True")
# os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
# Déterminer le répertoire de session
fileshare_mount = os.getenv("AZURE_FILESHARE_MOUNT_POINT", "/mnt/storage")
if os.path.exists(fileshare_mount) and os.access(fileshare_mount, os.W_OK):
    # Utiliser le FileShare monté si disponible et accessible
    session_base_dir = os.path.join(fileshare_mount, "sessions")
    print(f"📁 Utilisation du FileShare pour les sessions: {session_base_dir}")
else:
    # Fallback sur le système de fichiers local
    session_base_dir = os.path.join(os.getcwd(), "flask_session")
    print(f"📁 Utilisation du filesystem local pour les sessions: {session_base_dir}")

# Créer le répertoire de sessions s'il n'existe pas
os.makedirs(session_base_dir, exist_ok=True)


# ============================================
# PURGE DES SESSIONS AU DÉMARRAGE
# ============================================
def purge_session_directory(session_dir):
    """
    Purge complètement le répertoire de sessions au démarrage
    Supprime tous les fichiers de session existants
    """
    try:
        if not os.path.exists(session_dir):
            print(f"⚠️  Répertoire de sessions introuvable: {session_dir}")
            return

        deleted_count = 0
        error_count = 0
        total_size = 0

        print(f"🧹 Purge du répertoire de sessions: {session_dir}")

        for filename in os.listdir(session_dir):
            # Ignorer les fichiers cachés (., .., .gitkeep, etc.)
            if filename.startswith("."):
                continue

            file_path = os.path.join(session_dir, filename)

            # Ne supprimer que les fichiers (pas les sous-répertoires)
            if os.path.isfile(file_path):
                try:
                    file_size = os.path.getsize(file_path)
                    os.remove(file_path)
                    deleted_count += 1
                    total_size += file_size
                except Exception as e:
                    error_count += 1
                    print(f"   ⚠️ Erreur suppression {filename}: {str(e)}")

        if deleted_count > 0:
            size_mb = total_size / (1024 * 1024)
            print(
                f"   ✅ {deleted_count} fichier(s) de session supprimé(s) ({size_mb:.2f} MB libérés)"
            )
        else:
            print("   ℹ️  Aucun fichier de session à supprimer")

        if error_count > 0:
            print(f"   ⚠️ {error_count} erreur(s) lors de la suppression")

    except Exception as e:
        print(f"   ❌ Erreur lors de la purge des sessions: {str(e)}")


# Purger les sessions au démarrage si activé
PURGE_SESSIONS_ON_STARTUP = get_env_bool("PURGE_SESSIONS_ON_STARTUP", "True")

if PURGE_SESSIONS_ON_STARTUP:
    purge_session_directory(session_base_dir)
else:
    print("ℹ️  Purge des sessions au démarrage désactivée")

app.config["SESSION_FILE_DIR"] = session_base_dir
app.config["SESSION_FILE_THRESHOLD"] = int(os.getenv("SESSION_FILE_THRESHOLD", "500"))

# Configuration des cookies de session
app.config["SESSION_COOKIE_SAMESITE"] = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
app.config["SESSION_COOKIE_SECURE"] = get_env_bool("SESSION_COOKIE_SECURE", "False")
app.config["SESSION_COOKIE_HTTPONLY"] = get_env_bool("SESSION_COOKIE_HTTPONLY", "True")
app.config["SESSION_COOKIE_NAME"] = os.getenv("SESSION_COOKIE_NAME", "session_simsan")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
    hours=int(os.getenv("SESSION_LIFETIME_HOURS", "24"))
)
app.config["SESSION_USE_SIGNER"] = get_env_bool("SESSION_USE_SIGNER", "True")


# Configuration OAuth2 Gauthiq
app.config["GAUTHIQ_CLIENT_ID"] = os.getenv("GAUTHIQ_CLIENT_ID")
app.config["GAUTHIQ_CLIENT_SECRET"] = os.getenv("GAUTHIQ_CLIENT_SECRET")
app.config["GAUTHIQ_DISCOVERY_URL"] = os.getenv("GAUTHIQ_DISCOVERY_URL")
app.config["GAUTHIQ_REDIRECT_URI"] = os.getenv("GAUTHIQ_REDIRECT_URI")
app.config["GAUTHIQ_SSL_VERIFY"] = os.getenv("GAUTHIQ_SSL_VERIFY", "True").lower() in (
    "true",
    "1",
    "t",
)

# Configuration Habilitations Gauthiq
app.config["GAUTHIQ_HABILITATION"] = os.getenv("GAUTHIQ_HABILITATION")
app.config["GAUTHIQ_HABILITATION_FILTRE"] = os.getenv("GAUTHIQ_HABILITATION_FILTRE")

# Initialisation de la session Flask
Session(app)

# Diagnostic de la configuration session
print("=" * 60)
print("📋 CONFIGURATION SESSION FLASK - FILESHARE")
print("=" * 60)
print(f"SESSION_TYPE: {app.config.get('SESSION_TYPE')}")
print(f"SESSION_FILE_DIR: {app.config.get('SESSION_FILE_DIR')}")
print(f"SESSION_FILE_THRESHOLD: {app.config.get('SESSION_FILE_THRESHOLD')}")
print(f"SESSION_COOKIE_NAME: {app.config.get('SESSION_COOKIE_NAME')}")
print(f"SESSION_COOKIE_SAMESITE: {app.config.get('SESSION_COOKIE_SAMESITE')}")
print(f"SESSION_COOKIE_SECURE: {app.config.get('SESSION_COOKIE_SECURE')}")
print(f"SESSION_COOKIE_HTTPONLY: {app.config.get('SESSION_COOKIE_HTTPONLY')}")
print(f"SESSION_COOKIE_DOMAIN: {app.config.get('SESSION_COOKIE_DOMAIN', '(none)')}")
print(f"SESSION_COOKIE_PATH: {app.config.get('SESSION_COOKIE_PATH', '/')}")
print(f"SESSION_PERMANENT: {app.config.get('SESSION_PERMANENT')}")
print(f"PERMANENT_SESSION_LIFETIME: {app.config.get('PERMANENT_SESSION_LIFETIME')}")
print(f"SECRET_KEY configurée: {'Oui' if app.config.get('SECRET_KEY') else 'NON'}")
print(f"SECRET_KEY length: {len(app.config.get('SECRET_KEY', ''))}")

# Vérifier l'accès au répertoire
session_dir = app.config.get("SESSION_FILE_DIR")
if os.path.exists(session_dir):
    session_count = len([f for f in os.listdir(session_dir) if not f.startswith(".")])
    writable = os.access(session_dir, os.W_OK)
    print(f"✅ Répertoire session: {session_dir}")
    print(f"   Accessible en écriture: {'Oui' if writable else 'NON'}")
    print(f"   Sessions existantes: {session_count}")
else:
    print(f"⚠️  Répertoire session n'existe pas encore: {session_dir}")

print("=" * 60)
print("📋 CONFIGURATION GAUTHIQ HABILITATIONS")
print("=" * 60)
print(
    f"GAUTHIQ_HABILITATION: {app.config.get('GAUTHIQ_HABILITATION', 'NON CONFIGURÉ')}"
)
print(
    f"GAUTHIQ_HABILITATION_FILTRE: {app.config.get('GAUTHIQ_HABILITATION_FILTRE', 'NON CONFIGURÉ')}"
)
print("=" * 60)

# Initialisation de l'authentification Gauthiq
auth = GauthiqAuth(app)

# Plus besoin de synchronisation - le StorageManager gère directement l'accès au FileShare monté
app.logger.info("📁 Stockage unifié initialisé - accès direct au FileShare")


# Configuration des profils
dico_profil = [
    {"profile": "Particulier", "label": "Particulier"},
    {"profile": "ACPS", "label": "ACPS"},
    {"profile": "Agriculteur", "label": "Agriculteur"},
]

# Liste des administrateurs
LISTE_ADMINS = os.getenv("LISTE_ADMINS", "").split(",")

# Répertoires de stockage
CONVERSATIONS_DIR = os.path.join(os.getcwd(), "data", "conversations")
SYNTHESES_DIR = os.path.join(os.getcwd(), "data", "syntheses")
SUIVIS_DIR = os.path.join(os.getcwd(), "data", "suivis")
os.makedirs(CONVERSATIONS_DIR, exist_ok=True)
os.makedirs(SYNTHESES_DIR, exist_ok=True)
os.makedirs(SUIVIS_DIR, exist_ok=True)

# Configuration Azure Speech
speech_key = os.getenv("AZURE_SPEECH_KEY")
service_region = os.getenv("AZURE_SERVICE_REGION")
speech_endpoint = os.getenv("AZURE_SPEECH_ENDPOINT")


global compteur
compteur = 0

# Client Azure OpenAI
try:
    client = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    )
except Exception as e:
    print(f"Erreur lors de l'initialisation du client Azure OpenAI: {str(e)}")


# Configuration du logging optimisé
def setup_azure_optimized_logging(app):
    """Configure un système de logging optimisé pour Azure Web Apps"""
    async_logger = get_async_logger()
    log_dir = Path("log")
    log_dir.mkdir(exist_ok=True)

    app.logger.setLevel(logging.WARNING)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_formatter = logging.Formatter("%(asctime)s - CRITICAL - %(message)s")
    console_handler.setFormatter(console_formatter)

    if app.logger.handlers:
        app.logger.handlers.clear()

    app.logger.addHandler(console_handler)
    app.logger.propagate = False

    external_loggers = ["werkzeug", "urllib3", "azure", "requests", "openai"]
    for logger_name in external_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.ERROR)
        logger.propagate = False

    async_logger.info("=== SYSTÈME DE LOGGING AZURE ASYNCHRONE INITIALISÉ ===")
    return async_logger


# Middleware de logging
@app.before_request
def log_request_optimized():
    """Log optimisé des requêtes importantes"""
    async_logger = get_async_logger()

    if request.path.startswith(("/static/", "/favicon.ico", "/_stcore/")):
        return

    request_info = {
        "method": request.method,
        "path": request.path,
        "remote_addr": request.remote_addr,
        "user_agent": request.headers.get("User-Agent", "")[:100],
    }

    async_logger.info("REQUEST", extra_data=request_info)


@app.after_request
def log_response_optimized(response):
    """Log optimisé des réponses (erreurs uniquement)"""
    async_logger = get_async_logger()

    if request.path.startswith(("/static/", "/favicon.ico", "/_stcore/")):
        return response

    if response.status_code >= 400:
        async_logger.warning(
            f"HTTP ERROR {response.status_code}",
            method=request.method,
            path=request.path,
            remote_addr=request.remote_addr,
        )

    return response


# ============= ROUTES PRINCIPALES =============


@app.route("/")
@auth.login_required  # Protection par authentification
def index():
    """Page d'accueil - requiert une authentification"""
    async_logger = get_async_logger()

    # Récupérer les informations utilisateur depuis Gauthiq
    user_info = auth.get_user_info()
    user_name = user_info.get("preferred_username", user_info.get("name", "Unknown"))
    user_email = user_info.get("email", "unknown@email.com")
    user_id = user_info.get("sub", "unknown_id")
    print(f"User info: {user_info}")
    async_logger.info("SESSION START", user=user_name)

    # Initialisation de la session
    init_session_lists()
    init_session_profile(profil_manager)

    session.setdefault("user_rating", None)
    session["profile"] = session.get("profile_data", {}).get(
        "type_personne", "Particulier"
    )
    session["user_name"] = user_name
    session["user_email"] = user_email
    session["syfadis_userid"] = user_id
    session["syfadis_username"] = user_name
    session["syfadis_useremail"] = user_email

    async_logger.info("Profile initialized", profile=session["profile"])
    async_logger.info(
        "User session configured", user=user_name, email=user_email, userid=user_id
    )

    if "conversation_history" not in session:
        session["conversation_history"] = []
        async_logger.info("New conversation history initialized")
    else:
        async_logger.info(
            "Existing conversation found",
            messages_count=len(session["conversation_history"]),
        )

    session["user_folder"], session["history_conv"], session["history_eval"] = (
        get_user_folder_path(user_name)
    )
    log_to_journal(user_name, user_email, "connexion")

    async_logger.info("User session complete", folder=session["user_folder"])

    if "history_eval" not in session:
        session["history_eval"] = []
    if "history_conv" not in session:
        session["history_conv"] = []

    return render_template(
        "index.html", service_region=service_region, dico_profil=dico_profil
    )


@app.route("/get_speech_token", methods=["GET"])
@auth.login_required
def get_speech_token():
    """
    Génère un token d'autorisation temporaire pour Azure Speech Service
    Le token est valide pendant 10 minutes
    Cela évite d'exposer la clé API côté client
    """
    try:
        # Utiliser l'endpoint complet si disponible (meilleur pour Azure Web Apps)
        # Sinon construire l'URL depuis la région
        if speech_endpoint:
            # Extraire le host de l'endpoint pour construire l'URL du token
            # Format attendu: https://xxxxx.cognitiveservices.azure.com/
            endpoint_base = speech_endpoint.rstrip("/")
            fetch_token_url = f"{endpoint_base}/sts/v1.0/issueToken"
            app.logger.info(f"Utilisation endpoint configuré: {fetch_token_url}")
        else:
            # Fallback sur la région
            fetch_token_url = f"https://{service_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
            app.logger.info(f"Utilisation région: {fetch_token_url}")

        headers = {"Ocp-Apim-Subscription-Key": speech_key}

        # Requête pour obtenir le token avec retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(fetch_token_url, headers=headers, timeout=30)

                if response.status_code == 200:
                    access_token = response.text
                    return jsonify(
                        {
                            "token": access_token,
                            "region": service_region,
                            "endpoint": speech_endpoint,
                            "success": True,
                        }
                    )
                else:
                    app.logger.error(
                        f"Erreur HTTP {response.status_code} lors de la génération du token Speech"
                    )
                    if attempt < max_retries - 1:
                        continue
                    return jsonify(
                        {
                            "success": False,
                            "error": f"Erreur HTTP {response.status_code}",
                        }
                    ), 500
            except requests.exceptions.RequestException as req_err:
                app.logger.error(
                    f"Tentative {attempt + 1}/{max_retries} - Erreur réseau: {str(req_err)}"
                )
                if attempt < max_retries - 1:
                    import time

                    time.sleep(1)  # Attendre 1 seconde avant retry
                    continue
                raise

    except Exception as e:
        app.logger.error(f"Exception lors de la génération du token Speech: {str(e)}")
        return jsonify(
            {
                "success": False,
                "error": "Impossible de générer le token. Vérifiez la configuration Azure Speech.",
                "details": str(e) if app.debug else None,
            }
        ), 500


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


# Protection contre les appels multiples
_last_profile_change = {}


@app.route("/set_profile", methods=["POST"])
@auth.login_required
def set_profile():
    """Définir le profil utilisateur - requiert une authentification"""
    async_logger = get_async_logger()
    data = request.json
    profile = data.get("profile")

    user_key = session.get("user_name", "anonymous") + "_" + str(id(session))
    current_time = datetime.now().timestamp()

    # Protection contre les doublons
    if user_key in _last_profile_change:
        time_diff = current_time - _last_profile_change[user_key]["time"]
        last_profile = _last_profile_change[user_key]["profile"]

        if time_diff < 2.0 and last_profile == profile:
            async_logger.warning(
                "Duplicate profile change call ignored",
                user_key=user_key,
                profile=profile,
                time_diff=f"{time_diff:.2f}s",
            )
            return jsonify(
                {
                    "success": True,
                    "profile": profile,
                    "message": "Appel en doublon ignoré",
                }
            )

    _last_profile_change[user_key] = {"time": current_time, "profile": profile}

    if not profile or not any(p["profile"] == profile for p in dico_profil):
        async_logger.error("Invalid profile requested", profile=profile)
        return jsonify({"success": False, "error": "Profil invalide"}), 400

    current_profile = session.get("profile_data", {}).get("type_personne")
    if current_profile == profile:
        async_logger.info("Profile already active", profile=profile)
        return jsonify(
            {"success": True, "profile": profile, "message": "Profil déjà actif"}
        )

    try:
        async_logger.info(
            "Profile change initiated", from_profile=current_profile, to_profile=profile
        )

        new_pm = ProfilManager(type_personne=profile)

        if "conversation_history" in session:
            session["conversation_history"] = []

        save_profil_manager_to_session(new_pm)
        session.modified = True

        async_logger.info("Profile changed successfully", new_profile=profile)
        return jsonify({"success": True, "profile": profile})

    except Exception as e:
        async_logger.error("Profile change error", error=str(e), profile=profile)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/reset_conversation", methods=["POST"])
@auth.login_required
def reset_conversation():
    """Réinitialiser la conversation - requiert une authentification"""
    async_logger = get_async_logger()
    global compteur
    compteur = 0
    session["conversation_history"] = []
    session.modified = True
    async_logger.info("Conversation reset", user=session.get("user_name", "Unknown"))
    return jsonify({"success": True})


@app.route("/get_conversation_history", methods=["GET"])
@auth.login_required
def get_conversation_history():
    """Récupérer l'historique de conversation - requiert une authentification"""
    async_logger = get_async_logger()

    if "conversation_history" not in session:
        session["conversation_history"] = []

    async_logger.info(
        "Conversation history retrieved",
        user=session.get("user_name", "Unknown"),
        messages_count=len(session["conversation_history"]),
    )

    return jsonify({"success": True, "history": session["conversation_history"]})


@app.route("/serve_file_azure/<file_type>/<path:filename>")
@auth.login_required
def serve_file_azure(file_type, filename):
    """Servir un fichier depuis Azure - requiert une authentification"""
    async_logger = get_async_logger()

    try:
        user_folder = session.get("user_folder", "default_user")
        success, content = get_file_from_azure(file_type, filename, user_folder)

        if not success or content is None:
            async_logger.warning(
                "File not found on Azure",
                filename=filename,
                file_type=file_type,
                user_folder=user_folder,
            )
            return jsonify({"error": "Fichier non trouvé sur Azure"}), 404

        if filename.endswith(".html"):
            mimetype = "text/html"
        elif filename.endswith(".json"):
            mimetype = "application/json"
        else:
            mimetype = "text/plain"

        async_logger.info(
            "File served from Azure",
            filename=filename,
            mimetype=mimetype,
            content_size=len(content),
        )

        return Response(content, mimetype=mimetype)

    except Exception as e:
        async_logger.error("Azure file service error", filename=filename, error=str(e))
        return jsonify({"error": "Erreur lors de l'accès au fichier"}), 500


@app.route("/serve_file/<file_type>/<path:filename>")
@auth.login_required
def serve_file(file_type, filename):
    """Servir un fichier local - requiert une authentification"""
    async_logger = get_async_logger()

    try:
        if file_type == "conversation":
            directory = CONVERSATIONS_DIR
        elif file_type == "synthese":
            directory = SYNTHESES_DIR
        else:
            async_logger.error("Unsupported file type", file_type=file_type)
            return jsonify({"error": "Type de fichier non supporté"}), 400

        filepath = os.path.join(directory, filename)

        if not os.path.exists(filepath):
            async_logger.warning("Local file not found", filepath=filepath)
            return jsonify({"error": "Fichier non trouvé"}), 404

        if filename.endswith(".html"):
            mimetype = "text/html"
        elif filename.endswith(".json"):
            mimetype = "application/json"
        else:
            mimetype = "text/plain"

        async_logger.info("Local file served", filename=filename, mimetype=mimetype)
        return send_from_directory(directory, filename, mimetype=mimetype)

    except Exception as e:
        async_logger.error("Local file service error", filename=filename, error=str(e))
        return jsonify({"error": "Erreur lors de l'accès au fichier"}), 500


@app.route("/chat", methods=["POST"])
@auth.login_required
def chat():
    """Endpoint de chat - requiert une authentification"""
    async_logger = get_async_logger()
    global compteur

    init_session_lists()
    restore_profil_manager_from_session(profil_manager=profil_manager)

    required_env_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_DEPLOYMENT_m",
        "AZURE_OPENAI_DEPLOYMENT_n",
        "AZURE_OPENAI_API_KEY",
    ]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        async_logger.error("Missing environment variables", missing_vars=missing_vars)
        return jsonify(
            {
                "error": f"Variables d'environnement manquantes : {', '.join(missing_vars)}"
            }
        ), 500

    data = request.json

    # NOUVELLE SÉCURISATION - Remplacer les 3 lignes existantes par :
    raw_message = data.get("message", "")

    # Validation du format
    is_valid, error_msg = validate_message_format(raw_message)
    if not is_valid:
        async_logger.warning(
            "Invalid message format",
            user=session.get("user_name", "Unknown"),
            error=error_msg,
        )
        return jsonify({"error": error_msg}), 400

    # Nettoyage et sécurisation
    user_message = sanitize_user_input(
        raw_message, max_length=5000, allow_newlines=True
    )

    # Vérification après nettoyage
    if not user_message or len(user_message.strip()) < 1:
        async_logger.warning(
            "Empty message after sanitization", user=session.get("user_name", "Unknown")
        )
        return jsonify({"error": "Message invalide après nettoyage"}), 400

    profile = data.get("profile") or session.get("profile")

    current_profile_type = session.get("profile_data", {}).get("type_personne")
    if not current_profile_type:
        init_session_profile(profil_manager)
        current_profile_type = session.get("profile_data", {}).get("type_personne")

    if "conversation_history" not in session:
        session["conversation_history"] = []

    historique = session["conversation_history"]

    async_logger.info(
        "Chat message received",
        user=session.get("user_name", "Unknown"),
        message_length=len(user_message),
        conversation_length=len(historique),
        profile=current_profile_type,
    )

    result = get_next_bot_message(user_message, client, historique, profil_manager)

    user_timestamp = datetime.now().isoformat()
    bot_timestamp = datetime.now().isoformat()

    session["conversation_history"].append(
        {
            "msg_num": compteur,
            "role": "Vous",
            "text": user_message,
            "timestamp": user_timestamp,
        }
    )
    compteur += 1
    session["conversation_history"].append(
        {
            "msg_num": compteur,
            "role": "Assistant",
            "text": result["reply"],
            "timestamp": bot_timestamp,
        }
    )
    compteur += 1
    session.modified = True

    async_logger.info(
        "Chat response generated",
        response_length=len(result["reply"]),
        total_messages=len(session["conversation_history"]),
    )

    return jsonify(
        {
            "reply": result["reply"],
            "history": session["conversation_history"],
            "user_timestamp": user_timestamp,
            "bot_timestamp": bot_timestamp,
        }
    )


@app.route("/synthetiser", methods=["POST"])
@auth.login_required
def synthetiser():
    """Synthétiser la conversation - requiert une authentification"""
    async_logger = get_async_logger()
    init_session_lists()
    restore_profil_manager_from_session(profil_manager=profil_manager)

    if "conversation_history" not in session or not session["conversation_history"]:
        async_logger.warning(
            "Synthesis attempted with empty conversation",
            user=session.get("user_name", "Unknown"),
        )
        return jsonify({"error": "Pas d'historique à synthétiser"}), 400

    try:
        async_logger.info(
            "Starting conversation synthesis",
            user=session.get("user_name", "Unknown"),
            conversation_length=len(session["conversation_history"]),
        )

        synthesis_json = synthese_2(
            session["conversation_history"],
            client,
            documents_reference,
            profil_manager=profil_manager,
        )

        niveau_mapping = {
            "À améliorer": 1,
            "Satisfaisant": 2,
            "Bien": 3,
            "Très bien": 4,
        }

        niveau_general = synthesis_json.get("synthese", {}).get(
            "niveau_general", "À améliorer"
        )
        niveau = niveau_mapping.get(niveau_general, 1)

        async_logger.info(
            "Synthesis level evaluated", level=niveau_general, numeric_level=niveau
        )

        if session["conversation_history"]:
            statistiques = calcule_statistiques_conv(session["conversation_history"])
            async_logger.info(
                "Conversation statistics calculated",
                duration=statistiques["duree_conversation"],
                total_words=statistiques["nombre_mots_total"],
            )

        profil_type = session.get("profile_data", {}).get(
            "type_personne", "Particulier"
        )
        person_details = session.get("profile_data", {}).get("person_details", {})
        person_name = person_details.get("Nom", "Inconnu").replace(" ", "_")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name_html = (
            f"Rapport_synthese_{niveau}_{profil_type}_{person_name}_{timestamp}.html"
        )
        file_name_json = (
            f"Rapport_synthese_{niveau}_{profil_type}_{person_name}_{timestamp}.json"
        )

        async_logger.info("Converting synthesis to HTML", filename=file_name_html)

        html_data = generer_rapport_html_synthese(
            synthesis_json, chemin_fichier_sortie=file_name_html
        )

        user_folder = session.get("user_folder", "default_user")

        success_json, azure_path_json = save_file_to_azure(
            json.dumps(synthesis_json, ensure_ascii=False, indent=2),
            "synthese",
            file_name_json,
            user_folder,
        )

        success_html, azure_path_html = save_file_to_azure(
            html_data, "synthese", file_name_html, user_folder
        )

        if success_json and success_html:
            session["history_eval"].extend([file_name_json, file_name_html])
            session.modified = True

            flask_url = url_for(
                "serve_file_azure",
                file_type="synthese",
                filename=file_name_html,
                _external=True,
            )

            async_logger.info(
                "Synthesis saved to Azure successfully",
                url=flask_url,
                json_file=file_name_json,
                html_file=file_name_html,
            )

            # Enregistrer dans le journal (la note utilisateur a déjà été enregistrée séparément)
            log_to_journal(
                session["user_name"],
                session["user_email"],
                "génération de synthèse",
                stats=statistiques,
                note_user="--",
            )

            try:
                async_logger.info("Auto-resetting conversation after synthesis")

                global compteur
                compteur = 0
                session["conversation_history"] = []

                # Réinitialiser le profil en gardant le même type mais avec un nouveau persona
                try:
                    # Récupérer le type de profil actuel
                    current_profile_type = session.get("profile_data", {}).get(
                        "type_personne", "Particulier"
                    )

                    async_logger.info(
                        "Generating new persona in same profile type after synthesis",
                        current_profile_type=current_profile_type,
                    )

                    # Créer un nouveau ProfilManager avec le MÊME type de profil
                    # Le ProfilManager va générer un nouveau personnage aléatoire dans cette catégorie
                    new_pm = ProfilManager(type_personne=current_profile_type)
                    save_profil_manager_to_session(new_pm)

                    # Récupérer les détails du nouveau personnage
                    person_details = new_pm.get_person_details()
                    person_name = person_details.get("Nom", "Inconnu")

                    async_logger.info(
                        "New persona initialized successfully after synthesis",
                        profile_type=current_profile_type,
                        person_name=person_name,
                        person_details=person_details,
                    )

                    profile_reset_success = True
                    profile_reset_message = (
                        f"Nouveau personnage {current_profile_type} : {person_name}"
                    )
                    new_profile_data = {
                        "type": current_profile_type,
                        "name": person_name,
                        "details": person_details,
                    }

                except Exception as profile_error:
                    async_logger.warning(
                        "Persona reset failed after synthesis", error=str(profile_error)
                    )
                    profile_reset_success = False
                    profile_reset_message = f"Erreur lors de la réinitialisation du personnage: {str(profile_error)}"
                    new_profile_data = None

                session.modified = True

                async_logger.info(
                    "Conversation and persona reset successfully after synthesis"
                )

                return jsonify(
                    {
                        "success": True,
                        "filepath": flask_url,
                        "filename": file_name_json,
                        "message": "Synthèse terminée, conversation réinitialisée et nouveau profil généré",
                        "reset_performed": True,
                        "conversation_cleared": True,
                        "profile_reset": profile_reset_success,
                        "profile_message": profile_reset_message,
                        "new_profile": new_profile_data,
                    }
                )

            except Exception as reset_error:
                async_logger.warning("Auto-reset failed", error=str(reset_error))

                return jsonify(
                    {
                        "success": True,
                        "filepath": flask_url,
                        "filename": file_name_json,
                        "message": "Synthèse terminée (erreur lors de la réinitialisation)",
                        "reset_performed": False,
                        "conversation_cleared": False,
                        "reset_error": str(reset_error),
                    }
                )
        else:
            async_logger.error("Failed to save synthesis to Azure")
            return jsonify({"error": "Échec de la sauvegarde sur Azure"}), 500

    except Exception as e:
        async_logger.error("Synthesis error", error=str(e))
        return jsonify({"error": str(e)}), 500


@app.route("/history")
@auth.login_required
def history():
    """Historique des conversations - requiert une authentification"""
    async_logger = get_async_logger()
    init_session_lists()

    try:
        user_folder = session.get("user_folder", "default_user")
        files_info = list_files_from_azure("conversation", user_folder)

        conversations = []
        for file_info in files_info:
            filename = file_info["filename"]

            if not filename.endswith(".html"):
                continue

            date_conv = file_info["last_modified"]
            if hasattr(date_conv, "strftime"):
                date_str = date_conv.strftime("%d/%m/%Y %H:%M")
            else:
                date_str = str(date_conv)

            flask_url = url_for(
                "serve_file_azure",
                file_type="conversation",
                filename=filename,
                _external=True,
            )
            conversations.append(
                {
                    "date": date_str,
                    "fichier": filename,
                    "url": flask_url,
                    "taille": file_info["size"],
                }
            )

        conversations.sort(key=lambda x: x["date"], reverse=True)

        async_logger.info(
            "History page loaded",
            user=session.get("user_name", "Unknown"),
            conversations_count=len(conversations),
        )

        return render_template("history.html", conversations=conversations)

    except Exception as e:
        async_logger.error("History loading error", error=str(e))
        return render_template("history.html", conversations=[], error=str(e))


@app.route("/suivi_syntheses")
@auth.login_required
def suivi_syntheses():
    """Suivi des synthèses - requiert une authentification"""
    async_logger = get_async_logger()
    init_session_lists()

    highlight_filename = request.args.get("highlight")

    if highlight_filename:
        try:
            highlight_filename = urllib.parse.unquote(highlight_filename)
            async_logger.info(
                "Highlight filename decoded",
                original=request.args.get("highlight"),
                decoded=highlight_filename,
            )
        except Exception as e:
            async_logger.warning(
                "Failed to decode highlight filename",
                filename=highlight_filename,
                error=str(e),
            )

    try:
        user_folder = session.get("user_folder", "default_user")
        files_info = list_files_from_azure("synthese", user_folder)

        syntheses = []
        for file_info in files_info:
            filename = file_info["filename"]

            if not filename.endswith(".html"):
                continue

            match = re.search(r"_(\d{8}_\d{6})\.html$", filename)
            if match:
                timestamp_str = match.group(1)
                dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                date_str = dt.strftime("%d/%m/%Y %H:%M")
            else:
                date_str = "Date inconnue"

            appreciation = "À améliorer"
            try:
                match = re.search(r"Rapport_synthese_(\d)_", filename)
                if match:
                    niveau_num = int(match.group(1))
                    niveau_mapping = {
                        1: "À améliorer",
                        2: "Satisfaisant",
                        3: "Bien",
                        4: "Très bien",
                    }
                    appreciation = niveau_mapping.get(niveau_num, "À améliorer")
            except Exception as e:
                async_logger.warning(
                    "Failed to extract rating from filename",
                    filename=filename,
                    error=str(e),
                )

            flask_url = url_for(
                "serve_file_azure",
                file_type="synthese",
                filename=filename,
                _external=True,
            )
            syntheses.append(
                {
                    "date": date_str,
                    "rapport": filename,
                    "rapport_url": flask_url,
                    "appreciation": appreciation,
                }
            )

        syntheses.sort(
            key=lambda x: datetime.strptime(x["date"], "%d/%m/%Y %H:%M"), reverse=True
        )

        async_logger.info(
            "Synthesis tracking page loaded",
            user=session.get("user_name", "Unknown"),
            syntheses_count=len(syntheses),
            highlight_filename=highlight_filename,
        )

        return render_template(
            "suivi_syntheses.html",
            syntheses=syntheses,
            highlight_filename=highlight_filename,
        )

    except Exception as e:
        async_logger.error("Synthesis tracking error", error=str(e))
        return render_template(
            "suivi_syntheses.html",
            syntheses=[],
            error=str(e),
            highlight_filename=highlight_filename,
        )


@app.route("/get_person_details", methods=["POST"])
@auth.login_required
def get_person_details():
    """Récupérer les détails de la personne - requiert une authentification"""
    async_logger = get_async_logger()
    try:
        restore_profil_manager_from_session(profil_manager=profil_manager)
        person_details = profil_manager.get_person_details()
        async_logger.info(
            "Person details retrieved", user=session.get("user_name", "Unknown")
        )
        return jsonify(person_details or {"Sexe": "Homme"})
    except Exception as e:
        async_logger.error("Error retrieving profile details", error=str(e))
        return jsonify({"Sexe": "Homme"}), 500


@app.route("/check_admin", methods=["GET"])
@auth.login_required
def check_admin():
    """Vérifier si l'utilisateur connecté est admin"""
    async_logger = get_async_logger()
    user_name = session.get("user_name", "Unknown")
    user_email = session.get("user_email", "unknown@email.com")
    user_habilitations = session.get("user_habilitations", {})

    # Étape 1: Vérification des informations utilisateur
    async_logger.info("=" * 60)
    async_logger.info("🔍 VÉRIFICATION DES HABILITATIONS")
    async_logger.info("=" * 60)
    async_logger.info(f"👤 Utilisateur: {user_name}")
    async_logger.info(f"📧 Email: {user_email}")

    # Étape 2: Affichage des habilitations récupérées
    if user_habilitations:
        async_logger.info("✅ Habilitations trouvées en session")
        async_logger.info(f"📋 Nombre de clés: {len(user_habilitations)}")

        # Afficher les rôles si présents
        if "roles" in user_habilitations:
            roles = user_habilitations["roles"]
            async_logger.info(f"🎭 Nombre de rôles: {len(roles)}")
            for role_name, permissions in roles.items():
                async_logger.info(f"   • {role_name}: {len(permissions)} permissions")
    else:
        async_logger.warning("⚠️ Aucune habilitation trouvée en session")

    # Étape 3: Vérification de la liste des admins
    async_logger.info(f"📑 Liste des admins configurée: {len(LISTE_ADMINS)} entrées")
    async_logger.info(
        f"   • Admins: {', '.join(LISTE_ADMINS[:5])}{'...' if len(LISTE_ADMINS) > 5 else ''}"
    )

    # Étape 4: Vérification du statut admin
    is_admin_by_name = user_name in LISTE_ADMINS
    is_admin_by_email = user_email in LISTE_ADMINS
    is_admin = is_admin_by_name or is_admin_by_email

    async_logger.info("🔐 Résultat de la vérification:")
    async_logger.info(
        f"   • Admin par nom d'utilisateur: {'✅ OUI' if is_admin_by_name else '❌ NON'}"
    )
    async_logger.info(
        f"   • Admin par email: {'✅ OUI' if is_admin_by_email else '❌ NON'}"
    )
    async_logger.info(
        f"   • Statut final: {'✅ ADMIN' if is_admin else '❌ UTILISATEUR STANDARD'}"
    )
    async_logger.info("=" * 60)

    return jsonify({"is_admin": is_admin})


@app.route("/list_conversations", methods=["GET"])
@auth.login_required
def list_conversations():
    """Lister les conversations - requiert une authentification"""
    async_logger = get_async_logger()
    init_session_lists()

    try:
        user_folder = session.get("user_folder", "default_user")
        files_info = list_files_from_azure("conversation", user_folder)

        conversations = []
        for file_info in files_info:
            filename = file_info["filename"]

            if filename.endswith(".json"):
                date_conv = file_info["last_modified"]
                if hasattr(date_conv, "strftime"):
                    date_str = date_conv.strftime("%d/%m/%Y %H:%M")
                    creation_time = date_conv.timestamp()
                else:
                    date_str = str(date_conv)
                    creation_time = 0

                conversations.append(
                    {
                        "id": filename,
                        "name": filename,
                        "date": date_str,
                        "size": file_info["size"],
                        "creation_time": creation_time,
                    }
                )

        conversations.sort(key=lambda x: x["creation_time"], reverse=True)

        for conv in conversations:
            del conv["creation_time"]

        async_logger.info(
            "Conversations list retrieved",
            user=session.get("user_name", "Unknown"),
            count=len(conversations),
        )

        return jsonify({"conversations": conversations})

    except Exception as e:
        async_logger.error("Error retrieving conversations list", error=str(e))
        return jsonify({"error": str(e)}), 500


@app.route("/load_conversations", methods=["GET"])
@auth.login_required
def load_conversations_admin():
    """Page admin pour charger des conversations - requiert authentification + droits admin"""
    async_logger = get_async_logger()

    user_name = session.get("user_name", "unknown")
    user_email = session.get("user_email", "unknown@example.com")

    if user_name not in LISTE_ADMINS and user_email not in LISTE_ADMINS:
        async_logger.warning(
            "Unauthorized access to load_conversations",
            user=user_name,
            email=user_email,
        )
        return render_template(
            "error.html",
            error_title="Accès non autorisé",
            error_message="Vous n'avez pas l'autorisation d'accéder à cette page.",
        ), 403

    try:
        init_session_lists()
        async_logger.info(
            "Load conversations admin page accessed", admin_user=user_name
        )
        return render_template("load_conversations.html")
    except Exception as e:
        async_logger.error(
            "Error accessing load conversations admin page", error=str(e)
        )
        return render_template(
            "error.html", error_title="Erreur", error_message=str(e)
        ), 500


@app.route("/upload_conversation", methods=["POST"])
@auth.login_required
def upload_conversation():
    """Upload d'une conversation - requiert une authentification"""
    async_logger = get_async_logger()
    try:
        if "file" not in request.files:
            async_logger.error("Upload conversation: no file sent")
            return jsonify({"error": "Aucun fichier n'a été envoyé"}), 400

        file = request.files["file"]

        if file.filename == "":
            async_logger.error("Upload conversation: no file selected")
            return jsonify({"error": "Aucun fichier sélectionné"}), 400

        if not file.filename.endswith(".json"):
            async_logger.error(
                "Upload conversation: invalid file format", filename=file.filename
            )
            return jsonify({"error": "Le fichier doit être au format JSON"}), 400

        try:
            conversation_content = json.loads(file.read().decode("utf-8"))
        except json.JSONDecodeError as e:
            async_logger.error(
                "Upload conversation: JSON decode error",
                filename=file.filename,
                error=str(e),
            )
            return jsonify({"error": "Format de fichier JSON invalide"}), 400

        session["conversation_history"] = conversation_content

        global compteur
        if conversation_content:
            max_msg_num = max([msg.get("msg_num", 0) for msg in conversation_content])
            compteur = max_msg_num + 1
        else:
            compteur = 0

        session.modified = True

        async_logger.info(
            "Conversation uploaded successfully",
            filename=file.filename,
            messages_count=len(conversation_content),
            new_counter=compteur,
        )

        return jsonify(
            {
                "success": True,
                "message": "Conversation chargée avec succès",
                "conversation": conversation_content,
            }
        )

    except Exception as e:
        async_logger.error("Error uploading conversation", error=str(e))
        return jsonify({"error": str(e)}), 500


# ============= FAQ =============


@app.route("/faq")
@auth.login_required
def faq():
    """Page FAQ - requiert une authentification"""
    async_logger = get_async_logger()
    try:
        init_session_lists()
        async_logger.info("FAQ page accessed", user=session.get("user_name", "Unknown"))
        return render_template("faq.html")
    except Exception as e:
        async_logger.error("Error accessing FAQ page", error=str(e))
        return jsonify({"error": "Erreur lors du chargement de la page FAQ"}), 500


@app.route("/faq_chat", methods=["POST"])
@auth.login_required
def faq_chat():
    """Endpoint pour les questions FAQ - requiert une authentification"""
    async_logger = get_async_logger()
    try:
        init_session_lists()

        required_env_vars = [
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_DEPLOYMENT_m",
            "AZURE_OPENAI_API_KEY",
        ]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            async_logger.error(
                "FAQ chat: missing environment variables", missing_vars=missing_vars
            )
            return jsonify(
                {
                    "error": f"Variables d'environnement manquantes : {', '.join(missing_vars)}"
                }
            ), 500

        data = request.get_json()
        raw_question = data.get("message", "")

        # Validation et nettoyage
        is_valid, error_msg = validate_message_format(raw_question)
        if not is_valid:
            async_logger.warning("FAQ: invalid question format", error=error_msg)
            return jsonify({"error": error_msg}), 400

        user_question = sanitize_user_input(
            raw_question, max_length=2000, allow_newlines=False
        )

        if not user_question:
            async_logger.error("FAQ chat: empty question after sanitization")
            return jsonify({"error": "Question invalide après nettoyage"}), 400

        async_logger.info(
            "FAQ question received",
            user=session.get("user_name", "Unknown"),
            question_length=len(user_question),
        )

        expert_response = generate_expert_response(
            user_question,
            client,
            histo=session["faq_history"],
            documents_reference=documents_reference,
        )

        session["faq_history"].append(
            {
                "question": user_question,
                "response": expert_response,
                "timestamp": datetime.now().isoformat(),
            }
        )
        session.modified = True

        async_logger.info(
            "FAQ response generated", response_length=len(expert_response)
        )

        return jsonify(
            {
                "success": True,
                "response": expert_response,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        async_logger.error("FAQ chat error", error=str(e))
        return jsonify({"error": "Erreur lors du traitement de votre question"}), 500


@app.route("/faq_history", methods=["GET"])
@auth.login_required
def faq_history():
    """Récupérer l'historique FAQ - requiert une authentification"""
    async_logger = get_async_logger()
    try:
        history = session.get("faq_history", [])
        async_logger.info(
            "FAQ history retrieved",
            user=session.get("user_name", "Unknown"),
            history_count=len(history),
        )
        return jsonify({"success": True, "history": history})
    except Exception as e:
        async_logger.error("Error retrieving FAQ history", error=str(e))
        return jsonify({"error": "Erreur lors de la récupération de l'historique"}), 500


@app.route("/faq_reset", methods=["POST"])
@auth.login_required
def faq_reset():
    """Réinitialiser l'historique FAQ - requiert une authentification"""
    async_logger = get_async_logger()
    try:
        session["faq_history"] = []
        session.modified = True
        async_logger.info("FAQ history reset", user=session.get("user_name", "Unknown"))
        return jsonify({"success": True, "message": "Historique FAQ réinitialisé"})
    except Exception as e:
        async_logger.error("Error resetting FAQ history", error=str(e))
        return jsonify({"error": "Erreur lors de la réinitialisation"}), 500


# ============= ADMIN =============


@app.route("/admin_suivis")
@auth.login_required
def admin_page():
    """Page d'administration - requiert authentification + droits admin"""
    async_logger = get_async_logger()
    user_name = session.get("user_name", "Unknown")
    user_email = session.get("user_email", "unknown@email.com")

    if user_name not in LISTE_ADMINS and user_email not in LISTE_ADMINS:
        async_logger.warning("Unauthorized admin access attempt", user=user_name)
        return render_template("unauthorized.html"), 403

    async_logger.info("Admin page accessed", user=user_name)
    return render_template("admin.html")


@app.route("/admin/habilitations")
@auth.login_required
def admin_habilitations_page():
    """Page de gestion des habilitations - Admin uniquement"""
    async_logger = get_async_logger()
    user_name = session.get("user_name", "Unknown")
    user_email = session.get("user_email", "unknown@email.com")

    if user_name not in LISTE_ADMINS and user_email not in LISTE_ADMINS:
        async_logger.warning(
            "Unauthorized habilitations access attempt",
            user=user_name,
            email=user_email,
        )
        return render_template("unauthorized.html"), 403

    try:
        from core.habilitations_manager import get_habilitations_manager

        hab_manager = get_habilitations_manager()
        config = hab_manager.get_configuration_complete()

        async_logger.info("Habilitations page accessed", admin_user=user_name)
        return render_template("admin_habilitations.html", config=config)
    except Exception as e:
        async_logger.error("Error loading habilitations page", error=str(e))
        return render_template(
            "error.html",
            error_title="Erreur",
            error_message=f"Impossible de charger la page d'habilitations : {str(e)}",
        ), 500


@app.route("/admin/habilitations/config", methods=["GET"])
@auth.login_required
def admin_habilitations_config():
    """API pour récupérer la configuration actuelle des habilitations"""
    async_logger = get_async_logger()
    user_name = session.get("user_name", "Unknown")
    user_email = session.get("user_email", "unknown@email.com")

    if user_name not in LISTE_ADMINS and user_email not in LISTE_ADMINS:
        async_logger.warning(
            "Unauthorized habilitations config access", user=user_name, email=user_email
        )
        return jsonify({"error": "Accès non autorisé"}), 403

    try:
        from core.habilitations_manager import get_habilitations_manager

        hab_manager = get_habilitations_manager()

        # Charger la configuration complète
        config_file = hab_manager.config_file
        with config_file.open("r", encoding="utf-8") as f:
            import json

            config = json.load(f)

        async_logger.info("Habilitations config retrieved", admin_user=user_name)

        # Retourner la configuration JSON
        return jsonify(config)

    except Exception as e:
        async_logger.error("Error loading habilitations config", error=str(e))
        return jsonify({"error": f"Erreur: {str(e)}"}), 500


@app.route("/admin/habilitations/update", methods=["POST"])
@auth.login_required
def admin_habilitations_update():
    """Mise à jour des habilitations - Admin uniquement"""
    async_logger = get_async_logger()
    user_name = session.get("user_name", "Unknown")
    user_email = session.get("user_email", "unknown@email.com")

    if user_name not in LISTE_ADMINS and user_email not in LISTE_ADMINS:
        async_logger.warning(
            "Unauthorized habilitations update attempt",
            user=user_name,
            email=user_email,
        )
        return jsonify({"success": False, "message": "Accès non autorisé"}), 403

    try:
        from core.habilitations_manager import get_habilitations_manager

        data = request.json
        groupes_habilites = data.get("groupes_habilites", [])

        hab_manager = get_habilitations_manager()
        success, message = hab_manager.update_habilitations(
            groupes_habilites, user_name
        )

        if success:
            async_logger.info(
                "Habilitations updated successfully",
                admin_user=user_name,
                groupes_count=len(groupes_habilites),
            )
            return jsonify({"success": True, "message": message})
        else:
            async_logger.error(
                "Failed to update habilitations", admin_user=user_name, error=message
            )
            return jsonify({"success": False, "message": message}), 400

    except Exception as e:
        async_logger.error("Error updating habilitations", error=str(e))
        return jsonify({"success": False, "message": f"Erreur: {str(e)}"}), 500


@app.route("/download_suivi/<filename>")
@auth.login_required
def download_suivi_file(filename):
    """Télécharger un fichier de suivi - requiert authentification + droits admin"""
    async_logger = get_async_logger()
    user_name = session.get("user_name", "Unknown")

    if user_name not in LISTE_ADMINS:
        async_logger.warning(
            "Unauthorized download attempt", user=user_name, filename=filename
        )
        return "Accès non autorisé", 403

    allowed_files = [
        "journal.csv",
        "note_users.json",
        "synthetiser.log",
        "application.log",
        "app.log",
    ]
    if filename not in allowed_files:
        async_logger.warning(
            "Unauthorized file download attempt", user=user_name, filename=filename
        )
        return "Accès non autorisé", 403

    if filename.endswith(".log"):
        directory = os.path.join(app.root_path, "log")
    else:
        directory = os.path.join(app.root_path, "data", "suivis")

    try:
        async_logger.info("File download initiated", user=user_name, filename=filename)
        return send_from_directory(directory, filename, as_attachment=True)
    except FileNotFoundError:
        async_logger.error(
            "Download file not found", filename=filename, directory=directory
        )
        return "Fichier non trouvé.", 404


@app.route("/save_user_rating", methods=["POST"])
@auth.login_required
def save_user_rating_endpoint():
    """Sauvegarder la note utilisateur - requiert une authentification"""
    async_logger = get_async_logger()
    try:
        data = request.json
        note_user = data.get("note_user")
        conversation_history = data.get("conversation_history", [])

        note_data = {
            "date_heure": datetime.now().isoformat(),
            "note_user": note_user,
            "conversation_history": conversation_history,
        }
        session["user_rating"] = note_user
        session.modified = True

        save_user_rating_to_file(note_data)

        # Enregistrer l'événement dans le journal
        log_to_journal(
            user=session.get("user_name", "Unknown"),
            mail=session.get("user_email", "unknown@unknown.com"),
            event="note utilisateur",
            stats={},  # Pas de statistiques pour cet événement
            note_user=note_user,
        )

        async_logger.info(
            "User rating saved",
            user=session.get("user_name", "Unknown"),
            rating=note_user,
        )

        return jsonify({"success": True, "message": "Note enregistrée."})
    except Exception as e:
        async_logger.error("Error saving user rating", error=str(e))
        return jsonify({"success": False, "error": str(e)}), 500


# ============= ROUTES ADMIN FILESHARE BROWSER =============
# À ajouter dans app.py après les autres routes admin


@app.route("/admin_fileshare_browser")
@auth.login_required
def admin_fileshare_browser():
    """Interface de navigation dans le FileShare - Admin uniquement"""
    async_logger = get_async_logger()
    user_name = session.get("user_name", "Unknown")
    user_email = session.get("user_email", "unknown@example.com")

    # Vérifier les droits admin
    if user_name not in LISTE_ADMINS and user_email not in LISTE_ADMINS:
        async_logger.warning(
            "Unauthorized FileShare browser access", user=user_name, email=user_email
        )
        return render_template(
            "error.html",
            error_title="Accès non autorisé",
            error_message="Vous n'avez pas l'autorisation d'accéder au navigateur FileShare.",
        ), 403

    # Récupérer le chemin demandé (par défaut : racine)
    current_path = request.args.get("path", "").strip("/")

    async_logger.info(
        "FileShare browser accessed", admin_user=user_name, path=current_path
    )

    try:
        from core.storage_manager import get_storage_manager

        storage = get_storage_manager()
        base_path = storage.base_path
        share_name = base_path.name if storage.is_production else "local_data"

        # Construire le chemin complet
        browse_path = base_path / current_path

        # Vérifier que le chemin est dans le répertoire de base
        if not browse_path.resolve().is_relative_to(base_path.resolve()):
            return render_template(
                "error.html",
                error_title="Accès non autorisé",
                error_message="Navigation en dehors du répertoire de base non autorisée.",
            ), 403

        if not browse_path.exists() or not browse_path.is_dir():
            return render_template(
                "error.html",
                error_title="Répertoire introuvable",
                error_message=f"Le chemin '{current_path}' n'existe pas ou n'est pas un répertoire.",
            ), 404

        # Lister le contenu du répertoire actuel
        items = []
        total_size = 0

        HIDDEN_ROOT_FOLDERS = ["log", "suivis", "flask_session"]

        for item in browse_path.iterdir():
            item_name = item.name

            # Filtrer les dossiers masqués uniquement à la racine
            if not current_path and item_name.lower() in HIDDEN_ROOT_FOLDERS:
                async_logger.debug(f"Dossier masqué: {item_name}")
                continue

            is_directory = item.is_dir()
            item_size = 0
            last_modified = None

            try:
                stat = item.stat()
                last_modified = datetime.fromtimestamp(stat.st_mtime)
                if not is_directory:
                    item_size = stat.st_size
                    total_size += item_size
            except Exception as e:
                async_logger.warning(
                    f"Impossible de lire les stats pour {item_name}: {e}"
                )

            items.append(
                {
                    "name": item_name,
                    "is_directory": is_directory,
                    "size": item_size,
                    "last_modified": last_modified,
                    "path": str(item.relative_to(base_path)),
                }
            )

        # Trier : dossiers d'abord, puis fichiers alphabétiquement
        items.sort(key=lambda x: (not x["is_directory"], x["name"].lower()))

        # Construire le breadcrumb (fil d'Ariane)
        breadcrumb = []
        if current_path:
            parts = Path(current_path).parts
            path_accumulator = ""
            for part in parts:
                path_accumulator = Path(path_accumulator) / part
                breadcrumb.append({"name": part, "path": str(path_accumulator)})

        # Récupérer les informations du guide utilisateur si on est à la racine
        guide_exists = False
        guide_filename = None
        if not current_path:
            guide_path = get_guide_path()
            if guide_path and guide_path.exists():
                guide_exists = True
                guide_filename = guide_path.name

        async_logger.info(
            "FileShare content listed",
            path=current_path,
            items_count=len(items),
            total_size=total_size,
        )

        return render_template(
            "fileshare_browser.html",
            items=items,
            current_path=current_path,
            breadcrumb=breadcrumb,
            total_size=total_size,
            share_name=share_name,
            guide_exists=guide_exists,
            guide_filename=guide_filename,
        )

    except Exception as e:
        async_logger.error("FileShare browser error", error=str(e), path=current_path)
        return render_template(
            "error.html",
            error_title="Erreur",
            error_message=f"Erreur lors de la navigation : {str(e)}",
        ), 500


@app.route("/serve_guide")
def serve_guide():
    """Sert le guide utilisateur depuis le FileShare"""
    async_logger = get_async_logger()
    try:
        guide_path = get_guide_path()
        if guide_path and guide_path.exists():
            async_logger.info("Guide utilisateur servi", filename=guide_path.name)
            return send_file(guide_path, mimetype="application/pdf")
        else:
            async_logger.warning("Guide utilisateur non disponible")
            return "Guide non disponible", 404
    except Exception as e:
        async_logger.error("Erreur lors de la récupération du guide", error=str(e))
        return f"Erreur: {str(e)}", 500


@app.route("/admin/upload_guide", methods=["POST"])
@auth.login_required
def admin_upload_guide():
    """Upload un nouveau guide (admin uniquement)"""
    async_logger = get_async_logger()
    user_name = session.get("user_name", "Unknown")
    user_email = session.get("user_email", "unknown@example.com")

    # Vérifier les droits admin
    if user_name not in LISTE_ADMINS and user_email not in LISTE_ADMINS:
        async_logger.warning(
            "Unauthorized guide upload attempt", user=user_name, email=user_email
        )
        return jsonify({"error": "Accès non autorisé"}), 403

    if "file" not in request.files:
        return jsonify({"error": "Aucun fichier fourni"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nom de fichier vide"}), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Seuls les fichiers PDF sont acceptés"}), 400

    try:
        success, path = upload_guide(file.read(), file.filename)
        if success:
            async_logger.info(
                "Guide uploadé avec succès",
                admin_user=user_name,
                filename=file.filename,
            )
            return jsonify({"success": True, "message": "Guide uploadé avec succès"})
        else:
            async_logger.error("Erreur lors de l'upload du guide")
            return jsonify({"error": "Erreur lors de l'upload"}), 500
    except Exception as e:
        async_logger.error("Erreur lors de l'upload du guide", error=str(e))
        return jsonify({"error": str(e)}), 500


@app.route("/admin/delete_guide", methods=["POST"])
@auth.login_required
def admin_delete_guide():
    """Supprime le guide (admin uniquement)"""
    async_logger = get_async_logger()
    user_name = session.get("user_name", "Unknown")
    user_email = session.get("user_email", "unknown@example.com")

    # Vérifier les droits admin
    if user_name not in LISTE_ADMINS and user_email not in LISTE_ADMINS:
        async_logger.warning(
            "Unauthorized guide deletion attempt", user=user_name, email=user_email
        )
        return jsonify({"error": "Accès non autorisé"}), 403

    try:
        success = delete_guide()
        if success:
            async_logger.info("Guide supprimé avec succès", admin_user=user_name)
            return jsonify({"success": True, "message": "Guide supprimé avec succès"})
        else:
            async_logger.warning("Aucun guide à supprimer")
            return jsonify({"error": "Aucun guide à supprimer ou erreur"}), 400
    except Exception as e:
        async_logger.error("Erreur lors de la suppression du guide", error=str(e))
        return jsonify({"error": str(e)}), 500


@app.route("/admin_fileshare_download")
@auth.login_required
def admin_fileshare_download():
    """Télécharger un fichier depuis FileShare - Admin uniquement"""
    async_logger = get_async_logger()
    user_name = session.get("user_name", "Unknown")
    user_email = session.get("user_email", "unknown@example.com")

    # Vérifier les droits admin
    if user_name not in LISTE_ADMINS and user_email not in LISTE_ADMINS:
        async_logger.warning(
            "Unauthorized FileShare download attempt", user=user_name, email=user_email
        )
        return "Accès non autorisé", 403

    file_path = request.args.get("path", "").strip("/")
    if not file_path:
        return "Chemin de fichier manquant", 400

    try:
        from core.fonctions_fileshare import get_file_from_fileshare

        success, content = get_file_from_fileshare(file_path)

        if not success or content is None:
            async_logger.warning(
                "FileShare file not found", path=file_path, admin_user=user_name
            )
            return "Fichier non trouvé", 404

        # Déterminer le type MIME
        filename = file_path.split("/")[-1]
        if filename.endswith(".csv"):
            mimetype = "text/csv"
        elif filename.endswith(".json"):
            mimetype = "application/json"
        elif filename.endswith(".html"):
            mimetype = "text/html"
        elif filename.endswith(".log"):
            mimetype = "text/plain"
        else:
            mimetype = "application/octet-stream"

        # Convertir en bytes si nécessaire
        if isinstance(content, str):
            content = content.encode("utf-8")

        async_logger.info(
            "FileShare file downloaded",
            path=file_path,
            admin_user=user_name,
            size=len(content),
        )

        return send_file(
            io.BytesIO(content),
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename,
        )

    except Exception as e:
        async_logger.error("FileShare download error", error=str(e), path=file_path)
        return f"Erreur lors du téléchargement : {str(e)}", 500


@app.route("/admin_fileshare_delete", methods=["POST"])
@auth.login_required
def admin_fileshare_delete():
    """Supprimer un fichier/dossier depuis FileShare - Admin uniquement"""
    async_logger = get_async_logger()
    user_name = session.get("user_name", "Unknown")
    user_email = session.get("user_email", "unknown@example.com")

    # Vérifier les droits admin
    if user_name not in LISTE_ADMINS and user_email not in LISTE_ADMINS:
        async_logger.warning(
            "Unauthorized FileShare delete attempt", user=user_name, email=user_email
        )
        return jsonify({"success": False, "error": "Accès non autorisé"}), 403

    data = request.json
    file_path = data.get("path", "").strip("/")
    is_directory = data.get("is_directory", False)

    if not file_path:
        return jsonify({"success": False, "error": "Chemin manquant"}), 400

    try:
        from core.fonctions_fileshare import init_azure_fileshare_client, get_share_name

        share_service_client = init_azure_fileshare_client()
        share_name = get_share_name()
        share_client = share_service_client.get_share_client(share_name)

        if is_directory:
            dir_client = share_client.get_directory_client(file_path)
            dir_client.delete_directory()
        else:
            file_client = share_client.get_file_client(file_path)
            file_client.delete_file()

        async_logger.info(
            "FileShare item deleted",
            path=file_path,
            is_directory=is_directory,
            admin_user=user_name,
        )

        return jsonify({"success": True})

    except Exception as e:
        async_logger.error("FileShare delete error", error=str(e), path=file_path)
        return jsonify({"success": False, "error": str(e)}), 500


# ============= HEALTH & ERRORS =============


@app.route("/_stcore/health")
def health_check():
    """Health check endpoint"""
    return "OK", 200


@app.errorhandler(404)
def not_found(error):
    async_logger = get_async_logger()
    async_logger.warning(
        "404 error", path=request.path, remote_addr=request.remote_addr
    )
    return jsonify({"error": "Ressource non trouvée"}), 404


@app.errorhandler(500)
def internal_error(error):
    async_logger = get_async_logger()
    async_logger.error(
        "500 internal server error",
        error=str(error),
        path=request.path,
        remote_addr=request.remote_addr,
    )
    return "Internal Server Error", 500


@app.route("/get_ai_response", methods=["POST"])
@auth.login_required
def get_ai_response():
    """Placeholder - requiert une authentification"""
    pass


# ============= CLEANUP =============


@atexit.register
def cleanup():
    """Nettoyage à l'arrêt"""
    async_logger = get_async_logger()
    async_logger.info("Application shutdown initiated")
    shutdown_async_logger()


# Configuration du logging
azure_logger = setup_azure_optimized_logging(app)

# if __name__ == "__main__":
#     try:
#         app.run(host="0.0.0.0", port=5004, debug=False)
#         print("hello")
#     finally:
#         shutdown_async_logger()
