"""User preferences model for personalization."""

from sqlalchemy import Column, Integer, String, JSON, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class UserPreferences(Base):
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    personality_traits = Column(JSON, nullable=True)
    response_style = Column(String(50), nullable=True)
    interaction_history = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    chat = relationship("Chat", back_populates="preferences")
    
    def __repr__(self):
        return f"<UserPreferences(id={self.id}, chat_id={self.chat_id})>"
