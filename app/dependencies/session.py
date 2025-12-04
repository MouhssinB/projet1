"""
Dépendances pour la gestion de session
"""
from typing import Dict, Any
from fastapi import Request


async def get_session(request: Request) -> Dict[str, Any]:
    """
    Retourne la session de la requête

    Args:
        request: Requête FastAPI

    Returns:
        Dict: Session de la requête
    """
    return request.session
