from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Boolean, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from app.database import Base

class SenderType(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class MessageStatus(enum.Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False, index=True)
    
    # Message content
    content = Column(Text, nullable=False)
    sender_type = Column(String(20), nullable=False)  # Using String instead of Enum for simplicity
    
    # Message properties
    message_type = Column(String(20), default="text")  # "text", "image", "file", "system"
    status = Column(String(20), default="sent")  # Using String instead of Enum
    parent_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)  # For replies
    
    # AI-related data
    emotion_data = Column(JSON, nullable=True)  # Emotion analysis results
    sentiment_score = Column(String(10), nullable=True)  # Positive/Negative/Neutral
    confidence_score = Column(String(10), nullable=True)  # AI confidence in response
    
    # Processing data
    processing_time = Column(String(10), nullable=True)  # Time taken to generate response
    model_used = Column(String(50), nullable=True)  # AI model used for response
    tokens_used = Column(Integer, nullable=True)  # Number of tokens used
    
    # Additional data (renamed from 'metadata' to avoid SQLAlchemy conflict)
    message_metadata = Column(JSON, nullable=True)  # Additional flexible data
    is_edited = Column(Boolean, default=False)
    edit_history = Column(JSON, nullable=True)  # History of edits
    
    # Flags
    is_favorite = Column(Boolean, default=False)
    is_flagged = Column(Boolean, default=False)
    flag_reason = Column(String(100), nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")
    replies = relationship("Message", backref="parent", remote_side=[id])
    
    def __repr__(self):
        return f"<Message(id={self.id}, chat_id={self.chat_id}, sender_type={self.sender_type})>"
    
    def get_metadata(self):
        """Get message metadata (backward compatibility method)"""
        return self.message_metadata
    
    def set_metadata(self, value):
        """Set message metadata (backward compatibility method)"""
        self.message_metadata = value
    
    def to_dict(self) -> dict:
        """Convert message to dictionary"""
        return {
            "id": self.id,
            "chat_id": self.chat_id,
            "content": self.content,
            "sender_type": self.sender_type,
            "message_type": self.message_type,
            "emotion_data": self.emotion_data,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.message_metadata,  # Backward compatibility in dict output
            "message_metadata": self.message_metadata,  # Also include new field name
            "is_edited": self.is_edited,
            "is_favorite": self.is_favorite
        }