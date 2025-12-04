"""
Modèles pour la FAQ
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class FAQMessage(BaseModel):
    """Message FAQ"""
    question: str = Field(..., min_length=1, max_length=5000, description="Question de la FAQ")


class FAQResponse(BaseModel):
    """Réponse FAQ"""
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    history: Optional[List[dict]] = None
