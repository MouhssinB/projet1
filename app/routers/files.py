"""
Routes de gestion des fichiers
"""
import logging
import os
from typing import Dict, Any

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

from app.config import get_settings, Settings
from app.dependencies.auth import get_current_user
from core.security import sanitize_path, sanitize_filename


router = APIRouter(tags=["Files"])
logger = logging.getLogger(__name__)


@router.get("/serve_file/{file_type}/{filename:path}")
async def serve_file(
    file_type: str,
    filename: str,
    user: Dict[str, Any] = Depends(get_current_user),
    settings: Settings = Depends(get_settings)
):
    """
    Servir un fichier local

    Args:
        file_type: Type de fichier (conversations, syntheses, etc.)
        filename: Nom du fichier (avec chemin relatif)

    Returns:
        FileResponse: Fichier demandé
    """
    try:
        # Sécuriser le chemin
        safe_filename = sanitize_path(filename)
        safe_file_type = sanitize_filename(file_type)

        # Construire le chemin complet
        base_path = "data"
        if settings.is_production():
            base_path = settings.azure_fileshare_mount_point

        file_path = Path(base_path) / safe_file_type / safe_filename

        # Vérifier que le fichier existe
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        # Vérifier que le fichier est dans le répertoire autorisé (protection path traversal)
        try:
            file_path.resolve().relative_to(Path(base_path).resolve())
        except ValueError:
            logger.warning(f"Path traversal attempt detected: {filename}")
            raise HTTPException(status_code=403, detail="Access denied")

        return FileResponse(
            path=str(file_path),
            filename=safe_filename.split("/")[-1]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/serve_file_azure/{file_type}/{filename:path}")
async def serve_file_azure(
    file_type: str,
    filename: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Servir un fichier depuis Azure Blob Storage

    Args:
        file_type: Type de fichier
        filename: Nom du fichier

    Returns:
        FileResponse: Fichier depuis Azure
    """
    try:
        # TODO: Implement Azure Blob Storage file serving
        # This would use fonctions_fileshare.py and generate_blob_url_with_sas

        raise HTTPException(status_code=501, detail="Azure file serving not implemented yet")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving Azure file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/serve_guide")
async def serve_guide():
    """
    Servir un fichier guide (pas d'authentification requise)

    Returns:
        FileResponse: Fichier guide
    """
    try:
        # Les guides sont publics
        # TODO: Get filename from query parameter
        raise HTTPException(status_code=501, detail="Not implemented yet")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving guide: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download_suivi/{filename}")
async def download_suivi(
    filename: str,
    user: Dict[str, Any] = Depends(get_current_user),
    settings: Settings = Depends(get_settings)
):
    """
    Télécharger un fichier de suivi

    Args:
        filename: Nom du fichier

    Returns:
        FileResponse: Fichier de suivi
    """
    try:
        safe_filename = sanitize_filename(filename)

        base_path = "data"
        if settings.is_production():
            base_path = settings.azure_fileshare_mount_point

        file_path = Path(base_path) / "suivis" / safe_filename

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        # Protection path traversal
        try:
            file_path.resolve().relative_to(Path(base_path).resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")

        return FileResponse(
            path=str(file_path),
            filename=safe_filename,
            media_type="application/octet-stream"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading suivi: {e}")
        raise HTTPException(status_code=500, detail=str(e))
