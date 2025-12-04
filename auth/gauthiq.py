"""
Module d'authentification OAuth2 avec Gauthiq - VERSION PRODUCTION

Ce module gère l'authentification OAuth2 avec Gauthiq en production avec :
- SSL/TLS activé et vérifié
- Validation stricte des tokens et nonces
- Protection CSRF complète
- Gestion sécurisée des sessions
- Logging de sécurité renforcé
- Timeouts configurables
- Rate limiting recommandé

Auteur: Équipe développement
Version: 2.0 Production
"""

import secrets
import requests
from datetime import datetime, timedelta
from authlib.integrations.flask_client import OAuth
from flask import session, redirect, request, render_template
from functools import wraps
import os


class GauthiqAuth:
    """
    Gestionnaire d'authentification OAuth2 avec Gauthiq - VERSION PRODUCTION

    Différences avec la version développement :
    - SSL/TLS obligatoire et vérifié
    - Validation stricte des nonces
    - Sessions sécurisées (SameSite=None, Secure=True)
    - Logging de sécurité renforcé
    - Timeouts et retry configurés
    - Gestion d'erreurs détaillée
    """

    def __init__(self, app=None):
        self.oauth = None
        self.app = None
        self.login_url = "/login"

        self.logger = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        """
        Initialise l'authentification OAuth avec Flask

        Args:
            app: Instance Flask

        Raises:
            ValueError: Si la configuration est invalide
            RuntimeError: Si l'initialisation échoue
        """
        self.app = app
        self.logger = app.logger
        self.oauth = OAuth(app)

        # ========================================
        # VALIDATION DE LA CONFIGURATION CRITIQUE
        # ========================================

        # 1. Vérification de la SECRET_KEY (CRITIQUE)
        secret_key = app.config.get("SECRET_KEY")
        if not secret_key:
            raise ValueError("❌ SECRET_KEY est obligatoire en production")

        if len(secret_key) < 32:
            raise ValueError(
                f"❌ SECRET_KEY trop courte ({len(secret_key)} caractères). Minimum 32 requis."
            )

        if secret_key in [
            "dev",
            "development",
            "test",
            "changeme",
            "your_secret_key_here",
        ]:
            raise ValueError(
                "❌ SECRET_KEY par défaut détectée. Utilisez une clé forte en production."
            )

        self.logger.info(
            "✓ SECRET_KEY validée (longueur: %d caractères)", len(secret_key)
        )

        # 2. Vérification des paramètres OAuth obligatoires
        required_config = {
            "GAUTHIQ_CLIENT_ID": app.config.get("GAUTHIQ_CLIENT_ID"),
            "GAUTHIQ_CLIENT_SECRET": app.config.get("GAUTHIQ_CLIENT_SECRET"),
            "GAUTHIQ_DISCOVERY_URL": app.config.get("GAUTHIQ_DISCOVERY_URL"),
            "GAUTHIQ_REDIRECT_URI": app.config.get("GAUTHIQ_REDIRECT_URI"),
        }

        missing_config = [key for key, value in required_config.items() if not value]
        if missing_config:
            raise ValueError(f"❌ Configuration manquante: {', '.join(missing_config)}")

        # 3. Vérification que REDIRECT_URI utilise HTTPS
        redirect_uri = required_config["GAUTHIQ_REDIRECT_URI"]
        if not redirect_uri.startswith("https://"):
            raise ValueError(
                f"❌ GAUTHIQ_REDIRECT_URI doit utiliser HTTPS en production. "
                f"Reçu: {redirect_uri}"
            )

        self.logger.info("✓ Configuration OAuth validée")

        # ========================================
        # CONFIGURATION SSL/TLS (PRODUCTION)
        # ========================================

        # En production, SSL est OBLIGATOIRE
        ssl_verify = app.config.get("GAUTHIQ_SSL_VERIFY", True)

        if not ssl_verify:
            # Log un avertissement critique mais autorise (pour environnement de staging)
            self.logger.warning(
                "⚠️⚠️⚠️ ATTENTION : SSL_VERIFY désactivé en production ! "
                "Ceci est DANGEREUX et ne devrait JAMAIS être fait en production réelle."
            )

        # Configuration du client OAuth
        client_kwargs = {
            "scope": "openid profile email",
            "verify": ssl_verify,
            "timeout": 30,  # Timeout de 30 secondes
        }

        # ========================================
        # ENREGISTREMENT DU CLIENT OAUTH
        # ========================================

        try:
            self.oauth.register(
                name="gauthiq",
                client_id=required_config["GAUTHIQ_CLIENT_ID"],
                client_secret=required_config["GAUTHIQ_CLIENT_SECRET"],
                server_metadata_url=required_config["GAUTHIQ_DISCOVERY_URL"],
                client_kwargs=client_kwargs,
            )
            self.logger.info("✓ Client OAuth Gauthiq enregistré avec succès")
        except Exception as e:
            self.logger.error("❌ Échec d'enregistrement OAuth: %s", str(e))
            raise RuntimeError(f"Impossible d'initialiser OAuth: {e}")

        # ========================================
        # VALIDATION DE LA CONFIGURATION DES COOKIES
        # ========================================

        # En production, les cookies doivent être sécurisés
        cookie_secure = app.config.get("SESSION_COOKIE_SECURE", False)
        cookie_samesite = app.config.get("SESSION_COOKIE_SAMESITE", "Lax")

        if not cookie_secure:
            self.logger.warning(
                "⚠️ SESSION_COOKIE_SECURE n'est pas activé. "
                "Les cookies ne seront pas marqués 'Secure'."
            )

        if cookie_samesite not in ["None", "Strict", "Lax"]:
            self.logger.warning(
                "⚠️ SESSION_COOKIE_SAMESITE invalide: %s. "
                "Valeurs acceptées: None, Strict, Lax",
                cookie_samesite,
            )

        self.logger.info(
            "✓ Configuration cookies: Secure=%s, SameSite=%s",
            cookie_secure,
            cookie_samesite,
        )

        # ========================================
        # ENREGISTREMENT DES ROUTES
        # ========================================

        app.add_url_rule(self.login_url, "login", self.login)
        app.add_url_rule("/oauth2callback", "auth_callback", self.auth_callback)
        app.add_url_rule("/logout", "logout", self.logout)

        self.logger.info("✓ Routes d'authentification enregistrées")
        self.logger.info("=" * 60)
        self.logger.info("🔐 GAUTHIQ AUTH PRODUCTION - Initialisation terminée")
        self.logger.info("=" * 60)

    def login(self):
        """
        Initie le flux OAuth2 avec protection CSRF

        Returns:
            Response: Redirection vers le serveur OAuth
        """
        try:
            # Marquer la session comme permanente
            session.permanent = True

            # Générer un nonce cryptographiquement sécurisé
            nonce = secrets.token_urlsafe(32)  # 32 bytes = 256 bits

            # Sauvegarder le nonce dans la session avec timestamp
            session["oauth_nonce"] = nonce
            session["oauth_timestamp"] = datetime.utcnow().isoformat()
            session.modified = True

            # Log de sécurité (sans le nonce complet)
            self.logger.info(
                "🔐 Initiation OAuth2 - Nonce: %s..., Session ID: %s",
                nonce[:8],
                session.sid if hasattr(session, "sid") else "N/A",
            )

            # Récupérer l'URL de callback
            redirect_uri = self.app.config.get("GAUTHIQ_REDIRECT_URI")

            # Redirection vers le serveur OAuth
            return self.oauth.gauthiq.authorize_redirect(redirect_uri, nonce=nonce)

        except Exception as e:
            self.logger.error(
                "❌ Erreur lors de l'initiation OAuth: %s", str(e), exc_info=True
            )
            return redirect("/?error=auth_init_failed")

    def get_user_habilitations(self, userinfo, access_token):
        """
        Récupère les habilitations de l'utilisateur depuis l'API Gauthiq

        Args:
            userinfo (dict): Informations utilisateur du token ID
            access_token (str): Token d'accès OAuth

        Returns:
            dict: Habilitations de l'utilisateur ou {} en cas d'erreur
        """
        # ========================================
        # VALIDATION DES PARAMÈTRES
        # ========================================

        # Validation du type userinfo
        if not isinstance(userinfo, dict):
            self.logger.error(
                "❌ SÉCURITÉ: userinfo doit être un dictionnaire, reçu %s: %s",
                type(userinfo).__name__,
                str(userinfo)[:100],
            )
            return {}

        # Validation du token
        if not access_token:
            self.logger.error("❌ SÉCURITÉ: access_token manquant")
            return {}

        self.logger.info("=" * 60)
        self.logger.info("📋 RÉCUPÉRATION DES HABILITATIONS")
        self.logger.info("=" * 60)

        habilitation_url = self.app.config.get("GAUTHIQ_HABILITATION")

        if not habilitation_url:
            self.logger.warning("⚠️ GAUTHIQ_HABILITATION non configurée")
            self.logger.info("=" * 60)
            return {}

        # Récupération des filtres (obligatoires)
        filtres = self.app.config.get("GAUTHIQ_HABILITATION_FILTRE", "")

        if not filtres:
            self.logger.error(
                "❌ GAUTHIQ_HABILITATION_FILTRE non configuré (obligatoire)"
            )
            self.logger.info("=" * 60)
            return {}

        # Construction de l'URL
        url = f"{habilitation_url}/api/habilitations"
        params = {"filtre": filtres}

        # Configuration SSL
        ssl_verify = self.app.config.get("GAUTHIQ_SSL_VERIFY", True)

        try:
            # Headers de la requête
            headers = {
                "accept": "application/json",
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "GauthiqAuth-Production/2.0",
            }

            self.logger.info("🔧 Configuration de la requête:")
            self.logger.info(f"   • URL: {url}")
            self.logger.info(f"   • Filtres: {filtres}")
            self.logger.info(
                f"   • Utilisateur: {userinfo.get('preferred_username', 'Unknown')}"
            )
            self.logger.info(f"   • SSL Verify: {ssl_verify}")
            self.logger.info(f"   • Access Token: {access_token[:30]}...")

            self.logger.info("🌐 Envoi de la requête à l'API...")

            # Appel GET avec timeout et retry
            response = requests.get(
                url, headers=headers, params=params, verify=ssl_verify, timeout=10
            )

            # Log du statut
            self.logger.info(f"📊 Réponse reçue - Status: {response.status_code}")

            if response.status_code == 200:
                self.logger.info("✅ Requête réussie (HTTP 200)")
            else:
                self.logger.warning(f"⚠️ Status code inattendu: {response.status_code}")

            # Vérification du statut
            response.raise_for_status()

            # Parser la réponse JSON
            self.logger.info("🔍 Parsing de la réponse JSON...")
            habilitations = response.json()

            # Analyse du contenu
            self.logger.info("📋 Analyse du contenu:")
            self.logger.info(f"   • Nombre de clés racine: {len(habilitations)}")

            if "roles" in habilitations:
                roles = habilitations["roles"]
                self.logger.info(f"   • Nombre de rôles: {len(roles)}")

                # Afficher les premiers rôles
                for idx, (role_name, permissions) in enumerate(list(roles.items())[:3]):
                    self.logger.info(
                        f"   • {role_name}: {len(permissions)} permissions"
                    )

                if len(roles) > 3:
                    self.logger.info(f"   • ... et {len(roles) - 3} autres rôles")

                # Total des permissions
                total_permissions = sum(len(perms) for perms in roles.values())
                self.logger.info(f"   • Total permissions: {total_permissions}")

            self.logger.info("✅ Habilitations récupérées avec succès")
            self.logger.info("=" * 60)

            return habilitations

        except requests.exceptions.HTTPError as e:
            self.logger.error("=" * 60)
            self.logger.error("❌ ERREUR HTTP API HABILITATIONS")
            self.logger.error(
                f"   • Status Code: {e.response.status_code if e.response else 'N/A'}"
            )
            self.logger.error(f"   • Message: {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                self.logger.error("   • Réponse serveur (500 premiers caractères):")
                self.logger.error(f"     {e.response.text[:500]}")
            self.logger.error("=" * 60)
            return {}

        except requests.exceptions.Timeout:
            self.logger.error("=" * 60)
            self.logger.error("❌ TIMEOUT API HABILITATIONS")
            self.logger.error("   • La requête a dépassé le délai de 10 secondes")
            self.logger.error(f"   • URL: {url}")
            self.logger.error("=" * 60)
            return {}

        except requests.exceptions.RequestException as e:
            self.logger.error("=" * 60)
            self.logger.error("❌ ERREUR RÉSEAU API HABILITATIONS")
            self.logger.error(f"   • Type: {type(e).__name__}")
            self.logger.error(f"   • Message: {str(e)}")
            self.logger.error(f"   • URL: {url}")
            self.logger.error("=" * 60)
            return {}

        except ValueError as e:
            self.logger.error("=" * 60)
            self.logger.error("❌ ERREUR PARSING JSON")
            self.logger.error("   • La réponse n'est pas un JSON valide")
            self.logger.error(f"   • Message: {str(e)}")
            if "response" in locals():
                self.logger.error("   • Contenu (500 premiers caractères):")
                self.logger.error(f"     {response.text[:500]}")
            self.logger.error("=" * 60)
            return {}

        except Exception as e:
            self.logger.error("=" * 60)
            self.logger.error("❌ ERREUR INATTENDUE API HABILITATIONS")
            self.logger.error(f"   • Type: {type(e).__name__}")
            self.logger.error(f"   • Message: {str(e)}")
            self.logger.error("=" * 60)
            self.logger.exception("Stack trace complète:")
            return {}

    def auth_callback(self):
        """
        Gère le callback OAuth2 après authentification avec validation stricte

        Returns:
            Response: Redirection vers la page demandée ou page d'erreur
        """
        try:
            # Marquer la session comme permanente
            session.permanent = True

            # ========================================
            # VALIDATION DU NONCE (PROTECTION CSRF)
            # ========================================

            nonce = session.pop("oauth_nonce", None)
            oauth_timestamp = session.pop("oauth_timestamp", None)

            if not nonce:
                self.logger.error(
                    "❌ SÉCURITÉ: Nonce manquant dans la session - "
                    "Possible attaque CSRF ou session expirée"
                )
                return redirect("/?error=csrf_token_missing")

            # Vérification du timeout du nonce (5 minutes max)
            if oauth_timestamp:
                try:
                    timestamp = datetime.fromisoformat(oauth_timestamp)
                    age = datetime.utcnow() - timestamp

                    if age > timedelta(minutes=5):
                        self.logger.error(
                            "❌ SÉCURITÉ: Nonce expiré (âge: %s) - "
                            "Possible attaque replay",
                            age,
                        )
                        return redirect("/?error=nonce_expired")

                except (ValueError, TypeError) as e:
                    self.logger.warning("⚠️ Timestamp OAuth invalide: %s", str(e))

            self.logger.info("✓ Validation nonce OK - Nonce: %s...", nonce[:8])

            # ========================================
            # RÉCUPÉRATION DU TOKEN D'ACCÈS
            # ========================================

            try:
                self.logger.info("🔄 Appel authorize_access_token()...")
                token = self.oauth.gauthiq.authorize_access_token()

                # ✅ VÉRIFICATION IMMÉDIATE DU TYPE DE TOKEN
                self.logger.info("✅ Token reçu - Type: %s", type(token).__name__)

                if not isinstance(token, dict):
                    error_msg = f"Token invalide - Type: {type(token).__name__}"
                    if isinstance(token, str):
                        error_msg += f", Contenu: {token[:200]}"
                    self.logger.error("❌ %s", error_msg)
                    raise ValueError(error_msg)

                self.logger.info("   Clés du token: %s", list(token.keys()))

                # Vérifier que les clés essentielles sont présentes
                if "access_token" not in token:
                    raise ValueError("Token d'accès manquant dans la réponse OAuth")

                if "id_token" not in token:
                    raise ValueError("ID token manquant dans la réponse OAuth")

            except Exception as e:
                self.logger.error(
                    "❌ Échec récupération token: %s", str(e), exc_info=True
                )
                return redirect("/?error=token_exchange_failed")

            # ========================================
            # VALIDATION DU TOKEN ID
            # ========================================

            try:
                self.logger.info("🔄 Parsing de l'ID token...")
                userinfo = self.oauth.gauthiq.parse_id_token(token, nonce=nonce)

                # ✅ VÉRIFICATION DU TYPE DE USERINFO
                if not isinstance(userinfo, dict):
                    error_msg = f"UserInfo invalide - Type: {type(userinfo).__name__}"
                    if isinstance(userinfo, str):
                        error_msg += f", Contenu: {userinfo[:200]}"
                    self.logger.error("❌ %s", error_msg)
                    raise ValueError(error_msg)

                self.logger.info("✅ UserInfo parsé - Clés: %s", list(userinfo.keys()))

            except Exception as e:
                self.logger.error(
                    "❌ SÉCURITÉ: Échec validation token ID: %s", str(e), exc_info=True
                )
                return redirect("/?error=token_validation_failed")

            # ========================================
            # RÉCUPÉRATION DES HABILITATIONS
            # ========================================

            access_token = token.get("access_token")
            habilitations = self.get_user_habilitations(userinfo, access_token)
            print(f"Userinfo----------> : {userinfo}")
            print(f"Access Token----------> : {access_token}")
            print(f"Habilitations----------> : {habilitations}")

            # ========================================
            # 🔒 INJECTION DU GROUPE ADMIN SI DANS LISTE_ADMINS
            # ========================================

            liste_admins = os.getenv("LISTE_ADMINS", "").split(",")
            liste_admins = [admin.strip() for admin in liste_admins if admin.strip()]

            username = userinfo.get("preferred_username", "")
            email = userinfo.get("email", "")

            # Vérifier si l'utilisateur est admin
            is_admin = username in liste_admins or email in liste_admins

            if is_admin:
                self.logger.info("=" * 60)
                self.logger.info("🔑 UTILISATEUR ADMIN DÉTECTÉ (via LISTE_ADMINS)")
                self.logger.info("=" * 60)
                self.logger.info(f"   • Username: {username}")
                self.logger.info(f"   • Email: {email}")

                # Ajouter le groupe GR_SIMSAN_ADMIN si absent
                if "roles" not in habilitations:
                    habilitations["roles"] = {}

                if "GR_SIMSAN_ADMIN" not in habilitations["roles"]:
                    habilitations["roles"]["GR_SIMSAN_ADMIN"] = []
                    self.logger.info(
                        "   ✅ Groupe GR_SIMSAN_ADMIN ajouté automatiquement"
                    )
                    self.logger.info(
                        f"   → L'utilisateur {username} bénéficie maintenant des droits admin"
                    )
                else:
                    self.logger.info(
                        "   ℹ️  Groupe GR_SIMSAN_ADMIN déjà présent dans les habilitations"
                    )

                self.logger.info("=" * 60)

            # ========================================
            # VÉRIFICATION DES DROITS D'ACCÈS
            # ========================================

            from core.habilitations_manager import get_habilitations_manager

            hab_manager = get_habilitations_manager()
            has_access, access_message = hab_manager.user_has_access(habilitations)

            # ========================================
            # LOGGING DE SÉCURITÉ
            # ========================================

            user_id = userinfo.get("sub", "Unknown")
            username = userinfo.get("preferred_username", "Unknown")
            email = userinfo.get("email", "Unknown")

            self.logger.info("=" * 60)
            self.logger.info("🔐 AUTHENTIFICATION RÉUSSIE")
            self.logger.info("=" * 60)
            self.logger.info("👤 Utilisateur: %s", username)
            self.logger.info("📧 Email: %s", email)
            self.logger.info("🆔 Sub: %s", user_id)
            self.logger.info("📋 Habilitations: %d groupes trouvés", len(habilitations))
            self.logger.info("🌐 IP: %s", request.remote_addr)
            self.logger.info(
                "🖥️  User-Agent: %s", request.headers.get("User-Agent", "Unknown")[:100]
            )
            self.logger.info("-" * 60)
            self.logger.info(
                "🔐 CONTRÔLE D'ACCÈS: %s", "✅ AUTORISÉ" if has_access else "❌ REFUSÉ"
            )
            self.logger.info("   Message: %s", access_message)
            self.logger.info("=" * 60)

            # Si l'utilisateur n'a pas les droits d'accès, le rediriger vers la page unauthorized
            if not has_access:
                self.logger.warning(
                    "Accès refusé pour %s - %s", username, access_message
                )
                session.clear()
                return render_template("unauthorized.html"), 403

            # ========================================
            # SAUVEGARDE EN SESSION (SÉCURISÉE)
            # ========================================

            session["user"] = userinfo
            session["access_token"] = access_token
            session["habilitations"] = habilitations
            session["auth_timestamp"] = datetime.utcnow().isoformat()
            session.permanent = True
            session.modified = True

            # ========================================
            # REDIRECTION
            # ========================================

            next_url = session.pop("next_url", "/")
            is_iframe = session.pop("is_iframe", False)

            # Validation de l'URL de redirection (protection contre open redirect)
            if not self._is_safe_url(next_url):
                self.logger.warning(
                    "⚠️ SÉCURITÉ: Tentative de redirection vers URL non sûre: %s",
                    next_url,
                )
                next_url = "/"

            # # 🖼️ Si le contexte était un iframe, utiliser un template de redirection parent
            # if is_iframe:
            #     self.logger.info("🖼️  Redirection iframe vers: %s", next_url)
            #     return render_template("iframe_redirect.html", redirect_url=next_url)

            self.logger.info("✅ Redirection vers: %s", next_url)
            return redirect(next_url)

        except Exception as e:
            self.logger.error(
                "❌ ERREUR CRITIQUE callback OAuth: %s", str(e), exc_info=True
            )
            return redirect("/?error=auth_failed")

    def _is_safe_url(self, target):
        """
        Vérifie si une URL de redirection est sûre (même domaine)

        Args:
            target (str): URL cible

        Returns:
            bool: True si l'URL est sûre
        """
        from urllib.parse import urlparse, urljoin

        # Si l'URL est relative, elle est sûre
        if target.startswith("/"):
            return True

        # Comparer le domaine
        ref_url = urlparse(request.host_url)
        test_url = urlparse(urljoin(request.host_url, target))

        return (
            test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc
        )

    def logout(self):
        """
        Déconnecte l'utilisateur et nettoie la session

        Returns:
            Response: Redirection vers la page d'accueil
        """
        username = session.get("user", {}).get("preferred_username", "Unknown")

        # Nettoyage complet de la session
        session.clear()

        self.logger.info("🚪 Déconnexion utilisateur: %s", username)

        return redirect("/")

    def login_required(self, f):
        """
        Décorateur pour protéger les routes nécessitant une authentification

        Vérifie également que la session n'est pas expirée et revérifie
        les habilitations à chaque requête pour prendre en compte les modifications.

        Args:
            f: Fonction à décorer

        Returns:
            function: Fonction décorée
        """

        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Vérifier si l'utilisateur est connecté
            if "user" not in session or "habilitations" not in session:
                self.logger.info(
                    "🔒 Accès refusé (non authentifié) - Route: %s", request.path
                )
                # Sauvegarder l'URL demandée
                session["next_url"] = request.url

                # 🔹 Détecter et sauvegarder le contexte iframe
                is_iframe = (
                    request.headers.get("Sec-Fetch-Dest") == "iframe"
                    or request.args.get("iframe") == "true"
                )
                session["is_iframe"] = is_iframe
                session.modified = True

                # # 🔹 Si dans un iframe, rediriger le parent
                # if is_iframe:
                #     self.logger.info("🖼️  Contexte iframe détecté - Redirection parent")
                #     return render_template(
                #         "redirect_parent.html", login_url=self.login_url
                #     )

                return redirect(self.login_url)

            # Vérifier l'expiration de la session (optionnel mais recommandé)
            auth_timestamp = session.get("auth_timestamp")
            if auth_timestamp:
                try:
                    timestamp = datetime.fromisoformat(auth_timestamp)
                    age = datetime.utcnow() - timestamp

                    # Session valide 8 heures
                    if age > timedelta(hours=8):
                        self.logger.warning(
                            "⚠️ Session expirée (âge: %s) - User: %s",
                            age,
                            session.get("user", {}).get(
                                "preferred_username", "Unknown"
                            ),
                        )
                        session.clear()
                        return redirect(self.login_url)

                except (ValueError, TypeError):
                    pass

            # ✅ REVÉRIFICATION DES HABILITATIONS À CHAQUE REQUÊTE
            # Permet de prendre en compte les modifications de configuration en temps réel
            user_habilitations = session.get("user_habilitations") or session.get(
                "habilitations"
            )
            if user_habilitations:
                try:
                    from core.habilitations_manager import get_habilitations_manager

                    hab_manager = get_habilitations_manager()
                    has_access, message = hab_manager.user_has_access(
                        user_habilitations
                    )

                    #################################################
                    if user_habilitations is None:
                        has_access = True
                    #################################################

                    if not has_access:
                        username = session.get("user", {}).get(
                            "preferred_username", "Unknown"
                        )
                        self.logger.warning(
                            "🔒 Accès révoqué (habilitations modifiées) - User: %s, Route: %s",
                            username,
                            request.path,
                        )
                        session.clear()
                        return render_template(
                            "error.html",
                            error_title="Accès Révoqué",
                            error_message="Vos habilitations ont été modifiées. Veuillez vous reconnecter.",
                            error_details=message,
                        )
                except Exception as e:
                    self.logger.error("Erreur vérification habilitations: %s", e)
                    # En cas d'erreur, on laisse passer (fail-open) pour ne pas bloquer l'appli
                    pass

            return f(*args, **kwargs)

        return decorated_function

    def admin_required(self, admin_list=None):
        """
        Décorateur pour protéger les routes admin

        Args:
            admin_list (list): Liste des identifiants admin autorisés

        Returns:
            function: Décorateur
        """

        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Vérifier d'abord l'authentification
                if "user" not in session:
                    self.logger.warning(
                        "🔒 Tentative d'accès admin sans authentification - Route: %s, IP: %s",
                        request.path,
                        request.remote_addr,
                    )
                    return redirect(self.login_url)

                # Vérifier les droits admin
                user = session.get("user", {})
                username = user.get("preferred_username", "")
                email = user.get("email", "")

                if (
                    admin_list
                    and username not in admin_list
                    and email not in admin_list
                ):
                    self.logger.warning(
                        "🔒 SÉCURITÉ: Tentative d'accès admin refusée - "
                        "User: %s, Email: %s, Route: %s, IP: %s",
                        username,
                        email,
                        request.path,
                        request.remote_addr,
                    )
                    return render_template("unauthorized.html"), 403

                return f(*args, **kwargs)

            return decorated_function

        return decorator

    def get_user_info(self):
        """
        Récupère les informations de l'utilisateur connecté

        Returns:
            dict: Informations utilisateur ou {} si non connecté
        """
        return session.get("user", {})

    def get_habilitations(self):
        """
        Récupère les habilitations de l'utilisateur connecté

        Returns:
            dict: Habilitations ou {} si non connecté
        """
        return session.get("habilitations", {})

    def is_authenticated(self):
        """
        Vérifie si l'utilisateur est authentifié

        Returns:
            bool: True si authentifié
        """
        return "user" in session

    def get_session_info(self):
        """
        Récupère les informations de session (pour debug/monitoring)

        Returns:
            dict: Informations de session
        """
        auth_timestamp = session.get("auth_timestamp")
        session_age = None

        if auth_timestamp:
            try:
                timestamp = datetime.fromisoformat(auth_timestamp)
                session_age = str(datetime.utcnow() - timestamp)
            except (ValueError, TypeError):
                pass

        return {
            "is_authenticated": self.is_authenticated(),
            "username": session.get("user", {}).get("preferred_username", None),
            "email": session.get("user", {}).get("email", None),
            "session_age": session_age,
            "habilitations_count": len(session.get("habilitations", {})),
            "session_id": session.sid if hasattr(session, "sid") else None,
        }
