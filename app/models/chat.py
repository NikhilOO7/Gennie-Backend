"""Chat model for conversation sessions."""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Allow anonymous chats
    title = Column(String(255), nullable=True)
    context_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    emotions = relationship("Emotion", back_populates="chat", cascade="all, delete-orphan")
    preferences = relationship("UserPreferences", back_populates="chat", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Chat(id={self.id}, title='{self.title}')>"
