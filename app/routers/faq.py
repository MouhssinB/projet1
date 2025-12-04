"""
Routes FAQ
"""
import logging
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from openai import AzureOpenAI

from app.config import get_settings, Settings
from app.dependencies.auth import get_current_user
from app.models.faq import FAQMessage, FAQResponse
from core.fonctions import generate_expert_response, charger_documents_reference
from core.security import sanitize_user_input, validate_message_format
from core.async_logger import async_logger


router = APIRouter(tags=["FAQ"], prefix="/faq")
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


def get_azure_openai_client(settings: Settings = Depends(get_settings)):
    """Retourne le client Azure OpenAI"""
    return AzureOpenAI(
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_endpoint=settings.azure_openai_endpoint,
    )


@router.get("", response_class=templates.TemplateResponse)
async def faq_page(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Page FAQ

    Returns:
        TemplateResponse: Page faq.html
    """
    try:
        # Initialiser l'historique FAQ si nécessaire
        if "faq_history" not in request.session:
            request.session["faq_history"] = []

        return templates.TemplateResponse(
            "faq.html",
            {"request": request}
        )

    except Exception as e:
        logger.error(f"Error loading FAQ page: {e}")
        raise


@router.post("_chat")
async def faq_chat(
    request: Request,
    faq_message: FAQMessage,
    user: Dict[str, Any] = Depends(get_current_user),
    client: AzureOpenAI = Depends(get_azure_openai_client)
):
    """
    Chat FAQ - questions/réponses

    Args:
        faq_message: Question de l'utilisateur
        user: Utilisateur authentifié
        client: Client Azure OpenAI

    Returns:
        FAQResponse: Réponse FAQ
    """
    try:
        question = faq_message.question

        # Validation et sécurisation
        sanitized_question = sanitize_user_input(question)

        is_valid, error_msg = validate_message_format(sanitized_question)
        if not is_valid:
            return JSONResponse(
                {"success": False, "error": error_msg},
                status_code=400
            )

        # Récupérer l'historique FAQ
        faq_history = request.session.get("faq_history", [])

        # Charger les documents de référence
        references = charger_documents_reference()

        # Générer la réponse
        response_text = generate_expert_response(
            sanitized_question,
            client,
            faq_history,
            references
        )

        # Ajouter à l'historique
        faq_history.append({
            "question": sanitized_question,
            "response": response_text,
            "timestamp": datetime.utcnow().isoformat(),
        })

        request.session["faq_history"] = faq_history

        async_logger.info(
            "FAQ question answered",
            user=user.get("preferred_username", "")
        )

        return {
            "success": True,
            "response": response_text,
            "history": faq_history,
        }

    except Exception as e:
        logger.error(f"Error in FAQ chat: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@router.get("_history")
async def faq_history(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Récupérer l'historique FAQ

    Returns:
        dict: Historique FAQ
    """
    try:
        faq_history = request.session.get("faq_history", [])

        return {
            "success": True,
            "history": faq_history,
        }

    except Exception as e:
        logger.error(f"Error getting FAQ history: {e}")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@router.post("_reset")
async def faq_reset(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Réinitialiser l'historique FAQ

    Returns:
        dict: Confirmation
    """
    try:
        request.session["faq_history"] = []

        async_logger.info(
            "FAQ history reset",
            user=user.get("preferred_username", "")
        )

        return {
            "success": True,
            "message": "Historique FAQ réinitialisé",
        }

    except Exception as e:
        logger.error(f"Error resetting FAQ: {e}")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )
