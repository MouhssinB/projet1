"""
Modèles pour les utilisateurs
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any


class UserInfo(BaseModel):
    """Informations utilisateur"""
    sub: str
    preferred_username: str
    email: EmailStr
    name: str


class Habilitations(BaseModel):
    """Habilitations utilisateur"""
    roles: Dict[str, Any]


class SessionInfo(BaseModel):
    """Informations de session"""
    user: UserInfo
    access_token: str
    habilitations: Habilitations
    auth_timestamp: str
    user_name: str
    user_email: str
    user_id: str
    user_folder: str
