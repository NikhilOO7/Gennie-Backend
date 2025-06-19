"""Emotion model for emotion analysis results."""

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Emotion(Base):
    __tablename__ = "emotions"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    emotion_type = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    chat = relationship("Chat", back_populates="emotions")
    message = relationship("Message")
    
    def __repr__(self):
        return f"<Emotion(id={self.id}, emotion_type='{self.emotion_type}', confidence={self.confidence})>"
