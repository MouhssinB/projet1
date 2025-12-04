"""
Modèles pour le chat
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ChatMessage(BaseModel):
    """Message de chat"""
    message: str = Field(..., min_length=1, max_length=5000, description="Contenu du message")


class ConversationMessage(BaseModel):
    """Message dans l'historique de conversation"""
    msg_num: int
    role: str
    text: str
    timestamp: str


class ConversationHistory(BaseModel):
    """Historique de conversation"""
    messages: List[ConversationMessage]


class ChatResponse(BaseModel):
    """Réponse du bot"""
    success: bool
    message: Optional[str] = None
    response: Optional[str] = None
    error: Optional[str] = None
    history: Optional[List[ConversationMessage]] = None
