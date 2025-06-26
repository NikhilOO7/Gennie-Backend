"""
Models package initialization.
This file ensures all models are imported so SQLAlchemy can find them.
"""

from app.models.user import User
from app.models.chat import Chat
from app.models.message import Message
from app.models.emotion import Emotion
from app.models.user_preferences import UserPreferences

# Make all models available at package level
__all__ = [
    "User",
    "Chat", 
    "Message",
    "Emotion",
    "UserPreferences"
]