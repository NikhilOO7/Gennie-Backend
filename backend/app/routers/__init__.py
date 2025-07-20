# app/routers/__init__.py
"""
Router Package Initialization
"""

from app.routers.auth import router as auth_router
from app.routers.users import router as users_router  
from app.routers.chat import router as chat_router
from app.routers.ai import router as ai_router
from app.routers.websocket import router as websocket_router
from app.routers.health import health_router

# Import voice router - use mock if real voice module doesn't exist
try:
    from app.routers.voice import router as voice_router
except ImportError:
    # If voice.py doesn't exist, try voice_mock.py
    try:
        from app.routers.voice_mock import router as voice_router
    except ImportError:
        # Create a dummy router if neither exists
        from fastapi import APIRouter
        voice_router = APIRouter()

# Re-export routers
auth = auth_router
users = users_router  
chat = chat_router
ai = ai_router
websocket = websocket_router
health = health_router
voice = voice_router

__all__ = [
    "auth",
    "users",
    "chat",
    "ai",
    "websocket",
    "health",
    "voice"
]