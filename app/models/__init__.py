"""
Models Package Initialization
Imports all models to ensure they're registered with SQLAlchemy
"""

from app.models.user import User
from app.models.chat import Chat
from app.models.message import Message, MessageType, SenderType
from app.models.user_preference import UserPreference, PreferenceType
from app.models.emotion import Emotion, EmotionType

# Export all models and enums
__all__ = [
    "User",
    "Chat", 
    "Message",
    "MessageType",
    "SenderType",
    "UserPreference",
    "PreferenceType",
    "Emotion",
    "EmotionType"
]