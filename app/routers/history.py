"""
Routes d'historique et de gestion des conversations
"""
import logging
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, Request, Depends, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from app.config import get_settings, Settings
from app.dependencies.auth import get_current_user
from core.storage_manager import StorageManager
from core.async_logger import async_logger


router = APIRouter(tags=["History"])
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


@router.get("/history", response_class=templates.TemplateResponse)
async def history_page(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Page d'historique des conversations

    Returns:
        TemplateResponse: Page history.html
    """
    try:
        return templates.TemplateResponse(
            "history.html",
            {"request": request, "user": user}
        )
    except Exception as e:
        logger.error(f"Error loading history page: {e}")
        raise


@router.get("/suivi_syntheses", response_class=templates.TemplateResponse)
async def suivi_syntheses_page(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Page de suivi des synthèses

    Returns:
        TemplateResponse: Page suivi_syntheses.html
    """
    try:
        return templates.TemplateResponse(
            "suivi_syntheses.html",
            {"request": request, "user": user}
        )
    except Exception as e:
        logger.error(f"Error loading syntheses page: {e}")
        raise


@router.get("/load_conversations", response_class=templates.TemplateResponse)
async def load_conversations_page(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Page de chargement de conversations

    Returns:
        TemplateResponse: Page load_conversations.html
    """
    try:
        return templates.TemplateResponse(
            "load_conversations.html",
            {"request": request, "user": user}
        )
    except Exception as e:
        logger.error(f"Error loading conversations page: {e}")
        raise


@router.get("/list_conversations")
async def list_conversations(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Lister les conversations sauvegardées de l'utilisateur

    Returns:
        dict: Liste des conversations
    """
    try:
        storage = StorageManager()
        user_email = user.get("email", "")

        user_folder = storage.get_user_folder_path(user_email)
        conv_folder = user_folder / "conversations"

        conversations = []
        if conv_folder.exists():
            for file_path in conv_folder.glob("*.json"):
                conversations.append({
                    "filename": file_path.name,
                    "path": str(file_path.relative_to(user_folder)),
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                })

        return {
            "success": True,
            "conversations": conversations,
        }

    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@router.post("/upload_conversation")
async def upload_conversation(
    request: Request,
    file: UploadFile = File(...),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Upload une conversation

    Args:
        file: Fichier JSON de conversation

    Returns:
        dict: Confirmation
    """
    try:
        storage = StorageManager()
        user_email = user.get("email", "")

        # Lire le contenu
        content = await file.read()

        # Sauvegarder dans le dossier utilisateur
        user_folder = storage.get_user_folder_path(user_email)
        conv_folder = user_folder / "conversations"
        conv_folder.mkdir(parents=True, exist_ok=True)

        file_path = conv_folder / file.filename
        storage.save_file(str(file_path), content)

        async_logger.info(
            "Conversation uploaded",
            user=user.get("preferred_username", ""),
            filename=file.filename
        )

        return {
            "success": True,
            "message": f"Conversation '{file.filename}' uploadée avec succès",
        }

    except Exception as e:
        logger.error(f"Error uploading conversation: {e}")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@router.get("/_stcore/health")
async def health_check():
    """
    Health check endpoint (pas d'authentification)

    Returns:
        dict: Status
    """
    return {"status": "healthy"}


@router.get("/favicon.ico")
async def favicon():
    """
    Favicon endpoint

    Returns:
        FileResponse: Favicon
    """
    from pathlib import Path

    favicon_path = Path("static") / "img" / "favicon.ico"
    if favicon_path.exists():
        from fastapi.responses import FileResponse
        return FileResponse(str(favicon_path))
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
