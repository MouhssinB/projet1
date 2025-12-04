"""
Routers FastAPI
"""

from .auth import router as auth_router
from .chat import router as chat_router
from .faq import router as faq_router
from .admin import router as admin_router
from .files import router as files_router
from .history import router as history_router

__all__ = [
    "auth_router",
    "chat_router",
    "faq_router",
    "admin_router",
    "files_router",
    "history_router",
]
