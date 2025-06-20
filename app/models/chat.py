from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    
    # Chat settings
    ai_model = Column(String(50), default="gpt-3.5-turbo")
    system_prompt = Column(Text, nullable=True)
    temperature = Column(String(10), default="0.7")
    max_tokens = Column(Integer, default=1000)
    
    # Chat metadata
    is_archived = Column(Boolean, default=False)
    is_favorite = Column(Boolean, default=False)
    tags = Column(JSON, nullable=True)  # List of tags
    category = Column(String(50), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Chat(id={self.id}, user_id={self.user_id}, title='{self.title}')>"