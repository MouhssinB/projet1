import urllib3
import secrets
import requests
from datetime import datetime
from authlib.integrations.flask_client import OAuth
from flask import session, redirect, request, render_template
from functools import wraps
import os


class GauthiqAuth:
    """Gestionnaire d'authentification OAuth2 avec Gauthiq"""

    def __init__(self, app=None):
        self.oauth = None
        self.login_url = "/login"
        self.app = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize l'authentification OAuth avec Flask"""
        self.app = app
        self.oauth = OAuth(app)

        # Vérification de la SECRET_KEY
        if not app.config.get("SECRET_KEY") or app.config["SECRET_KEY"] == "dev":
            app.logger.error(
                "⚠️ SECRET_KEY manquante ou faible ! Cela causera des problèmes de session."
            )

        # Configuration SSL
        ssl_verify = app.config.get("GAUTHIQ_SSL_VERIFY", False)
        client_kwargs = {"scope": "openid profile email"}

        if not ssl_verify:
            client_kwargs["verify"] = False
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            app.logger.warning(
                "⚠️ Vérification SSL désactivée (non recommandé en production)"
            )

        # Enregistrement du client OAuth
        try:
            self.oauth.register(
                name="gauthiq",
                client_id=app.config["GAUTHIQ_CLIENT_ID"],
                client_secret=app.config["GAUTHIQ_CLIENT_SECRET"],
                server_metadata_url=app.config["GAUTHIQ_DISCOVERY_URL"],
                client_kwargs=client_kwargs,
            )
            app.logger.info("✓ Client OAuth Gauthiq enregistré")
        except Exception as e:
            app.logger.error(f"✗ Échec d'enregistrement OAuth: {e}")
            raise

        # Enregistrement des routes
        app.add_url_rule(self.login_url, "login", self.login)
        app.add_url_rule("/oauth2callback", "auth_callback", self.auth_callback)
        app.add_url_rule("/logout", "logout", self.logout)

    def login(self):
        """Initie le flux OAuth2"""
        # S'assurer que la session est persistante
        session.permanent = True

        # Debug : afficher les informations de session AVANT
        print("=" * 60)
        print("🔐 DÉBUT DU PROCESSUS DE LOGIN")
        print("=" * 60)
        print(f"Session ID: {session.get('_id', 'NO SESSION ID')}")
        print(f"Session SID: {session.sid if hasattr(session, 'sid') else 'NO SID'}")
        print(f"Session keys AVANT: {list(session.keys())}")
        print(
            f"Cookie config: SameSite={self.app.config.get('SESSION_COOKIE_SAMESITE')}, Secure={self.app.config.get('SESSION_COOKIE_SECURE')}"
        )

        redirect_uri = self.app.config.get("GAUTHIQ_REDIRECT_URI")
        nonce = secrets.token_urlsafe(16)
        print(f"Generated nonce: {nonce}")

        # SOLUTION : Encoder le nonce dans le state OAuth au lieu de la session
        # Le state sera renvoyé par le serveur OAuth
        state_data = {"nonce": nonce, "timestamp": datetime.now().isoformat()}

        # Sauvegarder quand même dans la session pour double vérification
        session["oauth_nonce"] = nonce
        session["test_value"] = "test_session_persistence"
        session.modified = True
        session.permanent = True

        print(f"Nonce créé: {nonce[:8]}...")
        print(f"Session keys APRÈS: {list(session.keys())}")
        print(f"Redirect URI: {redirect_uri}")
        print("=" * 60)

        try:
            # Passer le nonce via state (backup si session perdue)
            # Ne PAS laisser Authlib gérer le state automatiquement
            return self.oauth.gauthiq.authorize_redirect(
                redirect_uri,
                nonce=nonce,
                # On ne passe PAS de state personnalisé ici
                # Authlib va gérer son propre state
            )
        except Exception as e:
            self.app.logger.error(f"Erreur lors de l'initiation OAuth: {e}")
            import traceback

            self.app.logger.error(traceback.format_exc())
            return redirect("/")

    def get_user_habilitations(self, userinfo, access_token):
        """
        Récupère les habilitations de l'utilisateur depuis l'API Gauthiq

        Args:
            userinfo: Informations utilisateur du token ID (doit être un dict)
            access_token: Token d'accès OAuth

        Returns:
            dict: Habilitations de l'utilisateur ou {} en cas d'erreur
        """
        # Validation des paramètres
        if not isinstance(userinfo, dict):
            self.app.logger.error(
                f"❌ userinfo doit être un dictionnaire, reçu {type(userinfo).__name__}: {str(userinfo)[:100]}"
            )
            return {}

        if not access_token:
            self.app.logger.error("❌ access_token manquant")
            return {}

        habilitation_url = self.app.config.get("GAUTHIQ_HABILITATION")

        if not habilitation_url:
            self.app.logger.warning("⚠️ GAUTHIQ_HABILITATION non configurée")
            return {}

        # Récupération des filtres (obligatoires)
        filtres = self.app.config.get("GAUTHIQ_HABILITATION_FILTRE", "")

        if not filtres:
            self.app.logger.error(
                "✗ GAUTHIQ_HABILITATION_FILTRE non configuré (obligatoire)"
            )
            return {}

        # Construction de l'URL complète avec les paramètres
        # Format: https://svc-habilitation-gauthiq-d.caas-nonprod.intra.groupama.fr/api/habilitations
        url = f"{habilitation_url}/api/habilitations"

        # Les filtres doivent être encodés dans l'URL comme dans le curl
        # Exemple: filtre=GR_SMS,LAVANDE:GR_DTRH
        params = {"filtre": filtres}

        # Configuration SSL
        ssl_verify = self.app.config.get("GAUTHIQ_SSL_VERIFY", False)

        try:
            # Headers exactement comme dans le curl fonctionnel
            headers = {
                "accept": "application/json",
                "Authorization": f"Bearer {access_token}",
            }

            print("=" * 60)
            print("📋 APPEL API HABILITATIONS")
            print("=" * 60)
            print(f"URL: {url}")
            print(f"Filtres: {filtres}")
            print(
                f"Access Token (début): {access_token[:50]}..."
                if access_token
                else "Token absent"
            )
            print(
                f"Token complet dans header: Bearer : ****    {access_token}      ****"
            )
            print(f"SSL Verify: {ssl_verify}")
            print("=" * 60)

            # Appel GET avec les mêmes paramètres que le curl
            response = requests.get(
                url, headers=headers, params=params, verify=ssl_verify, timeout=10
            )

            # Affichage de la réponse pour debug
            print(f"📊 Status Code: {response.status_code}")
            print(f"📊 Response Headers: {dict(response.headers)}")

            # Vérifier le statut de la réponse
            response.raise_for_status()

            # Parser la réponse JSON
            habilitations = response.json()

            print("=" * 60)
            print("✅ HABILITATIONS RÉCUPÉRÉES")
            print("=" * 60)
            print(f"Nombre de clés: {len(habilitations)}")
            print(f"Contenu: {habilitations}")
            print("=" * 60)

            return habilitations

        except requests.exceptions.HTTPError as e:
            self.app.logger.error(
                f"✗ Erreur HTTP lors de la récupération des habilitations: {e}"
            )
            self.app.logger.error(
                f"✗ Status Code: {e.response.status_code if e.response else 'N/A'}"
            )
            if hasattr(e, "response") and e.response is not None:
                self.app.logger.error(f"✗ Réponse serveur: {e.response.text}")
            return {}
        except requests.exceptions.RequestException as e:
            self.app.logger.error(
                f"✗ Erreur réseau lors de la récupération des habilitations: {e}"
            )
            return {}
        except ValueError as e:
            self.app.logger.error(f"✗ Erreur de parsing JSON: {e}")
            self.app.logger.error(
                f"✗ Réponse reçue: {response.text if 'response' in locals() else 'N/A'}"
            )
            return {}
        except Exception as e:
            self.app.logger.error(
                f"✗ Erreur inattendue lors de la récupération des habilitations: {e}"
            )
            import traceback

            self.app.logger.error(traceback.format_exc())
            return {}

    def auth_callback(self):
        """Gère le callback OAuth2 après authentification"""
        session.permanent = True

        # Debug : afficher les informations de session AU CALLBACK
        print("=" * 60)
        print("🔄 CALLBACK OAUTH2 REÇU")
        print("=" * 60)
        print(f"Session ID: {session.get('_id', 'NO SESSION ID')}")
        print(f"Session SID: {session.sid if hasattr(session, 'sid') else 'NO SID'}")
        print(f"Session keys: {list(session.keys())}")
        print(f"Test value from session: {session.get('test_value', 'ABSENT')}")
        print(
            f"Nonce in session: {'PRÉSENT' if 'oauth_nonce' in session else 'ABSENT'}"
        )
        print(f"Callback params: {dict(request.args)}")
        print(f"Cookies reçus: {list(request.cookies.keys())}")
        if "simsan_session" in request.cookies:
            print(f"Cookie simsan_session: {request.cookies['simsan_session'][:20]}...")
        print("=" * 60)

        # Diagnostic : vérifier si la session est persistante
        session_persistent = "test_value" in session

        if not session_persistent:
            self.app.logger.warning(
                "⚠️ Session non persistante - Tentative de récupération..."
            )
            print("⚠️ Session perdue - Tentative de workaround")

        try:
            # Récupérer le state OAuth pour le workaround si nécessaire
            state = request.args.get("state")

            # Si la session est perdue, on doit injecter le state AVANT l'appel
            if not session_persistent and state:
                # Authlib cherche une clé spécifique dans la session
                session[f"_state_gauthiq_{state}"] = state
                session.modified = True
                print(f"🔄 State injecté dans session: {state}")

            # Appel à authorize_access_token - PEUT LEVER UNE EXCEPTION
            print("🔄 Appel authorize_access_token()...")
            token = self.oauth.gauthiq.authorize_access_token()

            # ✅ VÉRIFICATION IMMÉDIATE DU TYPE DE TOKEN
            print(f"✅ Token reçu - Type: {type(token).__name__}")

            if not isinstance(token, dict):
                error_msg = f"Token invalide - Type: {type(token).__name__}"
                if isinstance(token, str):
                    error_msg += f", Contenu: {token[:200]}"
                self.app.logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)

            print(f"   Clés du token: {list(token.keys())}")

            # Vérifier que les clés essentielles sont présentes
            if "access_token" not in token:
                raise ValueError("Token d'accès manquant dans la réponse OAuth")

            if "id_token" not in token:
                raise ValueError("ID token manquant dans la réponse OAuth")

            # Récupération du nonce
            nonce = session.pop("oauth_nonce", None)

            if not nonce:
                # FALLBACK : nonce de secours (UNIQUEMENT pour développement HTTP)
                self.app.logger.warning(
                    "⚠️ Nonce perdu - Génération d'un nonce de secours"
                )
                nonce = secrets.token_urlsafe(16)
                print(f"⚠️ FALLBACK : Nonce de secours : {nonce[:8]}...")
            else:
                print(f"✅ Nonce récupéré : {nonce[:8]}...")

            # Parse l'ID token pour obtenir les infos utilisateur
            print("🔄 Parsing de l'ID token...")
            userinfo = self.oauth.gauthiq.parse_id_token(token, nonce=nonce)

            # ✅ VÉRIFICATION DU TYPE DE USERINFO
            if not isinstance(userinfo, dict):
                error_msg = f"UserInfo invalide - Type: {type(userinfo).__name__}"
                if isinstance(userinfo, str):
                    error_msg += f", Contenu: {userinfo[:200]}"
                self.app.logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)

            print(f"✅ UserInfo parsé - Clés: {list(userinfo.keys())}")

            # Récupération du token d'accès
            access_token = token.get("access_token")

            # === RÉCUPÉRATION DES HABILITATIONS ===
            habilitations = self.get_user_habilitations(userinfo, access_token)

            # 🔒 INJECTION DU GROUPE ADMIN SI L'UTILISATEUR EST DANS LISTE_ADMINS

            liste_admins = os.getenv("LISTE_ADMINS", "").split(",")
            liste_admins = [admin.strip() for admin in liste_admins if admin.strip()]

            username = userinfo.get("preferred_username", "")
            email = userinfo.get("email", "")

            # Vérifier si l'utilisateur est admin
            is_admin = username in liste_admins or email in liste_admins

            if is_admin:
                self.app.logger.info("=" * 60)
                self.app.logger.info("🔑 UTILISATEUR ADMIN DÉTECTÉ")
                self.app.logger.info(f"   Username: {username}")
                self.app.logger.info(f"   Email: {email}")

                # Ajouter le groupe GR_SIMSAN_ADMIN si absent
                if "roles" not in habilitations:
                    habilitations["roles"] = {}

                if "GR_SIMSAN_ADMIN" not in habilitations["roles"]:
                    habilitations["roles"]["GR_SIMSAN_ADMIN"] = []
                    self.app.logger.info(
                        "   ✅ Groupe GR_SIMSAN_ADMIN ajouté automatiquement"
                    )
                else:
                    self.app.logger.info("   ℹ️  Groupe GR_SIMSAN_ADMIN déjà présent")

                self.app.logger.info("=" * 60)

            # === VÉRIFICATION DES DROITS D'ACCÈS ===
            from core.habilitations_manager import get_habilitations_manager

            hab_manager = get_habilitations_manager()
            has_access, access_message = hab_manager.user_has_access(habilitations)

            # Affichage des résultats
            print("=" * 60)
            print("🔐 AUTHENTIFICATION RÉUSSIE")
            print("=" * 60)
            print(f"👤 Utilisateur: {userinfo.get('preferred_username', 'N/A')}")
            print(f"📧 Email: {userinfo.get('email', 'N/A')}")
            print(f"🆔 Sub: {userinfo.get('sub', 'N/A')}")
            print("-" * 60)
            print("📋 HABILITATIONS:")

            if habilitations:
                for key, value in habilitations.items():
                    if isinstance(value, list):
                        print(f"  • {key}: {', '.join(map(str, value))}")
                    else:
                        print(f"  • {key}: {value}")
            else:
                print("  ⚠️ Aucune habilitation trouvée")

            print("-" * 60)
            print(
                f"🔐 CONTRÔLE D'ACCÈS: {'✅ AUTORISÉ' if has_access else '❌ REFUSÉ'}"
            )
            print(f"   Message: {access_message}")
            print("=" * 60)

            # Vérification des droits
            if not has_access:
                self.app.logger.warning(
                    f"Accès refusé pour {userinfo.get('preferred_username', 'Unknown')} - "
                    f"{access_message}"
                )
                session.clear()
                return render_template("unauthorized.html"), 403

            # Nettoyage et sauvegarde en session
            session.pop("test_value", None)
            session["user"] = userinfo
            session["access_token"] = access_token
            session["habilitations"] = habilitations
            session.permanent = True
            session.modified = True

            # Redirection
            next_url = session.pop("next_url", "/")
            is_iframe = session.pop("is_iframe", False)

            # 🖼️ Si le contexte était un iframe, utiliser un template de redirection iframe
            if is_iframe:
                print(f"🖼️  Redirection iframe vers: {next_url}")
                return render_template("iframe_redirect.html", redirect_url=next_url)

            print(f"✅ Redirecting to: {next_url}")
            return redirect(next_url)

        except Exception as e:
            # Logging détaillé de l'erreur
            self.app.logger.error("=" * 60)
            self.app.logger.error(f"❌ ERREUR D'AUTHENTIFICATION: {e}")
            self.app.logger.error(f"   Type d'erreur: {type(e).__name__}")
            self.app.logger.error(f"   Message: {str(e)}")

            # Informations de contexte
            self.app.logger.error(f"   Session persistante: {session_persistent}")
            self.app.logger.error(
                f"   Code OAuth: {request.args.get('code', 'ABSENT')[:20] if request.args.get('code') else 'ABSENT'}..."
            )
            self.app.logger.error(
                f"   State OAuth: {request.args.get('state', 'ABSENT')}"
            )
            self.app.logger.error(
                f"   Error param: {request.args.get('error', 'ABSENT')}"
            )

            # État des variables locales
            if "token" in locals():
                self.app.logger.error("   Token présent: Oui")
                self.app.logger.error(f"   Token type: {type(token).__name__}")
                if isinstance(token, dict):
                    self.app.logger.error(f"   Token keys: {list(token.keys())}")
                else:
                    self.app.logger.error(f"   Token value: {str(token)[:200]}")
            else:
                self.app.logger.error("   Token présent: Non")

            if "userinfo" in locals():
                self.app.logger.error(f"   Userinfo type: {type(userinfo).__name__}")
                if isinstance(userinfo, dict):
                    self.app.logger.error(f"   Userinfo keys: {list(userinfo.keys())}")
                else:
                    self.app.logger.error(f"   Userinfo value: {str(userinfo)[:200]}")
            else:
                self.app.logger.error("   Userinfo présent: Non")

            self.app.logger.error("=" * 60)

            # Solutions suggérées
            if "state" in str(e).lower() or not session_persistent:
                self.app.logger.error("💡 PROBLÈME DE SESSION DÉTECTÉ:")
                self.app.logger.error(
                    "   → Cause: Cookies de session non persistants (HTTP localhost)"
                )
                self.app.logger.error("   → Solutions:")
                self.app.logger.error("     1. Utiliser HTTPS (recommandé)")
                self.app.logger.error(
                    "     2. Vérifier SESSION_COOKIE_SAMESITE='Lax' dans config"
                )
                self.app.logger.error(
                    "     3. Vérifier SESSION_COOKIE_SECURE=False en dev"
                )
                self.app.logger.error("     4. Vérifier que SECRET_KEY est définie")

            if self.app.debug:
                import traceback

                self.app.logger.error("Stack trace complète:")
                self.app.logger.error(traceback.format_exc())

            # Nettoyer la session et rediriger
            session.clear()
            return redirect("/?error=auth_failed")

    def logout(self):
        """Déconnecte l'utilisateur et nettoie la session"""
        session.clear()
        print("Utilisateur déconnecté")
        return redirect("/")

    def login_required(self, f):
        """
        Décorateur pour protéger les routes nécessitant une authentification

        Revérifie les habilitations à chaque requête pour prendre en compte
        les modifications de configuration en temps réel.
        """

        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user" not in session or "habilitations" not in session:
                # Sauvegarder l'URL demandée
                session["next_url"] = request.url

                # 🔹 Détecter et sauvegarder le contexte iframe
                is_iframe = (
                    request.headers.get("Sec-Fetch-Dest") == "iframe"
                    or request.args.get("iframe") == "true"
                )
                session["is_iframe"] = is_iframe
                session.modified = True

                # 🔹 Si dans un iframe, rediriger le parent
                if is_iframe:
                    print("🖼️  Contexte iframe détecté - Redirection parent")
                    return render_template(
                        "redirect_parent.html", login_url=self.login_url
                    )

                return redirect(self.login_url)

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

                    if not has_access:
                        username = session.get("user", {}).get(
                            "preferred_username", "Unknown"
                        )
                        print(
                            f"🔒 Accès révoqué (habilitations modifiées) - User: {username}"
                        )
                        session.clear()
                        return render_template(
                            "error.html",
                            error_title="Accès Révoqué",
                            error_message="Vos habilitations ont été modifiées. Veuillez vous reconnecter.",
                            error_details=message,
                        )
                except Exception as e:
                    print(f"⚠️ Erreur vérification habilitations: {e}")
                    # En cas d'erreur, on laisse passer (fail-open) pour ne pas bloquer l'appli
                    pass

            return f(*args, **kwargs)

        return decorated_function

    def get_user_info(self):
        """Récupère les informations de l'utilisateur connecté"""
        return session.get("user", {})

    def get_habilitations(self):
        """Récupère les habilitations de l'utilisateur connecté"""
        return session.get("habilitations", {})
