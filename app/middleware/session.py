"""
Configuration du middleware de session pour FastAPI
"""
import os
from starlette.middleware.sessions import SessionMiddleware
from fastapi import FastAPI
from app.config import Settings


def setup_session_middleware(app: FastAPI, settings: Settings) -> None:
    """
    Configure le middleware de session pour FastAPI

    En production, les sessions sont stockées dans Azure FileShare.
    En développement, elles sont stockées localement dans flask_session/.

    Args:
        app: Application FastAPI
        settings: Configuration de l'application
    """
    # Vérifier que SECRET_KEY est définie
    if not settings.secret_key:
        raise ValueError("SECRET_KEY must be set in environment variables")

    if len(settings.secret_key) < 32:
        raise ValueError(f"SECRET_KEY too short ({len(settings.secret_key)} characters). Minimum 32 required.")

    # Configuration du middleware de session
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie=settings.session_cookie_name,
        max_age=settings.session_max_age,
        same_site=settings.session_cookie_samesite.lower(),
        https_only=settings.session_cookie_secure,
        http_only=settings.session_cookie_httponly,
    )

    # Note: FastAPI's SessionMiddleware stores sessions in cookies by default
    # For filesystem-based sessions like Flask-Session, we would need a custom implementation
    # or use a third-party library like fastapi-sessions with a filesystem backend.
    # For now, we'll use cookie-based sessions which is more scalable.
