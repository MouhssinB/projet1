"""
Gestion des exceptions pour FastAPI
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging


logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="templates")


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Gestionnaire d'exceptions HTTP

    Args:
        request: Requête FastAPI
        exc: Exception HTTP

    Returns:
        Response appropriée (JSON ou HTML)
    """
    # Pour les requêtes API, retourner du JSON
    if request.url.path.startswith("/api/") or "application/json" in request.headers.get("accept", ""):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "status_code": exc.status_code}
        )

    # Pour 401, rediriger vers login
    if exc.status_code == 401:
        # Vérifier si c'est une iframe
        if exc.detail == "iframe_auth_required":
            return templates.TemplateResponse(
                "iframe_redirect.html",
                {"request": request}
            )

        return RedirectResponse(url="/login")

    # Pour 403, afficher page unauthorized
    if exc.status_code == 403:
        return templates.TemplateResponse(
            "unauthorized.html",
            {"request": request},
            status_code=403
        )

    # Pour 404, retourner erreur JSON
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content={"error": "Not Found", "status_code": 404}
        )

    # Pour les autres erreurs, afficher page d'erreur
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "error": exc.detail},
        status_code=exc.status_code
    )


async def general_exception_handler(request: Request, exc: Exception):
    """
    Gestionnaire d'exceptions générales

    Args:
        request: Requête FastAPI
        exc: Exception

    Returns:
        Response d'erreur
    """
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        str(exc),
        exc_info=True
    )

    # Pour les requêtes API, retourner du JSON
    if request.url.path.startswith("/api/") or "application/json" in request.headers.get("accept", ""):
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error", "status_code": 500}
        )

    # Pour les autres, afficher page d'erreur
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "error": "Une erreur s'est produite"},
        status_code=500
    )


def setup_exception_handlers(app):
    """
    Configure les gestionnaires d'exceptions

    Args:
        app: Application FastAPI
    """
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
