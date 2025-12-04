"""
Routes de chat principal
"""
import json
import logging
import pickle
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from openai import AzureOpenAI

from app.config import get_settings, Settings
from app.dependencies.auth import get_current_user
from app.models.chat import ChatMessage, ChatResponse
from app.models.profile import ProfileRequest
from app.models.synthesis import SynthesisRequest, SynthesisResponse
from app.models.rating import UserRating

from core.fonctions import (
    get_next_bot_message,
    init_session_lists,
    init_session_profile,
    save_profil_manager_to_session,
    restore_profil_manager_from_session,
    get_user_folder_path,
    log_to_journal,
    save_user_rating_to_file,
)
from core.profil_manager import ProfilManager
from core.synthetiser import synthese_2
from core.fonctions import charger_documents_reference, generer_rapport_html_synthese
from core.security import sanitize_user_input, validate_message_format
from core.async_logger import async_logger


router = APIRouter(tags=["Chat"])
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


# Client Azure OpenAI global
def get_azure_openai_client(settings: Settings = Depends(get_settings)):
    """Retourne le client Azure OpenAI"""
    return AzureOpenAI(
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_endpoint=settings.azure_openai_endpoint,
    )


@router.get("/", response_class=templates.TemplateResponse)
async def index(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user),
    settings: Settings = Depends(get_settings)
):
    """
    Page d'accueil principale - interface de chat

    Returns:
        TemplateResponse: Page index.html
    """
    try:
        user_name = user.get("preferred_username", "")
        user_email = user.get("email", "")
        user_id = user.get("sub", "")

        # Charger le ProfilManager depuis la session ou créer un nouveau
        if "profil_manager_pickle" in request.session:
            try:
                profil_manager = pickle.loads(
                    bytes.fromhex(request.session["profil_manager_pickle"])
                )
            except Exception as e:
                logger.warning(f"Failed to restore profile manager: {e}")
                profil_manager = ProfilManager()
        else:
            profil_manager = ProfilManager()

        # Initialiser les listes de session
        if "conversation_history" not in request.session:
            request.session["conversation_history"] = []
        if "history_eval" not in request.session:
            request.session["history_eval"] = []
        if "history_conv" not in request.session:
            request.session["history_conv"] = []

        # Initialiser le profil
        if "profile_data" not in request.session:
            profile_data = {
                "type_personne": profil_manager.get_profil_type(),
                "person_details": profil_manager.get_person_details(),
                "caracteristiques": profil_manager.get_caracteristiques(),
                "objections": profil_manager.get_objections(),
                "aleas": profil_manager.get_contingencies(),
            }
            request.session["profile_data"] = profile_data

        request.session.setdefault("user_rating", None)
        request.session["profile"] = request.session.get("profile_data", {}).get(
            "type_personne", "Particulier"
        )
        request.session["user_name"] = user_name
        request.session["user_email"] = user_email
        request.session["user_folder"] = user_email.replace("@", "_at_").replace(".", "_")

        # Sauvegarder le profil manager dans la session
        request.session["profil_manager_pickle"] = pickle.dumps(profil_manager).hex()

        # Log de connexion
        log_to_journal(user_name, user_email, "connexion")

        async_logger.info("User session complete", folder=request.session["user_folder"])

        # Récupérer le dictionnaire de profils
        dico_profil = request.session.get("profile_data", {})

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "service_region": settings.azure_service_region or "",
                "dico_profil": dico_profil,
            }
        )

    except Exception as e:
        logger.error(f"Error loading index: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_speech_token")
