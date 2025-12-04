"""
Routes d'authentification OAuth2
"""
import secrets
import logging
from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth

from app.config import get_settings, Settings
from app.dependencies.auth import get_oauth_client, get_user_habilitations
from core.habilitations_manager import HabilitationsManager


router = APIRouter(tags=["Authentication"])
logger = logging.getLogger(__name__)


@router.get("/login")
async def login(
    request: Request,
    oauth: OAuth = Depends(get_oauth_client),
    settings: Settings = Depends(get_settings)
):
    """
    Initie le flux OAuth2 avec protection CSRF

    Returns:
        RedirectResponse: Redirection vers le serveur OAuth
    """
    try:
        # Marquer la session comme permanente
        request.session["permanent"] = True

        # Générer un nonce cryptographiquement sécurisé
        nonce = secrets.token_urlsafe(32)  # 32 bytes = 256 bits

        # Sauvegarder le nonce dans la session avec timestamp
        request.session["oauth_nonce"] = nonce
        request.session["oauth_timestamp"] = datetime.utcnow().isoformat()

        logger.info(
            "🔐 Initiation OAuth2 - Nonce: %s...",
            nonce[:8]
        )

        # Récupérer l'URL de callback
        redirect_uri = settings.gauthiq_redirect_uri

        # Redirection vers le serveur OAuth
        return await oauth.gauthiq.authorize_redirect(request, redirect_uri, nonce=nonce)

    except Exception as e:
        logger.error(
            "❌ Erreur lors de l'initiation OAuth: %s", str(e), exc_info=True
        )
        return RedirectResponse(url="/?error=auth_init_failed")


