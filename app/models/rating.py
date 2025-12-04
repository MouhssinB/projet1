"""
Modèles pour les notes utilisateur
"""
from pydantic import BaseModel, Field
from typing import Optional


class UserRating(BaseModel):
    """Note de satisfaction utilisateur"""
    note: int = Field(..., ge=1, le=5, description="Note de 1 à 5")
    commentaire: Optional[str] = Field(None, max_length=1000, description="Commentaire optionnel")
