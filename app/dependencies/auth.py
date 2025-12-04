"""
Dépendances d'authentification pour FastAPI
"""
import secrets
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config as StarletteConfig

from app.config import get_settings, Settings
from core.habilitations_manager import HabilitationsManager


# OAuth client singleton
_oauth_instance = None


def get_oauth_client():
    """Retourne l'instance OAuth (singleton)"""
    global _oauth_instance
    if _oauth_instance is None:
        settings = get_settings()

        # Configuration Authlib
        config_data = {
            "GAUTHIQ_CLIENT_ID": settings.gauthiq_client_id,
            "GAUTHIQ_CLIENT_SECRET": settings.gauthiq_client_secret,
        }
        config = StarletteConfig(environ=config_data)

        _oauth_instance = OAuth(config)

        # Configuration du client OAuth
        # Utilise le mode d'authentification (local ou production)
        ssl_verify = settings.get_auth_ssl_verify()

        client_kwargs = {
            "scope": "openid profile email",
            "verify": ssl_verify,
            "timeout": 30,
        }

        _oauth_instance.register(
            name="gauthiq",
            client_id=settings.gauthiq_client_id,
            client_secret=settings.gauthiq_client_secret,
            server_metadata_url=settings.gauthiq_discovery_url,
            client_kwargs=client_kwargs,
        )

    return _oauth_instance


oauth_client = Depends(get_oauth_client)


async def get_user_habilitations(
    userinfo: dict,
    access_token: str,
    settings: Settings = Depends(get_settings)
) -> dict:
    """
    Récupère les habilitations de l'utilisateur depuis l'API Gauthiq

    Args:
        userinfo: Informations utilisateur du token ID
        access_token: Token d'accès OAuth
        settings: Configuration de l'application

    Returns:
        dict: Habilitations de l'utilisateur ou {} en cas d'erreur
    """
    if not isinstance(userinfo, dict):
        return {}

    if not access_token or not isinstance(access_token, str):
        return {}

    # Récupération du filtre d'habilitations
    filtre_habilitation = settings.gauthiq_habilitation_filtre

    if not filtre_habilitation:
        return {}

    # Construction de l'URL avec le filtre
    api_url = settings.gauthiq_habilitation
    params = {"filtre": filtre_habilitation}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    try:
        # Utilise le mode d'authentification pour SSL
        ssl_verify = settings.get_auth_ssl_verify()

        response = requests.get(
            api_url,
            params=params,
            headers=headers,
            timeout=10,
            verify=ssl_verify,
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {}

    except requests.exceptions.Timeout:
        return {}
    except requests.exceptions.RequestException:
        return {}
    except ValueError:
        return {}


async def validate_session(request: Request, settings: Settings = Depends(get_settings)) -> Optional[Dict[str, Any]]:
    """
    Valide la session utilisateur

    Args:
        request: Requête FastAPI
        settings: Configuration de l'application

    Returns:
        Optional[Dict]: Informations utilisateur si authentifié, None sinon
    """
    # Vérifier si l'utilisateur est dans la session
    if "user" not in request.session:
        return None

    # Vérifier le timestamp de la session (8 heures max)
    auth_timestamp_str = request.session.get("auth_timestamp")
    if not auth_timestamp_str:
        return None

    try:
        auth_timestamp = datetime.fromisoformat(auth_timestamp_str)
        session_age = datetime.utcnow() - auth_timestamp

        # Session expirée après 8 heures
        if session_age > timedelta(hours=8):
            request.session.clear()
            return None
    except (ValueError, TypeError):
        return None

    # Re-valider les habilitations
    access_token = request.session.get("access_token")
    user = request.session.get("user")

    if not access_token or not user:
        return None

    # Récupérer les habilitations à nouveau
    habilitations = await get_user_habilitations(user, access_token, settings)

    # Vérifier si l'utilisateur est admin
    admin_list = settings.get_admin_list()
    user_email = user.get("email", "")
    user_name = user.get("preferred_username", "")

    # Injecter le rôle admin si nécessaire
    if user_email in admin_list or user_name in admin_list:
        if "roles" not in habilitations:
            habilitations["roles"] = {}
        if "GR_SIMSAN_ADMIN" not in habilitations["roles"]:
            habilitations["roles"]["GR_SIMSAN_ADMIN"] = ["ADMIN"]

    # Vérifier l'accès via HabilitationsManager
    hab_manager = HabilitationsManager()
    if not hab_manager.user_has_access(habilitations):
        return None

    return user


async def get_current_user(request: Request, settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    """
    Dépendance FastAPI pour obtenir l'utilisateur courant

    Args:
        request: Requête FastAPI
        settings: Configuration de l'application

    Returns:
        Dict: Informations utilisateur

    Raises:
        HTTPException: Si l'utilisateur n'est pas authentifié
    """
    user = await validate_session(request, settings)

    if user is None:
        # Vérifier si c'est une requête iframe
        is_iframe = request.session.get("is_iframe", False)

        if is_iframe:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="iframe_auth_required"
            )

        # Sauvegarder l'URL de retour
        request.session["next_url"] = str(request.url)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_admin(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user),
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Dépendance FastAPI pour obtenir un utilisateur admin

    Args:
        request: Requête FastAPI
        user: Utilisateur courant
        settings: Configuration de l'application

    Returns:
        Dict: Informations utilisateur admin

    Raises:
        HTTPException: Si l'utilisateur n'est pas admin
    """
    admin_list = settings.get_admin_list()

    user_email = user.get("email", "")
    user_name = user.get("preferred_username", "")

    # Vérifier si l'utilisateur est dans la liste des admins
    if user_email not in admin_list and user_name not in admin_list:
        # Vérifier les habilitations
        habilitations = request.session.get("habilitations", {})
        roles = habilitations.get("roles", {})

        if "GR_SIMSAN_ADMIN" not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

    return user


def get_habilitations_manager() -> HabilitationsManager:
    """
    Dépendance pour obtenir le gestionnaire d'habilitations

    Returns:
        HabilitationsManager: Instance du gestionnaire
    """
    return HabilitationsManager()
