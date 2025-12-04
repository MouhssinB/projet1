"""
Modèles Pydantic pour la validation des données
"""

from .chat import ChatMessage, ChatResponse, ConversationHistory
from .user import UserInfo, SessionInfo
from .profile import ProfileData, PersonDetails, ProfileRequest
from .synthesis import SynthesisRequest, SynthesisResponse
from .rating import UserRating
from .habilitations import HabilitationsConfig, HabilitationUpdate
from .faq import FAQMessage, FAQResponse

__all__ = [
    "ChatMessage",
    "ChatResponse",
    "ConversationHistory",
    "UserInfo",
    "SessionInfo",
    "ProfileData",
    "PersonDetails",
    "ProfileRequest",
    "SynthesisRequest",
    "SynthesisResponse",
    "UserRating",
    "HabilitationsConfig",
    "HabilitationUpdate",
    "FAQMessage",
    "FAQResponse",
]