@router.get("/oauth2callback")
async def oauth2callback(
    request: Request,
    oauth: OAuth = Depends(get_oauth_client),
    settings: Settings = Depends(get_settings)
):
    """
    Callback OAuth2 - traite le retour du serveur OAuth

    Returns:
        RedirectResponse: Redirection vers la page demandée ou l'accueil
    """
    try:
        # ========================================
        # 1. VALIDATION DU NONCE (Protection CSRF)
        # ========================================
        stored_nonce = request.session.get("oauth_nonce")
        nonce_timestamp = request.session.get("oauth_timestamp")

        if not stored_nonce or not nonce_timestamp:
            logger.error("❌ SÉCURITÉ: Nonce manquant dans la session")
            return RedirectResponse(url="/login?error=csrf_failed")

        # Vérifier que le nonce n'est pas trop vieux (5 minutes max)
        try:
            timestamp_dt = datetime.fromisoformat(nonce_timestamp)
            age = (datetime.utcnow() - timestamp_dt).total_seconds()

            if age > 300:  # 5 minutes
                logger.error(
                    "❌ SÉCURITÉ: Nonce expiré (âge: %.1f secondes)",
                    age
                )
                request.session.pop("oauth_nonce", None)
                request.session.pop("oauth_timestamp", None)
                return RedirectResponse(url="/login?error=nonce_expired")
        except (ValueError, TypeError) as e:
            logger.error(
                "❌ SÉCURITÉ: Timestamp invalide: %s", str(e)
            )
            return RedirectResponse(url="/login?error=invalid_timestamp")

        # ========================================
        # 2. ÉCHANGE DU CODE CONTRE UN TOKEN
        # ========================================
        try:
            token = await oauth.gauthiq.authorize_access_token(request, nonce=stored_nonce)
        except Exception as e:
            logger.error(
                "❌ Échec d'échange du code OAuth: %s", str(e), exc_info=True
            )
            return RedirectResponse(url="/login?error=token_exchange_failed")

        # Nettoyer le nonce de la session
        request.session.pop("oauth_nonce", None)
        request.session.pop("oauth_timestamp", None)

        # ========================================
        # 3. EXTRACTION DES INFORMATIONS UTILISATEUR
        # ========================================
        id_token = token.get("id_token")
        access_token = token.get("access_token")

        if not id_token:
            logger.error("❌ ID Token manquant dans la réponse OAuth")
            return RedirectResponse(url="/login?error=no_id_token")

        if not access_token:
            logger.error("❌ Access Token manquant dans la réponse OAuth")
            return RedirectResponse(url="/login?error=no_access_token")

        # Parser le token pour extraire les informations utilisateur
        try:
            userinfo = await oauth.gauthiq.parse_id_token(request, token, nonce=stored_nonce)
        except Exception as e:
            logger.error(
                "❌ Échec de parsing du ID token: %s", str(e), exc_info=True
            )
            return RedirectResponse(url="/login?error=token_parse_failed")

        # ========================================
        # 4. RÉCUPÉRATION DES HABILITATIONS
        # ========================================
        habilitations = await get_user_habilitations(userinfo, access_token, settings)

        # ========================================
        # 5. VÉRIFICATION ADMIN ET INJECTION DE RÔLE
        # ========================================
        admin_list = settings.get_admin_list()

        user_email = userinfo.get("email", "")
        user_name = userinfo.get("preferred_username", "")

        # Si l'utilisateur est dans LISTE_ADMINS, injecter le rôle admin
        if user_email in admin_list or user_name in admin_list:
            if "roles" not in habilitations:
                habilitations["roles"] = {}

            if "GR_SIMSAN_ADMIN" not in habilitations["roles"]:
                habilitations["roles"]["GR_SIMSAN_ADMIN"] = ["ADMIN"]
                logger.info(
                    "✓ Rôle ADMIN injecté pour %s (%s)",
                    user_name,
                    user_email
                )

        # ========================================
        # 6. VÉRIFICATION DE L'ACCÈS
        # ========================================
        hab_manager = HabilitationsManager()

        if not hab_manager.user_has_access(habilitations):
            logger.warning(
                "⚠️ Accès refusé pour %s (%s) - Habilitations insuffisantes",
                user_name,
                user_email
            )
            return RedirectResponse(url="/unauthorized")

        # ========================================
        # 7. STOCKAGE DANS LA SESSION
        # ========================================
        request.session["user"] = {
            "sub": userinfo.get("sub"),
            "preferred_username": user_name,
            "email": user_email,
            "name": userinfo.get("name", user_name),
        }
        request.session["access_token"] = access_token
        request.session["habilitations"] = habilitations
        request.session["auth_timestamp"] = datetime.utcnow().isoformat()

        # Informations utilisateur supplémentaires
        request.session["user_name"] = user_name
        request.session["user_email"] = user_email
        request.session["user_id"] = userinfo.get("sub", "")
        request.session["user_folder"] = user_email.replace("@", "_at_").replace(".", "_")

        logger.info(
            "✓ Authentification réussie pour %s (%s)",
            user_name,
            user_email
        )

        # ========================================
        # 8. REDIRECTION VERS LA PAGE DEMANDÉE
        # ========================================

        # Protection contre les redirections ouvertes
        next_url = request.session.pop("next_url", "/")

        # Valider que next_url est une URL relative (pas de domaine externe)
        if next_url.startswith("http://") or next_url.startswith("https://"):
            logger.warning(
                "⚠️ SÉCURITÉ: Tentative de redirection externe bloquée: %s",
                next_url
            )
            next_url = "/"

        return RedirectResponse(url=next_url)

    except Exception as e:
        logger.error(
            "❌ Erreur dans le callback OAuth: %s", str(e), exc_info=True
        )
        return RedirectResponse(url="/login?error=callback_failed")


@router.get("/logout")
async def logout(request: Request):
    """
    Déconnexion - efface la session

    Returns:
        RedirectResponse: Redirection vers la page d'accueil
    """
    try:
        user_name = request.session.get("user_name", "unknown")
        logger.info("👋 Déconnexion de %s", user_name)

        # Effacer la session
        request.session.clear()

        return RedirectResponse(url="/")

    except Exception as e:
        logger.error(
            "❌ Erreur lors de la déconnexion: %s", str(e), exc_info=True
        )
        return RedirectResponse(url="/")


@router.get("/check_admin")
async def check_admin(request: Request, settings: Settings = Depends(get_settings)):
    """
    Vérifie si l'utilisateur est admin

    Returns:
        dict: {"is_admin": bool}
    """
    try:
        user_email = request.session.get("user_email", "")
        user_name = request.session.get("user_name", "")

        admin_list = settings.get_admin_list()

        # Vérifier si l'utilisateur est dans la liste des admins
        is_admin = user_email in admin_list or user_name in admin_list

        # Vérifier aussi les habilitations
        if not is_admin:
            habilitations = request.session.get("habilitations", {})
            roles = habilitations.get("roles", {})
            is_admin = "GR_SIMSAN_ADMIN" in roles

        return {"is_admin": is_admin}

    except Exception as e:
        logger.error("Error checking admin status: %s", str(e))
        return {"is_admin": False}