async def get_speech_token(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user),
    settings: Settings = Depends(get_settings)
):
    """
    Génère un token d'autorisation temporaire pour Azure Speech Service

    Returns:
        dict: Token et informations de région
    """
    try:
        import requests

        speech_key = settings.azure_speech_key
        service_region = settings.azure_service_region
        speech_endpoint = settings.azure_speech_endpoint

        if not speech_key:
            return JSONResponse(
                {"success": False, "error": "Speech key not configured"},
                status_code=500
            )

        # Construire l'URL du token
        if speech_endpoint:
            endpoint_base = speech_endpoint.rstrip("/")
            fetch_token_url = f"{endpoint_base}/sts/v1.0/issueToken"
        else:
            fetch_token_url = f"https://{service_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"

        headers = {"Ocp-Apim-Subscription-Key": speech_key}

        # Requête pour obtenir le token avec retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(fetch_token_url, headers=headers, timeout=30)

                if response.status_code == 200:
                    access_token = response.text
                    return {
                        "token": access_token,
                        "region": service_region,
                        "endpoint": speech_endpoint,
                        "success": True,
                    }
                else:
                    if attempt < max_retries - 1:
                        continue
                    return JSONResponse(
                        {
                            "success": False,
                            "error": f"HTTP {response.status_code}",
                        },
                        status_code=500
                    )
            except requests.exceptions.RequestException as req_err:
                if attempt < max_retries - 1:
                    continue
                return JSONResponse(
                    {"success": False, "error": str(req_err)},
                    status_code=500
                )

    except Exception as e:
        logger.error(f"Error generating speech token: {e}")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@router.post("/set_profile")
