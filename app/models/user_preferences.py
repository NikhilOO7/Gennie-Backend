from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class UserPreferences(Base):
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Basic preferences
    age = Column(Integer, nullable=True)
    interests = Column(JSON, nullable=True)  # List of interests
    language = Column(String(10), default="en")
    timezone = Column(String(50), nullable=True)
    
    # Personality and response preferences
    personality_type = Column(String(50), nullable=True)  # e.g., "INTJ", "extrovert"
    response_style = Column(String(50), default="balanced")  # "formal", "casual", "balanced"
    preferred_response_length = Column(String(20), default="medium")  # "short", "medium", "long"
    
    # UI/UX preferences
    theme = Column(String(20), default="light")  # "light", "dark", "auto"
    font_size = Column(String(20), default="medium")
    color_scheme = Column(String(50), nullable=True)
    
    # Notification preferences
    notification_settings = Column(JSON, nullable=True)
    email_notifications = Column(Boolean, default=True)
    push_notifications = Column(Boolean, default=True)
    
    # AI behavior preferences
    ai_personality = Column(String(50), default="helpful")  # "helpful", "friendly", "professional"
    context_memory = Column(Boolean, default=True)
    personalization_enabled = Column(Boolean, default=True)
    
    # Privacy settings
    data_sharing = Column(Boolean, default=False)
    analytics_tracking = Column(Boolean, default=True)
    
    # Learning and interaction history
    personality_traits = Column(JSON, nullable=True)  # Learned personality traits
    interaction_history = Column(JSON, nullable=True)  # Summary of past interactions
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="preferences")
    
    def __repr__(self):
        return f"<UserPreferences(id={self.id}, user_id={self.user_id})>"