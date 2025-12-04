"""
Modèles pour les habilitations
"""
from pydantic import BaseModel
from typing import List, Optional


class HabilitationsConfig(BaseModel):
    """Configuration des habilitations"""
    groupes_habilites: List[str]
    derniere_modification: Optional[str] = None
    modifie_par: Optional[str] = None


class HabilitationUpdate(BaseModel):
    """Mise à jour des habilitations"""
    groupes_habilites: List[str]
