from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Float, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class UserPreference(Base):
    __tablename__ = "user_preferences"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Conversation Preferences
    preferred_response_length = Column(String(20), default="medium")  # short, medium, long
    conversation_style = Column(String(30), default="friendly")  # formal, friendly, casual, professional
    language = Column(String(10), default="en")
    timezone = Column(String(50), default="UTC")
    
    # AI Model Preferences
    temperature = Column(Float, default=0.7)  # OpenAI temperature setting
    max_tokens = Column(Integer, default=1000)
    top_p = Column(Float, default=1.0)
    frequency_penalty = Column(Float, default=0.0)
    presence_penalty = Column(Float, default=0.0)
    
    # Personalization Settings
    enable_emotion_detection = Column(Boolean, default=True)
    enable_context_memory = Column(Boolean, default=True)
    enable_learning = Column(Boolean, default=True)
    enable_suggestions = Column(Boolean, default=True)
    
    # User Profile Data (JSON fields)
    interests = Column(JSON, nullable=True)  # List of interests
    personality_traits = Column(JSON, nullable=True)  # Personality analysis
    conversation_patterns = Column(JSON, nullable=True)  # Learned patterns
    topics_of_interest = Column(JSON, nullable=True)  # Frequently discussed topics
    
    # Privacy Settings
    data_retention_days = Column(Integer, default=365)  # How long to keep data
    allow_data_analysis = Column(Boolean, default=True)
    allow_personalization = Column(Boolean, default=True)
    
    # Notification Preferences
    email_notifications = Column(Boolean, default=True)
    push_notifications = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="preferences")
    
    def __repr__(self):
        return f"<UserPreference(id={self.id}, user_id={self.user_id}, style='{self.conversation_style}')>"