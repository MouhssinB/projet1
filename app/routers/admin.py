"""
Routes d'administration
"""
import logging
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, Request, Depends, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates

from app.config import get_settings, Settings
from app.dependencies.auth import get_current_admin
from app.models.habilitations import HabilitationsConfig, HabilitationUpdate
from core.habilitations_manager import HabilitationsManager
from core.storage_manager import StorageManager
from core.async_logger import async_logger


router = APIRouter(tags=["Admin"], prefix="/admin")
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


@router.get("_suivis", response_class=templates.TemplateResponse)
async def admin_suivis(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Tableau de bord admin - suivi des synthèses

    Returns:
        TemplateResponse: Page admin.html
    """
    try:
        return templates.TemplateResponse(
            "admin.html",
            {"request": request, "user": user}
        )
    except Exception as e:
        logger.error(f"Error loading admin page: {e}")
        raise


@router.get("/habilitations", response_class=templates.TemplateResponse)
async def admin_habilitations_page(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Page de gestion des habilitations

    Returns:
        TemplateResponse: Page admin_habilitations.html
    """
    try:
        return templates.TemplateResponse(
            "admin_habilitations.html",
            {"request": request, "user": user}
        )
    except Exception as e:
        logger.error(f"Error loading habilitations page: {e}")
        raise


@router.get("/habilitations/config")
async def get_habilitations_config(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Récupérer la configuration des habilitations

    Returns:
        dict: Configuration actuelle
    """
    try:
        hab_manager = HabilitationsManager()
        config = hab_manager.get_configuration_complete()

        return {
            "success": True,
            "config": config,
        }

    except Exception as e:
        logger.error(f"Error getting habilitations config: {e}")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@router.post("/habilitations/update")
async def update_habilitations(
    request: Request,
    update: HabilitationUpdate,
    user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Mettre à jour les habilitations

    Args:
        update: Nouvelle configuration

    Returns:
        dict: Confirmation
    """
    try:
        hab_manager = HabilitationsManager()

        user_name = user.get("preferred_username", "")
        user_email = user.get("email", "")

        success = hab_manager.update_configuration(
            groupes_habilites=update.groupes_habilites,
            modifie_par=f"{user_name} ({user_email})"
        )

        if success:
            async_logger.info(
                "Habilitations updated",
                user=user_name,
                groups=update.groupes_habilites
            )

            return {
                "success": True,
                "message": "Habilitations mises à jour avec succès",
            }
        else:
            return JSONResponse(
                {"success": False, "error": "Échec de la mise à jour"},
                status_code=500
            )

    except Exception as e:
        logger.error(f"Error updating habilitations: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@router.get("_fileshare_browser", response_class=templates.TemplateResponse)
async def admin_fileshare_browser(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Navigateur de fichiers FileShare

    Returns:
        TemplateResponse: Page fileshare_browser.html
    """
    try:
        return templates.TemplateResponse(
            "fileshare_browser.html",
            {"request": request, "user": user}
        )
    except Exception as e:
        logger.error(f"Error loading fileshare browser: {e}")
        raise


@router.post("/upload_guide")
async def upload_guide(
    request: Request,
    file: UploadFile = File(...),
    user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Upload un fichier guide

    Args:
        file: Fichier à uploader

    Returns:
        dict: Confirmation
    """
    try:
        storage = StorageManager()

        # Lire le contenu du fichier
        content = await file.read()

        # Sauvegarder dans data/guide_utilisateur/
        file_path = f"data/guide_utilisateur/{file.filename}"
        storage.save_file(file_path, content)

        async_logger.info(
            "Guide uploaded",
            user=user.get("preferred_username", ""),
            filename=file.filename
        )

        return {
            "success": True,
            "message": f"Fichier '{file.filename}' uploadé avec succès",
        }

    except Exception as e:
        logger.error(f"Error uploading guide: {e}")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@router.post("/delete_guide")
async def delete_guide(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Supprimer un fichier guide

    Returns:
        dict: Confirmation
    """
    try:
        data = await request.json()
        filename = data.get("filename")

        if not filename:
            return JSONResponse(
                {"success": False, "error": "Nom de fichier manquant"},
                status_code=400
            )

        storage = StorageManager()
        file_path = f"data/guide_utilisateur/{filename}"
        storage.delete_file(file_path)

        async_logger.info(
            "Guide deleted",
            user=user.get("preferred_username", ""),
            filename=filename
        )

        return {
            "success": True,
            "message": f"Fichier '{filename}' supprimé avec succès",
        }

    except Exception as e:
        logger.error(f"Error deleting guide: {e}")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@router.post("_fileshare_download")
async def admin_fileshare_download(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Télécharger un fichier du FileShare

    Returns:
        FileResponse: Fichier demandé
    """
    try:
        data = await request.json()
        file_path = data.get("file_path")

        if not file_path:
            return JSONResponse(
                {"success": False, "error": "Chemin de fichier manquant"},
                status_code=400
            )

        # TODO: Implement file download from Azure FileShare
        # This would use the fonctions_fileshare.py module

        return JSONResponse(
            {"success": False, "error": "Not implemented yet"},
            status_code=501
        )

    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@router.post("_fileshare_delete")
async def admin_fileshare_delete(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Supprimer un fichier du FileShare

    Returns:
        dict: Confirmation
    """
    try:
        data = await request.json()
        file_path = data.get("file_path")

        if not file_path:
            return JSONResponse(
                {"success": False, "error": "Chemin de fichier manquant"},
                status_code=400
            )

        # TODO: Implement file deletion from Azure FileShare
        # This would use the fonctions_fileshare.py module

        return JSONResponse(
            {"success": False, "error": "Not implemented yet"},
            status_code=501
        )

    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )
