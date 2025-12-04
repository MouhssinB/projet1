"""
Middleware de logging pour FastAPI
"""
import logging
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware pour logger les requêtes et réponses
    Équivalent de @app.before_request et @app.after_request de Flask
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

        # Filtrer certains chemins pour éviter trop de logs
        self.excluded_paths = {
            "/static",
            "/favicon.ico",
            "/_stcore/health",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Traite la requête et la réponse

        Args:
            request: Requête FastAPI
            call_next: Fonction pour appeler le prochain middleware/handler

        Returns:
            Response: Réponse HTTP
        """
        # Vérifier si le chemin doit être exclu
        path = request.url.path
        should_log = not any(path.startswith(excluded) for excluded in self.excluded_paths)

        # Log de la requête entrante (équivalent de before_request)
        if should_log:
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")

            logger.info(
                "→ %s %s from %s | UA: %s",
                request.method,
                path,
                client_ip,
                user_agent[:100]  # Limiter la longueur du User-Agent
            )

        # Mesurer le temps de traitement
        start_time = time.time()

        # Traiter la requête
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(
                "❌ Error processing %s %s: %s",
                request.method,
                path,
                str(e),
                exc_info=True
            )
            raise

        # Calculer le temps de traitement
        process_time = time.time() - start_time

        # Log de la réponse (équivalent de after_request)
        if should_log:
            # Logger les erreurs (status >= 400)
            if response.status_code >= 400:
                logger.error(
                    "← %s %s → %d (%.3fs)",
                    request.method,
                    path,
                    response.status_code,
                    process_time
                )
            else:
                logger.info(
                    "← %s %s → %d (%.3fs)",
                    request.method,
                    path,
                    response.status_code,
                    process_time
                )

        # Ajouter le header de temps de traitement
        response.headers["X-Process-Time"] = f"{process_time:.3f}"

        return response