async def set_profile(
    request: Request,
    profile_request: ProfileRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Définir le profil utilisateur

    Args:
        profile_request: Type de profil et paramètres

    Returns:
        dict: Détails du nouveau profil
    """
    try:
        # Créer un nouveau ProfilManager
        profil_manager = ProfilManager(
            type_personne=profile_request.profile_type,
            nb_caracteristiques=profile_request.nb_caracteristiques,
            nb_objections=profile_request.nb_objections,
            nb_aleas=profile_request.nb_aleas,
        )

        # Sauvegarder dans la session
        profile_data = {
            "type_personne": profil_manager.get_profil_type(),
            "person_details": profil_manager.get_person_details(),
            "caracteristiques": profil_manager.get_caracteristiques(),
            "objections": profil_manager.get_objections(),
            "aleas": profil_manager.get_contingencies(),
        }

        request.session["profile_data"] = profile_data
        request.session["profile"] = profile_request.profile_type
        request.session["profil_manager_pickle"] = pickle.dumps(profil_manager).hex()

        async_logger.info(
            "Profile updated",
            profile_type=profile_request.profile_type,
            user=user.get("preferred_username", "")
        )

        return {
            "success": True,
            "message": f"Profil '{profile_request.profile_type}' défini avec succès",
            "profile_data": profile_data,
        }

    except Exception as e:
        logger.error(f"Error setting profile: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@router.post("/reset_conversation")
async def reset_conversation(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Réinitialiser la conversation

    Returns:
        dict: Confirmation de réinitialisation
    """
    try:
        request.session["conversation_history"] = []

        async_logger.info(
            "Conversation reset",
            user=user.get("preferred_username", "")
        )

        return {
            "success": True,
            "message": "Conversation réinitialisée avec succès",
        }

    except Exception as e:
        logger.error(f"Error resetting conversation: {e}")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@router.post("/chat")
async def chat(
    request: Request,
    chat_message: ChatMessage,
    user: Dict[str, Any] = Depends(get_current_user),
    client: AzureOpenAI = Depends(get_azure_openai_client)
):
    """
    Endpoint de chat - traitement des messages utilisateur

    Args:
        chat_message: Message de l'utilisateur
        user: Utilisateur authentifié
        client: Client Azure OpenAI

    Returns:
        ChatResponse: Réponse du bot
    """
    try:
        user_message = chat_message.message

        # Validation et sécurisation du message
        sanitized_message = sanitize_user_input(user_message)

        is_valid, error_msg = validate_message_format(sanitized_message)
        if not is_valid:
            return JSONResponse(
                {"success": False, "error": error_msg},
                status_code=400
            )

        # Récupérer l'historique de conversation
        conversation_history = request.session.get("conversation_history", [])

        # Restaurer le ProfilManager
        if "profil_manager_pickle" in request.session:
            profil_manager = pickle.loads(
                bytes.fromhex(request.session["profil_manager_pickle"])
            )
        else:
            profil_manager = ProfilManager()

        # Ajouter le message utilisateur à l'historique
        msg_num = len(conversation_history) + 1
        user_msg = {
            "msg_num": msg_num,
            "role": "Vous",
            "text": sanitized_message,
            "timestamp": datetime.utcnow().isoformat(),
        }
        conversation_history.append(user_msg)

        # Obtenir la réponse du bot
        bot_response_dict = get_next_bot_message(
            sanitized_message, client, conversation_history, profil_manager
        )

        # Ajouter la réponse du bot à l'historique
        bot_msg = {
            "msg_num": msg_num + 1,
            "role": "Bot",
            "text": bot_response_dict.get("text", ""),
            "timestamp": datetime.utcnow().isoformat(),
        }
        conversation_history.append(bot_msg)

        # Sauvegarder l'historique
        request.session["conversation_history"] = conversation_history

        async_logger.info(
            "Chat message processed",
            user=user.get("preferred_username", ""),
            msg_count=len(conversation_history)
        )

        return {
            "success": True,
            "response": bot_response_dict.get("text", ""),
            "history": conversation_history,
        }

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@router.post("/synthetiser")
async def synthetiser(
    request: Request,
    synthesis_request: SynthesisRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    client: AzureOpenAI = Depends(get_azure_openai_client)
):
    """
    Synthétiser la conversation

    Args:
        synthesis_request: Requête de synthèse
        user: Utilisateur authentifié
        client: Client Azure OpenAI

    Returns:
        SynthesisResponse: Résultat de la synthèse
    """
    try:
        conversation_history = request.session.get("conversation_history", [])

        if not conversation_history:
            return JSONResponse(
                {"success": False, "error": "Aucune conversation à synthétiser"},
                status_code=400
            )

        # Restaurer le ProfilManager
        if "profil_manager_pickle" in request.session:
            profil_manager = pickle.loads(
                bytes.fromhex(request.session["profil_manager_pickle"])
            )
        else:
            profil_manager = ProfilManager()

        # Charger les documents de référence
        references = charger_documents_reference()

        # Générer la synthèse
        synthesis_data = synthese_2(
            conversation_history,
            client,
            references,
            profil_manager,
            request.session
        )

        # Générer le rapport HTML
        user_folder = request.session.get("user_folder", "default")
        output_path = f"data/utilisateurs/{user_folder}/syntheses/"

        html_report_path = generer_rapport_html_synthese(
            synthesis_data,
            output_path
        )

        # Ajouter au suivi
        if "history_eval" in request.session:
            request.session["history_eval"].append(html_report_path)

        async_logger.info(
            "Synthesis generated",
            user=user.get("preferred_username", ""),
            report_path=html_report_path
        )

        return {
            "success": True,
            "message": "Synthèse générée avec succès",
            "synthesis_data": synthesis_data,
            "html_report_path": html_report_path,
        }

    except Exception as e:
        logger.error(f"Error in synthesis: {e}", exc_info=True)
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@router.post("/save_user_rating")
async def save_user_rating(
    request: Request,
    rating: UserRating,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Sauvegarder la note de satisfaction utilisateur

    Args:
        rating: Note et commentaire
        user: Utilisateur authentifié

    Returns:
        dict: Confirmation de sauvegarde
    """
    try:
        note_data = {
            "user_name": user.get("preferred_username", ""),
            "user_email": user.get("email", ""),
            "note": rating.note,
            "commentaire": rating.commentaire or "",
            "timestamp": datetime.utcnow().isoformat(),
        }

        save_user_rating_to_file(note_data)

        request.session["user_rating"] = rating.note

        async_logger.info(
            "User rating saved",
            user=user.get("preferred_username", ""),
            note=rating.note
        )

        return {
            "success": True,
            "message": "Note enregistrée avec succès",
        }

    except Exception as e:
        logger.error(f"Error saving rating: {e}")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@router.get("/get_conversation_history")
async def get_conversation_history(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Récupérer l'historique de conversation

    Returns:
        dict: Historique de conversation
    """
    try:
        conversation_history = request.session.get("conversation_history", [])

        return {
            "success": True,
            "history": conversation_history,
        }

    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )


@router.post("/get_person_details")
async def get_person_details(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Obtenir les détails du profil de la personne

    Returns:
        dict: Détails du profil
    """
    try:
        profile_data = request.session.get("profile_data", {})

        return {
            "success": True,
            "profile_data": profile_data,
        }

    except Exception as e:
        logger.error(f"Error getting person details: {e}")
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500
        )
