"""
Point d'entrée principal de l'application FastAPI
GMA Training Bot IHM - Migré de Flask vers FastAPI
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.middleware.logging import LoggingMiddleware
from app.middleware.session import setup_session_middleware
from app.exceptions import setup_exception_handlers
from app.routers import (
    auth_router,
    chat_router,
    faq_router,
    admin_router,
    files_router,
    history_router,
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestionnaire de cycle de vie de l'application
    """
    # Startup
    logger.info("=" * 60)
    logger.info("🚀 GMA Training Bot IHM - FastAPI Edition")
    logger.info("=" * 60)

    settings = get_settings()

    logger.info(f"Environment: {'Production' if settings.is_production() else 'Development'}")
    logger.info(f"Azure OpenAI Endpoint: {settings.azure_openai_endpoint}")
    logger.info(f"OAuth Redirect URI: {settings.gauthiq_redirect_uri}")

    # Initialiser Azure Monitor si configuré
    if settings.applicationinsights_connection_string:
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            configure_azure_monitor(
                connection_string=settings.applicationinsights_connection_string
            )

            FastAPIInstrumentor.instrument_app(app)

            logger.info("✓ Azure Monitor OpenTelemetry initialized")
        except ImportError:
            logger.warning("⚠️ Azure Monitor libraries not available")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Azure Monitor: {e}")

    logger.info("✓ Application startup complete")

    yield

    # Shutdown
    logger.info("👋 Shutting down application")

    # Arrêt propre du logger asynchrone
    try:
        from core.async_logger import shutdown_async_logger
        shutdown_async_logger()
        logger.info("✓ Async logger shutdown complete")
    except Exception as e:
        logger.error(f"Error shutting down async logger: {e}")


def create_app() -> FastAPI:
    """
    Créer et configurer l'application FastAPI

    Returns:
        FastAPI: Application configurée
    """
    settings = get_settings()

    # Créer l'application FastAPI
    app = FastAPI(
        title="GMA Training Bot IHM",
        description="Interface de formation GMA - Migré vers FastAPI",
        version="2.0.0",
        docs_url="/docs" if not settings.is_production() else None,  # Désactiver docs en prod
        redoc_url="/redoc" if not settings.is_production() else None,
        lifespan=lifespan,
    )

    # ========================================
    # MIDDLEWARE
    # ========================================

    # 1. CORS Middleware (en premier pour permettre les requêtes cross-origin)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    logger.info("✓ CORS middleware configured")

    # 2. Session Middleware (pour gérer les sessions utilisateur)
    setup_session_middleware(app, settings)
    logger.info("✓ Session middleware configured")

    # 3. Logging Middleware (pour logger les requêtes/réponses)
    app.add_middleware(LoggingMiddleware)
    logger.info("✓ Logging middleware configured")

    # ========================================
    # EXCEPTION HANDLERS
    # ========================================
    setup_exception_handlers(app)
    logger.info("✓ Exception handlers configured")

    # ========================================
    # STATIC FILES
    # ========================================
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("✓ Static files mounted at /static")

    # ========================================
    # ROUTERS
    # ========================================

    # Routes d'authentification (sans préfixe, chemins définis dans le router)
    app.include_router(auth_router)
    logger.info("✓ Auth routes registered")

    # Routes de chat (routes principales)
    app.include_router(chat_router)
    logger.info("✓ Chat routes registered")

    # Routes FAQ
    app.include_router(faq_router)
    logger.info("✓ FAQ routes registered")

    # Routes d'administration
    app.include_router(admin_router)
    logger.info("✓ Admin routes registered")

    # Routes de fichiers
    app.include_router(files_router)
    logger.info("✓ File routes registered")

    # Routes d'historique
    app.include_router(history_router)
    logger.info("✓ History routes registered")

    logger.info("=" * 60)
    logger.info("✓ All routes registered successfully")
    logger.info("=" * 60)

    return app


# Créer l'instance de l'application
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    # Configuration d'uvicorn
    uvicorn_config = {
        "app": "main_fastapi:app",
        "host": "0.0.0.0",
        "port": int(os.getenv("PORT", "8000")),
        "reload": not settings.is_production(),
        "log_level": "info",
        "access_log": True,
    }

    logger.info(f"Starting uvicorn server on {uvicorn_config['host']}:{uvicorn_config['port']}")

    uvicorn.run(**uvicorn_config)
