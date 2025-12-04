"""
Modèles pour la synthèse de conversation
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class SynthesisRequest(BaseModel):
    """Requête de synthèse"""
    conversation_id: Optional[str] = None


class SynthesisResponse(BaseModel):
    """Réponse de synthèse"""
    success: bool
    message: Optional[str] = None
    synthesis_data: Optional[Dict[str, Any]] = None
    html_report_path: Optional[str] = None
    error: Optional[str] = None
