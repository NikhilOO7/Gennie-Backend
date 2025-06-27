"""
Router Package Initialization
"""

from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.chat import router as chat_router
from app.routers.ai import router as ai_router
from app.routers.websocket import router as websocket_router
from app.routers.health import health_router

# Re-export with consistent names
auth = auth_router
users = users_router
chat = chat_router
ai = ai_router
websocket = websocket_router
health = health_router

__all__ = [
    "auth",
    "users", 
    "chat",
    "ai",
    "websocket",
    "health",
    "auth_router",
    "users_router",
    "chat_router",
    "ai_router",
    "websocket_router",
    "health_router"
]