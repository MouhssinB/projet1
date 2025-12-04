"""
Dépendances FastAPI pour l'application
"""

from .auth import (
    get_current_user,
    get_current_admin,
    oauth_client,
    get_habilitations_manager,
)
from .session import get_session

__all__ = [
    "get_current_user",
    "get_current_admin",
    "oauth_client",
    "get_habilitations_manager",
    "get_session",
]
